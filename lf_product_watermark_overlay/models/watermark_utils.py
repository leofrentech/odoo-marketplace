import base64
import binascii
import functools
import glob
import importlib
import io
import logging
import os
from PIL import Image, ImageDraw, ImageFont


_logger = logging.getLogger(__name__)

# Odoo preinitializes PIL with only BMP/GIF/JPEG/PPM/PNG and blocks
# loading the rest (see odoo/tools/image.py), so WebP, the format the
# product form converts every upload to, can't be opened or saved
# unless its plugin is registered explicitly.
importlib.import_module("PIL.WebPImagePlugin")

# Common font install locations across the platforms Odoo actually runs on
# (Linux servers/containers, macOS dev machines). Searched recursively.
_FONT_SEARCH_DIRS = [
    "/usr/share/fonts",
    "/usr/local/share/fonts",
    "/Library/Fonts",
    "/System/Library/Fonts",
    os.path.expanduser("~/.fonts"),
    os.path.expanduser("~/Library/Fonts"),
]

# The selectable fonts are proprietary Microsoft/Apple fonts that are
# rarely present on a Linux server by default. These open-licensed /
# commonly-preinstalled equivalents are tried as fallbacks so watermarks
# still render even when the exact font isn't installed.
_FONT_FALLBACKS = {
    "Arial": ["arial.ttf", "LiberationSans-Regular.ttf", "DejaVuSans.ttf"],
    "Times New Roman": ["times.ttf", "LiberationSerif-Regular.ttf", "DejaVuSerif.ttf"],
    "Courier New": ["cour.ttf", "LiberationMono-Regular.ttf", "DejaVuSansMono.ttf"],
    "Verdana": ["verdana.ttf", "DejaVuSans.ttf"],
    "Georgia": ["georgia.ttf", "DejaVuSerif.ttf"],
    "Comic Sans MS": ["comic.ttf", "ComicNeue-Regular.ttf", "DejaVuSans.ttf"],
    "Impact": ["impact.ttf", "DejaVuSans-Bold.ttf"],
}

# Selectable fonts, shared by the settings and the watermark wizard.
FONT_SELECTION = [(font, font) for font in _FONT_FALLBACKS]


# Convert base64 to PIL Image
def decode_image(image_data):
    """Decode base64 image to PIL Image."""
    if not image_data:
        return None

    try:
        image_bytes = base64.b64decode(image_data)
        return Image.open(io.BytesIO(image_bytes)).convert("RGBA")

    except (binascii.Error, OSError, ValueError):
        return None


# Raster formats a watermark can be composited onto without losing
# anything. Everything else is left untouched: an (animated) GIF would
# be flattened to its first frame, and SVG/other files PIL can't decode
# must never be overwritten with an empty result.
_WATERMARKABLE_FORMATS = {"PNG", "JPEG", "WEBP"}

# Default logo watermark size, as a percentage of the product image's
# width and height the logo is scaled to fit within.
DEFAULT_LOGO_SIZE = 20

# Sizes Odoo's image field widget pre-generates for a WebP upload (see
# web/static/src/views/fields/image/image_field.js, `onFileUploaded`).
_WEBP_RESIZE_SIZES = (1920, 1024, 512, 256, 128)


def decode_watermarkable_image(image_data):
    """Like `decode_image()`, but also returns the source format, so the
    watermarked result can be saved back in that same format.

    Returns `(None, None)` for any image whose format is not in
    `_WATERMARKABLE_FORMATS`, meaning "skip it"."""
    if not image_data:
        return None, None

    try:
        image = Image.open(io.BytesIO(base64.b64decode(image_data)))
        if image.format not in _WATERMARKABLE_FORMATS:
            return None, None
        return image.convert("RGBA"), image.format

    except (binascii.Error, OSError, ValueError):
        return None, None

# Convert PIL Image to base64
def encode_image(pil_image, output_format="PNG"):
    """Encode PIL Image to base64, in `output_format` (PNG, JPEG or
    WEBP). JPEG has no alpha channel, so transparency is flattened onto
    white."""
    if not pil_image:
        return False

    try:
        output = io.BytesIO()
        if output_format == "JPEG":
            _flatten_on_white(pil_image).save(output, format="JPEG", quality=95, optimize=True)
        elif output_format == "WEBP":
            pil_image.save(output, format="WEBP", quality=90)
        else:
            pil_image.save(output, format="PNG", optimize=True)
        return base64.b64encode(output.getvalue())

    except (OSError, ValueError):
        return False


