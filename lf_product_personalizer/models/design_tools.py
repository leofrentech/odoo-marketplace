"""Validation of design data sent by website visitors.

Everything coming from the editor is untrusted: it is posted by public users.
These helpers bound the size of the payload, keep only the Fabric.js objects the
editor can create, and only accept raster images / sanitized SVG.
"""
import base64
import binascii
import json
import re

from lxml import etree

from odoo.exceptions import UserError

DEFAULT_MAX_UPLOAD_MB = 15
MAX_OBJECTS_PER_AREA = 100
MAX_TEXT_CHARS = 2000
MAX_JSON_CHARS = 2 * 1024 * 1024  # once images are extracted to attachments

ALLOWED_OBJECT_TYPES = {
    "i-text", "text", "textbox", "image", "rect", "circle", "ellipse",
    "triangle", "line", "polygon", "polyline", "path",
}
TEXT_TYPES = {"i-text", "text", "textbox"}

RASTER_MIMETYPES = {
    "png": "image/png",
    "jpeg": "image/jpeg",
    "jpg": "image/jpeg",
    "webp": "image/webp",
    "gif": "image/gif",
}
DATA_URL_RE = re.compile(r"^data:image/(png|jpeg|jpg|webp|gif);base64,(.*)$", re.S)
# Images the editor may reference once uploads are stored as attachments.
SAFE_SRC_RE = re.compile(
    r"^/web/(content/\d+\?access_token=[\w-]+"
    r"|image/product\.design\.clipart/\d+/image"
    r"|image/product\.product/\d+/image_1920)$"
)
MAGIC_BYTES = {
    "image/png": (b"\x89PNG\r\n\x1a\n",),
    "image/jpeg": (b"\xff\xd8\xff",),
    "image/gif": (b"GIF87a", b"GIF89a"),
    "image/webp": (b"RIFF",),
}


def max_upload_bytes(env):
    value = env["ir.config_parameter"].sudo().get_param(
        "lf_product_personalizer.max_upload_mb", DEFAULT_MAX_UPLOAD_MB
    )
    try:
        megabytes = max(1, int(value))
    except (TypeError, ValueError):
        megabytes = DEFAULT_MAX_UPLOAD_MB
    return megabytes * 1024 * 1024


