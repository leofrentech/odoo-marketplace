import base64
import binascii
import functools
import glob
import io
import logging
import os
from PIL import Image, ImageDraw, ImageFont


_logger = logging.getLogger(__name__)

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

# Convert PIL Image to base64
def encode_image(pil_image):
    """Encode PIL Image to base64."""
    if not pil_image:
        return False

    try:
        output = io.BytesIO()
        pil_image.save(output, format="PNG")
        return base64.b64encode(output.getvalue())

    except (OSError, ValueError):
        return False

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
    """
    candidates = [f"{font_name}.ttf"] + _FONT_FALLBACKS.get(font_name, [])

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


def is_valid_opacity(value):
    """Whether `value` is a valid watermark opacity (0-1 range, inclusive)."""
    return 0 <= value <= 1


def resolve_watermark_type(enabled, watermark_type):
    """Combine the settings "enabled" boolean with the image/text type
    Selection into the single 'type' value (image/text/none) the rest
    of the watermarking pipeline expects."""
    return watermark_type if enabled else "none"
