# -*- coding: utf-8 -*-
import base64
from io import StringIO, BytesIO
from datetime import datetime, date
from collections import defaultdict
from odoo import api, fields, models, _

ENCODING = "cp1252"  # Windows-1252 as per spec

def _clean(s):
    if s is None:
        return ""
    return str(s).replace("\n", " ").replace("\r", " ").strip()

def _fw_text(v, width):
    s = _clean(v)
    if len(s) > width:
        return s[:width]
    return s.ljust(width, " ")

def _fw_num(value, width, decimals=0, allow_negative=True):
    try:
        n = float(value or 0.0)
    except Exception:
        n = 0.0
    # Keep sign for negatives
    sign = "-" if (allow_negative and n < 0) else ""
    n_abs = abs(n)
    if decimals > 0:
        fmt = f"{{:0{width - (1 if sign else 0)}.{decimals}f}}"
    else:
        fmt = f"{{:0{width - (1 if sign else 0)}.0f}}"
    s = fmt.format(n_abs)
    s = sign + s
    if len(s) > width:
        s = s[-width:]
    return s

def _dz4(v, width):
    return _fw_num(v, width, decimals=4)

def _dz5(v, width):
    return _fw_num(v, width, decimals=5)

def _num(v, width):
    return _fw_num(v, width, decimals=0)

def _today():
    now = datetime.now()
    return now.strftime("%Y%m%d"), now.strftime("%H%M"), now.strftime("%Y%m%d%H%M")

