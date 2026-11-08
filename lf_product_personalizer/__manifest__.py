{
    "name": "Product Personalizer - Online Product Designer, Custom Printing & Engraving",
    "version": "19.0.2.0.0",
    "category": "Website/eCommerce",
    "summary": "Let customers design products online: text, images, clipart, "
    "personalization fees, print-ready artwork and artwork approval.",
    "description": """
Product Personalization Editor
==============================
Let your eCommerce customers personalize products (t-shirts, mugs, engraved gifts,
jerseys, signs...) directly from the product page.

* Design editor with text, images, clipart, shapes, layers and undo/redo. Each
  tool can be turned off per product (e.g. text only for engraving).
* Several design areas per product (front, back, sleeve...) with optional printable zone.
* Reusable design templates shared by many products.
* Personalization fees (per product and per customized area), added to the line price.
* High-resolution PNG and SVG print files, downloadable from the sales order.
* Original uploaded artwork kept as attachments.
* Artwork approval workflow for the production team.
* Designs shown in the cart, customer portal and quotation / order PDF.
* Customers can save designs to their account and share them with a link.
* Ready-made templates (presets), fonts and clipart managed from the backend.
    """,
    "author": "Leofren Technologies",
    "website": "https://leofren.com",
    "depends": ["website_sale"],
    "data": [
        "security/ir.model.access.csv",
        "security/security.xml",
        "data/product_design_font_data.xml",
        "views/product_design_config_views.xml",
        "views/product_design_set_views.xml",
        "views/product_design_font_views.xml",
        "views/product_design_clipart_views.xml",
        "views/product_design_preset_views.xml",
        "views/product_design_saved_views.xml",
        "views/product_template_views.xml",
        "views/sale_order_line_personalization_views.xml",
        "views/sale_order_views.xml",
        "views/res_config_settings_views.xml",
        "views/menus.xml",
        "views/website_templates.xml",
        "views/product_personalized_preview_template.xml",
        "views/cart_templates.xml",
        "views/portal_templates.xml",
        "report/sale_order_report.xml",
    ],
    "demo": [
        "demo/product_demo.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "lf_product_personalizer/static/src/js/utils/fabric_loader.js",
            "lf_product_personalizer/static/src/js/design_area_widget.js",
            "lf_product_personalizer/static/src/xml/design_area_widget.xml",
            "lf_product_personalizer/static/src/backend/color_palette_field.js",
            "lf_product_personalizer/static/src/backend/color_palette_field.xml",
            "lf_product_personalizer/static/src/backend/color_palette_field.scss",
        ],
        "web.assets_frontend": [
            "lf_product_personalizer/static/src/scss/customizer.scss",
            "lf_product_personalizer/static/src/js/utils/fabric_loader.js",
            "lf_product_personalizer/static/src/js/utils/dom_utils.js",
            "lf_product_personalizer/static/src/js/utils/font_loader.js",
            "lf_product_personalizer/static/src/js/utils/object_utils.js",
            "lf_product_personalizer/static/src/js/utils/preview_generator.js",
            "lf_product_personalizer/static/src/js/core/canvas_manager.js",
            "lf_product_personalizer/static/src/js/core/history_manager.js",
            "lf_product_personalizer/static/src/js/core/state_manager.js",
            "lf_product_personalizer/static/src/js/handlers/text_handler.js",
            "lf_product_personalizer/static/src/js/handlers/image_handler.js",
            "lf_product_personalizer/static/src/js/handlers/shape_handler.js",
            "lf_product_personalizer/static/src/js/handlers/layer_handler.js",
            "lf_product_personalizer/static/src/js/ui/menu_controller.js",
            "lf_product_personalizer/static/src/js/ui/controls_updater.js",
            "lf_product_personalizer/static/src/js/product_customizer.js",
            "lf_product_personalizer/static/src/js/personalize_button.js",
            "lf_product_personalizer/static/src/js/portal_designs.js",
        ],
        "web.assets_tests": [
            "lf_product_personalizer/static/tests/tours/*.js",
        ],
    },
    "images": ["static/description/banner/lf_product_personalizer_cover.png"],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
