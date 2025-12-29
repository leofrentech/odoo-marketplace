import base64
import io
from PIL import Image, ImageDraw, ImageFont


# Convert base64 to PIL Image
def decode_image(image_data):
    """Decode base64 image to PIL Image."""
    if not image_data:
        return None
    
    try:
        image_bytes = base64.b64decode(image_data)
        return Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    
    except Exception:
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
    
    except Exception:
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
    alpha = int(255 * (settings.get("opacity", 50.0) / 100.0))
    overlay_alpha = overlay.getchannel("A")
    overlay.putalpha(
        overlay_alpha.point(lambda x: min(x, alpha) if x > 0 else 0)
    )

    return Image.alpha_composite(img, overlay)

# Text Watermark
def _draw_text_watermark(overlay, settings):
    draw = ImageDraw.Draw(overlay)
    text = settings.get("text", "WATERMARK")

    try:
        font = ImageFont.truetype(
            f"{settings.get('font', 'Arial')}.ttf",
            settings.get("size", 24),
        )

    except Exception:
        font = ImageFont.load_default()

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
    padding = 20

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