def encode_watermarked_image(env, pil_image, output_format):
    """Encode a watermarked image in its original format, ready to be
    written to an `image_1920`-like field.

    Odoo never resizes WebP server side: `image_1024`/`image_512`/...
    and PDF reports are served from `ir.attachment` alternates the web
    client generates at upload time, matched by checksum. A watermarked
    WebP is new content with no such alternates, so they are created
    here the same way the client does, before the image field is
    written (the related resized fields look them up on write)."""
    image_b64 = encode_image(pil_image, output_format)
    if image_b64 and output_format == "WEBP":
        _create_webp_alternates(env, pil_image, image_b64)
    return image_b64


def render_watermark(env, image_b64, settings):
    """Watermark a base64 image with `settings`, returning the result in
    the image's own format — or False when the image must be left as is:
    an unsupported format (see `_WATERMARKABLE_FORMATS`), or a failed
    rendering (bad font, color, ...), which is logged. Never raises for
    a bad image or setting, so it can't block saving the record."""
    base_image, source_format = decode_watermarkable_image(image_b64)
    if base_image is None:
        return False
    try:
        result = apply_watermark(base_image, settings)
    except (OSError, ValueError) as e:
        _logger.warning("Watermark rendering failed: %s", e)
        return False
    return encode_watermarked_image(env, result, source_format)


def _flatten_on_white(pil_image):
    background = Image.new("RGB", pil_image.size, (255, 255, 255))
    background.paste(pil_image, mask=pil_image.getchannel("A") if pil_image.mode == "RGBA" else None)
    return background


def _create_webp_alternates(env, pil_image, image_b64):
    """Mirror of the web client's WebP upload handling: store the image
    as a standalone attachment, plus one resized WebP per smaller size
    and a JPEG fallback (for wkhtmltopdf) of each."""
    Attachment = env["ir.attachment"]
    name = "watermarked.webp"
    original_size = max(pil_image.size)
    sizes = [original_size] + [size for size in _WEBP_RESIZE_SIZES if size < original_size]

    reference_id = False
    for size in sizes:
        if size == original_size:
            resized, datas = pil_image, image_b64
        else:
            resized = pil_image.copy()
            resized.thumbnail((size, size), Image.LANCZOS)
            datas = encode_image(resized, "WEBP")
        [resized_id] = Attachment.create_unique([{
            "name": name,
            "description": "" if size == original_size else f"resize: {size}",
            "datas": datas,
            "res_id": reference_id,
            "res_model": "ir.attachment",
            "mimetype": "image/webp",
        }])
        reference_id = reference_id or resized_id  # keep track of the original
        Attachment.create_unique([{
            "name": "watermarked.jpg",
            "description": "format: jpeg",
            "datas": encode_image(resized, "JPEG"),
            "res_id": resized_id,
            "res_model": "ir.attachment",
            "mimetype": "image/jpeg",
        }])

# Apply watermark main method
def apply_watermark(base_image, settings):
    """Apply watermark on a PIL image."""
    if not base_image:
        return None

    img = base_image.copy()
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))

    if settings["type"] == "text" and settings.get("text"):
        overlay = _draw_text_watermark(overlay, settings)

    elif settings["type"] == "image" and settings.get("logo"):
        overlay = _draw_image_watermark(overlay, settings)

    else:
        return img

    # Apply opacity
    alpha = int(255 * settings.get("opacity", 0.5))
    overlay_alpha = overlay.getchannel("A")
    overlay.putalpha(
        overlay_alpha.point(lambda x: min(x, alpha) if x > 0 else 0)
    )

    return Image.alpha_composite(img, overlay)


@functools.lru_cache(maxsize=32)
def _find_font_path(font_name):
    """Best-effort lookup of a usable .ttf file for `font_name`.

    Tries the exact font first (works when it's actually installed, e.g.
    on a macOS dev box), then walks a list of open-licensed / commonly
    preinstalled fallbacks so watermarking still works on servers that
    lack proprietary fonts such as Arial or Comic Sans MS. Result is
    cached per font name since scanning font directories is not cheap.

    Only the known fonts in `_FONT_FALLBACKS` are ever looked up: the
    name ends up in a recursive glob pattern, so an arbitrary value
    (e.g. "../../**/*") must never reach it.
    """
    if font_name not in _FONT_FALLBACKS:
        font_name = "Arial"
    candidates = [f"{font_name}.ttf"] + _FONT_FALLBACKS[font_name]

    for candidate in candidates:
        for directory in _FONT_SEARCH_DIRS:
            matches = glob.glob(os.path.join(directory, "**", candidate), recursive=True)
            if matches:
                return matches[0]

    return None