def decode_data_url(env, data_url, max_bytes):
    """Return (raw bytes, mimetype) of a base64 raster data URL, or raise."""
    match = DATA_URL_RE.match(data_url or "")
    if not match:
        raise UserError(env._("Only PNG, JPEG, WebP or GIF images are accepted."))
    mimetype = RASTER_MIMETYPES[match.group(1)]
    payload = match.group(2)
    if len(payload) * 3 // 4 > max_bytes:
        raise UserError(
            env._("This image is too large (maximum %s MB).", max_bytes // (1024 * 1024))
        )
    try:
        raw = base64.b64decode(payload, validate=True)
    except (binascii.Error, ValueError):
        raise UserError(env._("The image could not be read.")) from None
    if not raw.startswith(MAGIC_BYTES[mimetype]):
        raise UserError(env._("The image content does not match its type."))
    return raw, mimetype


def parse_json(env, value):
    if isinstance(value, (dict, list)):
        return value
    if not value:
        return {}
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        raise UserError(env._("The design data is invalid.")) from None


def sanitize_canvas_json(env, canvas_json, max_text_length=0):
    """Return a clean ``{"objects": [...]}`` dict, raising on invalid content."""
    canvas_json = parse_json(env, canvas_json)
    if not isinstance(canvas_json, dict):
        raise UserError(env._("The design data is invalid."))
    objects = canvas_json.get("objects") or []
    if not isinstance(objects, list):
        raise UserError(env._("The design data is invalid."))
    if len(objects) > MAX_OBJECTS_PER_AREA:
        raise UserError(
            env._("A design can contain at most %s elements per area.", MAX_OBJECTS_PER_AREA)
        )
    text_limit = min(max_text_length or MAX_TEXT_CHARS, MAX_TEXT_CHARS)
    clean = []
    for obj in objects:
        if not isinstance(obj, dict):
            raise UserError(env._("The design data is invalid."))
        obj_type = obj.get("type")
        if obj_type not in ALLOWED_OBJECT_TYPES:
            raise UserError(env._("Unsupported design element: %s", obj_type))
        if obj_type in TEXT_TYPES:
            text = obj.get("text")
            if not isinstance(text, str):
                raise UserError(env._("The design data is invalid."))
            if len(text) > text_limit:
                raise UserError(
                    env._("Texts are limited to %s characters.", text_limit)
                )
        if obj_type == "image":
            src = obj.get("src")
            if not isinstance(src, str):
                raise UserError(env._("The design data is invalid."))
            if not (DATA_URL_RE.match(src) or SAFE_SRC_RE.match(_relative_src(src))):
                raise UserError(env._("Images must be uploaded from your device."))
            obj["src"] = src if src.startswith("data:") else _relative_src(src)
            if not isinstance(obj.get("filters", []), list):
                obj.pop("filters")
        clean.append(obj)
    return {"objects": clean}


def extract_artwork(env, canvas, res_model, res_id, name_prefix):
    """Store images embedded as data URLs in ``canvas`` as attachments.

    The original files are kept for production and the JSON stays small: it
    references the attachments with an access token so the design can be
    reopened in the editor. Returns the created attachments.
    """
    max_bytes = max_upload_bytes(env)
    Attachment = env["ir.attachment"].sudo()
    attachments = Attachment
    for index, obj in enumerate(canvas.get("objects", [])):
        src = obj.get("src") if obj.get("type") == "image" else None
        if not src or not DATA_URL_RE.match(src):
            continue
        raw, mimetype = decode_data_url(env, src, max_bytes)
        extension = mimetype.split("/")[1].replace("jpeg", "jpg")
        attachment = Attachment.create({
            "name": f"{name_prefix}-artwork-{index + 1}.{extension}",
            "raw": raw,
            "mimetype": mimetype,
            "res_model": res_model,
            "res_id": res_id,
        })
        attachment.generate_access_token()
        obj["src"] = f"/web/content/{attachment.id}?access_token={attachment.access_token}"
        attachments |= attachment
    return attachments


def check_json_size(env, canvas):
    if len(json.dumps(canvas)) > MAX_JSON_CHARS:
        raise UserError(env._("This design is too large."))


def _relative_src(src):
    """Fabric serializes image URLs as absolute: keep only the local path."""
    return re.sub(r"^https?://[^/]+", "", src)


SVG_NS = "http://www.w3.org/2000/svg"
XLINK_HREF = "{http://www.w3.org/1999/xlink}href"
FORBIDDEN_SVG_TAGS = {"script", "foreignObject", "iframe", "object", "embed", "use"}


def sanitize_svg(env, svg, max_bytes):
    """Strip scripting from an SVG produced by Fabric.js, return bytes."""
    if not svg:
        return False
    data = svg.encode() if isinstance(svg, str) else svg
    if len(data) > max_bytes:
        raise UserError(env._("The print file is too large."))
    parser = etree.XMLParser(resolve_entities=False, no_network=True, huge_tree=True)
    try:
        root = etree.fromstring(data, parser=parser)
    except etree.XMLSyntaxError:
        raise UserError(env._("The print file is invalid.")) from None
    if etree.QName(root).localname != "svg":
        raise UserError(env._("The print file is invalid."))
    for element in list(root.iter()):
        if not isinstance(element.tag, str):  # comments, processing instructions
            element.getparent().remove(element)
            continue
        if etree.QName(element).localname in FORBIDDEN_SVG_TAGS:
            element.getparent().remove(element)
            continue
        for attr in list(element.attrib):
            value = element.attrib[attr].strip().lower()
            name = etree.QName(attr).localname.lower()
            if name.startswith("on"):
                del element.attrib[attr]
            elif name == "href" and not (
                value.startswith("#") or DATA_URL_RE.match(element.attrib[attr].strip())
            ):
                del element.attrib[attr]
            elif "javascript:" in value or "expression(" in value:
                del element.attrib[attr]
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8")
