# -*- coding: utf-8 -*-
{
    'name': 'Zapier RPC Compatibility',
    'version': '17.0.1.0.1',
    'category': 'Extra Tools',
    'summary': 'Accepts a legacy search() call shape some XML-RPC clients still send',
    'description': """
Zapier RPC Compatibility
=========================
Zapier's "Odoo ERP Self Hosted" app (and possibly other legacy XML-RPC
clients) calls search() with an extra leading placeholder argument before
the domain, followed by offset, limit, order and context - a shape that
worked without error through Odoo 16. Odoo 17 removed the count parameter
from search()'s signature, so that trailing context dict now overflows the
positional arguments and raises TypeError: BaseModel.search() takes from
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
