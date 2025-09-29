# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class Z14GedatManufacturer(models.Model):
    _name = "z14.gedat.manufacturer"
    _description = "GEDAT Manufacturer (z14)"
    _order = "name"

    name = fields.Char(required=True)
    code = fields.Char(
        string="GEDAT Teilnehmer-Nr (8-st.)",
        help="8-digit GEDAT participant number (GFGH/Hersteller)",
    )
    is_our_company_code = fields.Boolean(
        string="This is our own GEDAT code",
        help="Marks this record as OUR company's GEDAT identification.",
    )

    @api.model
    def z14_get_our_company_gedat_code(self):
        rec = self.search([("is_our_company_code", "=", True)], limit=1)
        return (rec.code or "").strip() if rec else ""


class ProductTemplate(models.Model):
    _inherit = "product.template"

    # 4 GEDAT fields (template)
    z14_gedat_man_id = fields.Many2one(
        "z14.gedat.manufacturer",
        string="GEDAT Manufacturer",
        help="Manufacturer mapping for GEDAT exports.",
    )
    z14_gedat_vendcode = fields.Char(
        string="Manufacturer Article Code",
        help="Hersteller-Artikel-ID used in BWG.",
    )
    z14_gedat_unitcount = fields.Integer(
        string="Units per Pack (Füllungen)",
        default=0,
        help="Anzahl je Gebinde (bottles per case).",
    )
    z14_gedat_unitvol = fields.Float(
        string="Unit Volume (L)",
        digits=(16, 3),
        default=0.0,
        help="Inhalt je Füllung in Litern (0.000).",
    )

    # Backward compatibility: total litre per pack (computed)
    z14_gedat_vol = fields.Float(
        string="Volume per Pack (L)",
        digits=(16, 3),
        compute="_compute_z14_vol",
        store=True,
        help="Computed as Units per Pack × Unit Volume (L).",
    )

    @api.depends("z14_gedat_unitcount", "z14_gedat_unitvol")
    def _compute_z14_vol(self):
        for rec in self:
            rec.z14_gedat_vol = (rec.z14_gedat_unitcount or 0) * (rec.z14_gedat_unitvol or 0.0)


class ProductProduct(models.Model):
    _inherit = "product.product"

    z14_gedat_man_id = fields.Many2one(
        related="product_tmpl_id.z14_gedat_man_id",
        store=True, readonly=False,
    )
    z14_gedat_vendcode = fields.Char(
        related="product_tmpl_id.z14_gedat_vendcode",
        store=True, readonly=False,
    )
    z14_gedat_unitcount = fields.Integer(
        related="product_tmpl_id.z14_gedat_unitcount",
        store=True, readonly=False,
    )
    z14_gedat_unitvol = fields.Float(
        related="product_tmpl_id.z14_gedat_unitvol",
        store=True, readonly=False,
    )
    z14_gedat_vol = fields.Float(
        related="product_tmpl_id.z14_gedat_vol",
        store=True, readonly=False,
    )