class Z14GedatExportWizard(models.TransientModel):
    _name = "z14.gedat.export.wizard"
    _description = "GEDAT Export Wizard (z14)"

    date_from = fields.Date(required=True, default=lambda self: date.today().replace(day=1))
    date_to   = fields.Date(required=True, default=lambda self: date.today())
    only_posted = fields.Boolean(string="Only Posted Invoices", default=True)
    move_types = fields.Selection([
        ('out_invoice', 'Customer Invoice'),
        ('out_refund', 'Customer Credit Note'),
        ('both', 'Both')],
        default='both', string="Invoice Types")
    meldeeinheit = fields.Selection([('01','01 - VKE'),('02','02 - Füllungen'),('03','03 - Hektoliter')], default='02', required=True)
    seq_number = fields.Integer(string="Sequence No. (8-stellig)", default=1, help="Durchnummerierung der Datenübertragungen (fill to 8 digits)")

    kunden_file   = fields.Binary(readonly=True)
    kunden_fname  = fields.Char(readonly=True)
    bwg_file      = fields.Binary(readonly=True)
    bwg_fname     = fields.Char(readonly=True)

    def action_export(self):
        self.ensure_one()
        kunden_bytes = self._build_kunden_bytes()
        bwg_bytes = self._build_bwg_bytes()

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.kunden_file  = base64.b64encode(kunden_bytes)
        self.kunden_fname = f"KUNDEN_{ts}.TXT"
        self.bwg_file     = base64.b64encode(bwg_bytes)
        self.bwg_fname    = f"BWG_{ts}.TXT"
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "view_mode": "form",
            "res_id": self.id,
            "target": "new",
        }

    # ---------------------
    # KUNDEN.TXT per spec
    # ---------------------
    def _kunden_line(self, vals):
        # Build per exact field list (total length 407)
        parts = []
        # 01 Satzart (2) -> "01"
        parts.append(_fw_text("01", 2))
        # 02 Version (2) -> "02"
        parts.append(_fw_text("02", 2))
        # 03 Teilnehmer-Nr GFGH (8)
        parts.append(_fw_text(vals.get("teilnehmer"), 8))
        # 04 Kunden-Nr (13)
        parts.append(_fw_text(vals.get("kunden_nr"), 13))
        # 05 GLN des Kunden (13)
        parts.append(_fw_text(vals.get("gln"), 13))
        # 06 Geschäftstyp (30)
        parts.append(_fw_text(vals.get("biztype"), 30))
        # 07 Name-1 (40)
        parts.append(_fw_text(vals.get("name1"), 40))
        # 08 Name-2 (40)
        parts.append(_fw_text(vals.get("name2"), 40))
        # 09 Straße-1 (40)
        parts.append(_fw_text(vals.get("street1"), 40))
        # 10 PLZ (15)
        parts.append(_fw_text(vals.get("zip"), 15))
        # 11 Ort (30)
        parts.append(_fw_text(vals.get("city"), 30))
        # 12 Land (3)
        parts.append(_fw_text(vals.get("country"), 3))
        # 13 Telefon-1 (20)
        parts.append(_fw_text(vals.get("phone1"), 20))
        # 14 Telefon-2 (20)
        parts.append(_fw_text(vals.get("phone2"), 20))
        # 15 Telefax (20)
        parts.append(_fw_text(vals.get("fax"), 20))
        # 16 Erstellungsdatum (8) YYYYMMDD
        parts.append(_fw_text(vals.get("date"), 8))
        # 17 Erstellungszeit (4) HHMM
        parts.append(_fw_text(vals.get("time"), 4))
        # 18 Zentrale/Schiene (13)
        parts.append(_fw_text(vals.get("chain"), 13))
        # 19 Steuernummer (20)
        parts.append(_fw_text(vals.get("tax"), 20))
        # 20 E-Mail (50)
        parts.append(_fw_text(vals.get("email"), 50))
        # 21 Filial-Nr. (13)
        parts.append(_fw_text(vals.get("branch_no"), 13))
        # 22 Mitglieds-Nr. (13)
        parts.append(_fw_text(vals.get("member_no"), 13))
        # 23 Straße-2 (40)
        parts.append(_fw_text(vals.get("street2"), 40))
        # 24 Postfach (15)
        parts.append(_fw_text(vals.get("po_box"), 15))
        # 25 Kundentyp-Kennzeichen (30)
        parts.append(_fw_text(vals.get("ctype"), 30))
        # 26 Status (1) N/A/L/K
        parts.append(_fw_text(vals.get("status", "K"), 1))
        # 27 Sonstiges/Memo (40) -> blank per spec
        parts.append(_fw_text("", 40))
        # 28 GLN/ILN Absender (13) or 8-digit Teilnehmer-Nr
        parts.append(_fw_text(vals.get("sender_gln"), 13))
        line = "".join(parts)
        # Ensure length 407
        if len(line) != 407:
            # pad or trim
            if len(line) < 407:
                line = line + (" " * (407 - len(line)))
            else:
                line = line[:407]
        return line

    def _build_kunden_bytes(self):
        self.ensure_one()
        teilnehmer = self.env["z14.gedat.manufacturer"].z14_get_our_company_gedat_code()
        sender_gln = self.env["z14.gedat.manufacturer"].z14_get_our_company_gln()
        d, t, dt = _today()

        domain = [("move_type", "in", ("out_invoice","out_refund"))]
        if self.only_posted:
            domain += [("state","=","posted")]
        if self.date_from:
            domain += [("invoice_date", ">=", self.date_from)]
        if self.date_to:
            domain += [("invoice_date", "<=", self.date_to)]
        moves = self.env["account.move"].search(domain)
        partners = moves.mapped("partner_id")

        lines = []
        for p in partners:
            vals = {
                "teilnehmer": teilnehmer,
                "kunden_nr": p.ref or str(p.id),
                "gln": "",  # unknown
                "biztype": "",
                "name1": p.name or "",
                "name2": getattr(p, "parent_id", False) and (p.parent_id.name or "") or "",
                "street1": p.street or "",
                "zip": p.zip or "",
                "city": p.city or "",
                "country": (p.country_id and p.country_id.code) or "DE",
                "phone1": p.phone or "",
                "phone2": p.mobile or "",
                "fax": p.fax or "",
                "date": d,
                "time": t,
                "chain": "",
                "tax": p.vat or "",
                "email": p.email or "",
                "branch_no": "",
                "member_no": "",
                "street2": p.street2 or "",
                "po_box": "",
                "ctype": "01",  # default Warenempfänger
                "status": "K",
                "sender_gln": sender_gln or teilnehmer,
            }
            line = self._kunden_line(vals)
            lines.append(line)
        content = "\r\n".join(lines)
        return content.encode(ENCODING, errors="replace")

    # ---------------------
    # BWG.TXT per spec
    # ---------------------
    def _bwg_line(self, V):
        parts = []
        # Field widths per spec; total 407
        parts.append(_fw_text("20", 2))                    # 1 Satzart
        parts.append(_fw_text("02", 2))                    # 2 Version
        parts.append(_fw_text(V["teilnehmer_gfgh"], 8))    # 3 GFGH
        parts.append(_fw_text(V["teilnehmer_her"], 8))     # 4 Hersteller
        parts.append(_fw_text(V["auslieferer"], 13))       # 5
        parts.append(_fw_text(V["warenempf"], 13))         # 6
        parts.append(_fw_text(V["rechempf"], 13))          # 7
        parts.append(_fw_text(V["gtin"], 15))              # 8
        parts.append(_fw_text(V["artid_her"], 15))         # 9
        parts.append(_fw_text(V["artid_gfgh"], 15))        # 10
        parts.append(_fw_text(V["artbez"], 70))            # 11
        parts.append(_fw_text(V["fuellungen"], 6))         # 12 TXT (we send number as text)
        parts.append(_dz5(V["inhalt"], 8))                 # 13 DZ5
        parts.append(_fw_text(V["von"], 8))                # 14
        parts.append(_fw_text(V["bis"], 8))                # 15
        parts.append(_dz4(V["abs_norm"], 15))              # 16
        parts.append(_dz4(V["abs_aktion"], 15))            # 17
        parts.append(_dz4(V["abs_gratis"], 15))            # 18
        parts.append(_dz4(V["abs_gesamt"], 15))            # 19
        parts.append(_num(V["anz_lief"], 4))               # 20
        parts.append(_fw_text(V["melde"], 2))              # 21
        parts.append(_dz4(V["liters"], 15))                # 22
        parts.append(_dz4(V["fillings"], 15))              # 23
        parts.append(_fw_text(V["art_abs"], 2))            # 24
        parts.append(_fw_text(V["lager"], 13))             # 25
        parts.append(_fw_text(V["schiene"], 13))           # 26
        parts.append(_fw_text(V["kunden_nr_her"], 13))     # 27
        parts.append(_fw_text(V["datenursprung"], 2))      # 28
        parts.append(_fw_text(V["meldezeitraum"], 2))      # 29
        parts.append(_fw_text(V["kw"], 6))                 # 30
        parts.append(_fw_text(V["faktura"], 8))            # 31
        parts.append(_fw_text(V["anlief"], 8))             # 32
        parts.append(_fw_text(V["sales_inout"], 2))        # 33
        d,t,dt = _today()
        parts.append(_fw_text(d, 8))                       # 34
        parts.append(_fw_text(t, 4))                       # 35
        parts.append(_fw_text(V["gln_abs"], 13))           # 36
        parts.append(_fw_text(V["gln_empf"], 13))          # 37
        line = "".join(parts)
        if len(line) != 407:
            if len(line) < 407:
                line = line + (" " * (407 - len(line)))
            else:
                line = line[:407]
        return line

    def _build_bwg_bytes(self):
        self.ensure_one()
        teilnehmer = self.env["z14.gedat.manufacturer"].z14_get_our_company_gedat_code()
        sender_gln = self.env["z14.gedat.manufacturer"].z14_get_our_company_gln()
        d, t, dt = _today()

        # Build aggregation per month boundaries
        # Enforce monthly range per spec (JJJJMM01..JJJJMMUltimo)
        date_from = self.date_from or date.today().replace(day=1)
        date_to = self.date_to or date.today()
        # domain for moves
        domain = [("move_type","in",("out_invoice","out_refund"))]
        if self.move_types != "both":
            domain = [("move_type","=", self.move_types)]
        if self.only_posted:
            domain += [("state","=","posted")]
        domain += [("invoice_date", ">=", date_from), ("invoice_date", "<=", date_to)]
        moves = self.env["account.move"].search(domain)

        # Group lines by (manufacturer code, partner, product)
        agg = defaultdict(lambda: {"qty":0.0, "deliveries":0, "products": set(), "moves": set()})
        for mv in moves:
            for line in mv.invoice_line_ids:
                prod = line.product_id
                if not prod:
                    continue
                tmpl = prod.product_tmpl_id
                man = tmpl.z14_gedat_man_id
                man_code = (man and (man.code or "").strip()) or ""
                if not man_code:
                    # skip if no manufacturer target (cannot route to Hersteller)
                    continue
                key = (man_code, mv.partner_id.id, prod.id)
                rec = agg[key]
                rec["qty"] += float(line.quantity or 0.0)
                rec["products"].add(prod.id)
                rec["moves"].add(mv.id)
                rec["deliveries"] += 1

        # Compose lines
        lines = []
        total_lines = 1  # header included later
        for (man_code, partner_id, product_id), rec in agg.items():
            partner = self.env["res.partner"].browse(partner_id)
            product = self.env["product.product"].browse(product_id)
            tmpl = product.product_tmpl_id
            fillings = (tmpl.z14_gedat_unitcount or 0) * rec["qty"]
            litres = fillings * (tmpl.z14_gedat_unitvol or 0.0)
            abs_norm = fillings  # we report in Füllungen for ME=02
            abs_gesamt = abs_norm  # since no aktion/gratis split here

            V = dict(
                teilnehmer_gfgh = teilnehmer,
                teilnehmer_her = man_code,
                auslieferer = partner.ref or str(partner.id),
                warenempf = partner.ref or str(partner.id),
                rechempf = partner.ref or str(partner.id),
                gtin = product.barcode or "",
                artid_her = (tmpl.z14_gedat_vendcode or "")[:15],
                artid_gfgh = product.default_code or "",
                artbez = product.display_name or "",
                fuellungen = str(tmpl.z14_gedat_unitcount or 0),
                inhalt = tmpl.z14_gedat_unitvol or 0.0,
                von = date_from.strftime("%Y%m%d"),
                bis = date_to.strftime("%Y%m%d"),
                abs_norm = abs_norm,
                abs_aktion = 0.0,
                abs_gratis = 0.0,
                abs_gesamt = abs_gesamt,
                anz_lief = max(1, rec["deliveries"]),
                melde = self.meldeeinheit,  # default 02
                liters = litres,
                fillings = fillings,
                art_abs = "01",  # fakturierter Absatz an LEH/Gastro/GAM
                lager = teilnehmer,  # if no separate Auslieferungslager -> own id
                schiene = "",
                kunden_nr_her = "",  # unknown mapping
                datenursprung = "01",  # Fakturadatei
                meldezeitraum = "03",  # Monat
                kw = "",  # not used for month
                faktura = "",  # optional for month
                anlief = "",  # optional for month
                sales_inout = "01",
                gln_abs = sender_gln or teilnehmer,
                gln_empf = "",  # unknown, left blank
            )
            line = self._bwg_line(V)
            lines.append(line)
            total_lines += 1

        # Header line: KP;SLSRPT;GFGHID;SEQ;LINECOUNT;YYYYMMDDHHMM
        header = "KP;SLSRPT;{g};{seq};{cnt};{ts}".format(
            g=(teilnehmer or "").zfill(8)[:8],
            seq=str(self.seq_number).zfill(8)[:8],
            cnt=str(total_lines),
            ts=d + t
        )
        content = header + "\r\n" + ("\r\n".join(lines) if lines else "")
        return content.encode(ENCODING, errors="replace")
