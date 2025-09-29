# -*- coding: utf-8 -*-
from odoo import api, fields, models

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    z14_gedat_fillings = fields.Float(
        string="GEDAT Fillings",
        compute="_compute_z14_gedat_quantities",
        store=True,
        help="quantity × product template Units per Pack"
    )
    z14_gedat_litres = fields.Float(
        string="GEDAT Litres",
        compute="_compute_z14_gedat_quantities",
        store=True,
        help="Fillings × product template Unit Volume (L)"
    )
    z14_gedat_hl = fields.Float(
        string="GEDAT HL",
        compute="_compute_z14_gedat_quantities",
        store=True,
        help="Litres / 100"
    )

    @api.depends(
        "quantity",
        "product_id",
        "product_id.product_tmpl_id.z14_gedat_unitcount",
        "product_id.product_tmpl_id.z14_gedat_unitvol",
    )
    def _compute_z14_gedat_quantities(self):
        for line in self:
            qty = line.quantity or 0.0
            tmpl = line.product_id.product_tmpl_id if line.product_id else None
            unitcount = tmpl.z14_gedat_unitcount if tmpl else 0
            unitvol = tmpl.z14_gedat_unitvol if tmpl else 0.0
            fillings = qty * (unitcount or 0)
            litres = fillings * (unitvol or 0.0)
            line.z14_gedat_fillings = fillings
            line.z14_gedat_litres = litres
            line.z14_gedat_hl = litres / 100.0 if litres else 0.0

    @api.onchange("product_id", "quantity")
    def _onchange_z14_refresh_gedat(self):
        for line in self:
            _ = (line.z14_gedat_fillings, line.z14_gedat_litres, line.z14_gedat_hl)

