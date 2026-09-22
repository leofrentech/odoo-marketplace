{
    "name": "Product Image Watermark Overlay",
    "version": "19.0.2.0.0",
    "summary": "Adds watermark overlay on product images.",
    "website": "https://leofren.com",
    "author": "Leofren Technologies",
    "depends": ["base_setup", "product"],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_cron_data.xml",
        "wizard/product_watermark_wizard_views.xml",
        "views/res_config_settings_views.xml",
        "views/product_template_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
    "license": "LGPL-3",
}
