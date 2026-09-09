# -*- coding: utf-8 -*-
{
    'name': 'Zapier RPC Compatibility',
    'version': '17.0.1.0.0',
    'category': 'Extra Tools',
    'summary': 'Accepts the legacy pre-v8 search() calling convention some XML-RPC clients still use',
    'description': """
Zapier RPC Compatibility
=========================
Zapier's "Odoo ERP Self Hosted" app (and other legacy XML-RPC clients) still
call search() using the pre-v8 convention where context was a positional
argument: search(domain, offset, limit, order, context[, count]). Modern
Odoo no longer accepts context positionally at all, so that dict lands in
search()'s count slot and raises TypeError: BaseModel.search() takes from
2 to 5 positional arguments but 6 were given.

This module patches base.search() to detect that legacy shape and translate
it, rather than erroring - without changing behavior for any normal call.
    """,
    'author': 'Leofren Technologies',
    'website': 'https://leofren.com',
    'support': 'contact@leofren.com',
    'depends': ['base'],
    'images': ['static/description/banner/lf_zapier_compat_cover_light.gif'],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
