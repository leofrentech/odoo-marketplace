# -*- coding: utf-8 -*-
{
    'name': 'Product QR Track',
    'version': '17.0.1.0.1',
    'category': 'Website/eCommerce',
    'summary': 'Adds QR code to track the customer analytics.',
    'description': """
Product QR Track
=================
Generates a unique, scannable QR code for every product variant and lets
you print it directly onto small (25mm x 25mm) labels from the standard
"Print Labels" wizard.

Scanning a QR code redirects the customer straight to that variant's page
on your website, while logging the visit - IP, city, country, browser and
OS - against the exact variant that was scanned.

Track scan activity from a dedicated "QR Visits" menu (list and graph
views, with a "Visited Today" filter and grouping by country, OS or
browser), or jump straight to a product's own visits from the "QR Visits"
smart button on its form.
    """,
    'author': 'Leofren Technologies',
    'website': 'https://leofren.com',
    'support': 'contact@leofren.com',
    'depends': ['website_sale'],
    'data': [
        'security/ir.model.access.csv',
        'data/report_paperformat_data.xml',
        'views/product_product_views.xml',
        'views/product_template_views.xml',
        'views/product_qr_visit_views.xml',
        'report/product_qr_track_templates.xml',
        'report/product_qr_track_reports.xml',
    ],
    'images': ['static/description/banner/product_qr_track_cover_light.gif'],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
