{
    "name": "z14_gedat",
    "version": "19.0.1.0.0",
    "summary": "GEDAT getDATA integration",
    "description": "z14 GEDAT export for Odoo 19 with fixed-width files per spec. Adds manufacturer, product fields and export wizard.",
    "category": "Accounting/Invoicing",
    "author": "z14",
    "license": "LGPL-3",
    "depends": ["base", "product", "account"],
    "data": [
        "security/ir.model.access.csv",
        "views/z14_views_menus.xml",
        "views/z14_view_manufacturer.xml",
        "views/z14_view_product.xml",
        "wizard/z14_wizard_export.xml"
    ],
    "installable": True,
    "application": True
}