def _load_font(font_name, font_size):
    """Load a TrueType font for `font_name`, falling back through known
    alternates and finally PIL's built-in default font, so a missing
    font on the server never breaks watermark generation entirely."""
    path = _find_font_path(font_name)
    if path:
        try:
            return ImageFont.truetype(path, font_size)
        except OSError:
            _logger.warning("Found font file %s but failed to load it.", path)

    _logger.warning(
        "No usable .ttf found for watermark font %r; falling back to PIL's default font.",
        font_name,
    )
    try:
        # Pillow >= 10.1 supports a scalable default font via `size`.
        return ImageFont.load_default(size=font_size)
    except TypeError:
        # Older Pillow: fixed-size bitmap default font.
        return ImageFont.load_default()

# Text Watermark
def _draw_text_watermark(overlay, settings):
    draw = ImageDraw.Draw(overlay)
    text = settings.get("text", "WATERMARK")

    img_w, img_h = overlay.size
    diagonal = (img_w**2 + img_h**2) ** 0.5
    size_percent = settings.get("size", 6)
    font_size = max(12, int(diagonal * size_percent / 100))

    font = _load_font(settings.get("font") or "Arial", font_size)

    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    x, y = _calculate_position(
        overlay.size, (text_width, text_height), settings.get("position")
    )

    color = _hex_to_rgb(settings.get("color", "#FFFFFF"))
    draw.text((x, y), text, font=font, fill=color + (255,))

    return overlay

# Image Watermark
def _draw_image_watermark(overlay, settings):
    logo_image = decode_image(settings.get("logo"))
    if not logo_image:
        return overlay

    # Scale the logo (up or down, keeping its aspect ratio) to fit a box
    # `logo_size`% of the product image's width and height, so it keeps
    # the same relative footprint whatever the logo's or photo's own
    # resolution, instead of being pasted at its native pixel size.
    img_width, img_height = overlay.size
    percent = settings.get("logo_size") or DEFAULT_LOGO_SIZE
    ratio = min(
        img_width * percent / 100 / logo_image.width,
        img_height * percent / 100 / logo_image.height,
    )
    logo_image = logo_image.resize(
        (max(1, round(logo_image.width * ratio)), max(1, round(logo_image.height * ratio))),
        Image.LANCZOS,
    )
    logo_width, logo_height = logo_image.size

    x, y = _calculate_position(
        overlay.size, (logo_width, logo_height), settings.get("position")
    )

    overlay.paste(logo_image, (x, y), logo_image)
    return overlay

# Position Caluculation
def _calculate_position(image_size, watermark_size, position):
    img_width, img_height = image_size
    wm_width, wm_height = watermark_size
    padding = int(min(img_width, img_height) * 0.05)  # Padding as 5% of the image size

    positions = {
        "top_left": (padding, padding),
        "top_right": (img_width - wm_width - padding, padding),
        "center": (
            (img_width - wm_width) // 2,
            (img_height - wm_height) // 2,
        ),
        "bottom_left": (padding, img_height - wm_height - padding),
        "bottom_right": (
            img_width - wm_width - padding,
            img_height - wm_height - padding,
        ),
    }

    return positions.get(position, positions["bottom_right"])

# Covert Hex code to RGB
def _hex_to_rgb(hex_color):
    hex_color = (hex_color or "").lstrip("#")
    if len(hex_color) != 6:
        return (255, 255, 255)

    try:
        return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))

    except ValueError:
        return (255, 255, 255)


def is_valid_size_percent(value):
    """Whether `value` is a valid watermark or logo size (1-100%)."""
    return 1 <= value <= 100


def is_valid_opacity(value):
    """Whether `value` is a valid watermark opacity (0-1 range, inclusive)."""
    return 0 <= value <= 1


def resolve_watermark_type(enabled, watermark_type):
    """Combine the settings "enabled" boolean with the image/text type
    Selection into the single 'type' value (image/text/none) the rest
    of the watermarking pipeline expects."""
    return watermark_type if enabled else "none"
