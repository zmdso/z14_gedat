# -*- coding: utf-8 -*-
{
    "name": "Z14 GEDAT",
    "version": "19.0.1.0.0",
    "summary": "GEDAT getDATA exports (KUNDEN/BWG) with manufacturer & product fields",
    "category": "Accounting/Invoicing",
    "author": "z14",
    "license": "LGPL-3",
    "depends": ["base", "product", "account"],
    "data": [
        "security/ir.model.access.csv",
        "views/z14_views_menus.xml",
        "views/z14_view_manufacturer.xml",
        "views/z14_view_product.xml",
        "views/z14_view_account_move_line.xml",
        "wizard/z14_wizard_export.xml"
    ],
    "installable": True,
    "application": True
}
