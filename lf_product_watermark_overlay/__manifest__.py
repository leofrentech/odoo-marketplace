{
    "name": "Product Image Watermark Overlay",
    "version": "18.0.2.2.0",
    "category": "Sales/Sales",
    "summary": "Add your logo or text as a watermark on product images.",
    "description": """
Product Image Watermark Overlay
===============================
Adds your logo or a line of text as a watermark on product images.

Configure a company-wide watermark from Settings (logo or text, position,
size, opacity, and font and color for text) with a live preview. Only
products ticked "Eligible for Watermark" are watermarked, and that box is
unticked by default, so enabling the feature never changes your whole
catalog at once.

New photos uploaded to eligible products are watermarked automatically,
and "Regenerate All Images" backfills existing photos in the background.
The "Add/Update Watermark" button on a product applies a one-off custom
watermark to all of its images, with a live preview, and "Remove
Watermark" restores the originals.

The untouched original photo is always kept, so watermarks never stack
and can be changed or removed at any time. Images keep their own file
format (JPEG, PNG or WebP); GIF and SVG images are left untouched.
    """,
    "website": "https://leofren.com",
    "author": "Leofren Technologies",
    "support": "contact@leofren.com",
    "depends": ["base_setup", "product"],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_cron_data.xml",
        "wizard/product_template_watermark_views.xml",
        "views/res_config_settings_views.xml",
        "views/product_template_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
    "images": ["static/description/banner/lf_product_watermark_overlay_cover.png"],
    "license": "LGPL-3",
}
