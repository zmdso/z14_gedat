# -*- coding: utf-8 -*-
import base64
from io import StringIO
from datetime import datetime, date
from collections import defaultdict
from odoo import api, fields, models, _

ENCODING = "cp1252"  # Windows-1252

def _today():
    now = datetime.now()
    return now.strftime("%Y%m%d"), now.strftime("%H%M")

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
    sign = "-" if (allow_negative and n < 0) else ""
    n_abs = abs(n)
    if decimals > 0:
        fmt = f"{{:0{width - (1 if sign else 0)}.{decimals}f}}"
    else:
        fmt = f"{{:0{width - (1 if sign else 0)}.0f}}"
    s = sign + fmt.format(n_abs)
    if len(s) > width:
        s = s[-width:]
    return s

def _dz4(v, w): return _fw_num(v, w, 4)
def _dz5(v, w): return _fw_num(v, w, 5)
def _num(v, w): return _fw_num(v, w, 0)

def _kundennr(partner):
    try:
        return f"{int(partner.id):05d}"
    except Exception:
        return str(partner.id)

class Z14GedatExportWizard(models.TransientModel):
    _name = "z14.gedat.export.wizard"
    _description = "GEDAT Export Wizard (z14)"

    date_from = fields.Date(required=True, default=lambda self: date.today().replace(day=1))
    date_to   = fields.Date(required=True, default=lambda self: date.today())
    only_posted = fields.Boolean(string="Only Posted Invoices", default=True)
    move_types = fields.Selection([
        ('out_invoice', 'Customer Invoice'),
        ('out_refund', 'Customer Credit Note'),
        ('both', 'Both'),
    ], default='both', string="Invoice Types")
    meldeeinheit = fields.Selection([('01','01 - VKE'),('02','02 - Füllungen'),('03','03 - Hektoliter')], default='02', required=True)
    seq_number = fields.Integer(string="Sequence No. (8 digits)", default=1)

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

    # ---------- KUNDEN.TXT (fixed-width 407) ----------
    def _kunden_line(self, vals):
        parts = []
        parts.append(_fw_text("01", 2))                    # Satzart
        parts.append(_fw_text("02", 2))                    # Version
        parts.append(_fw_text(vals.get("teilnehmer"), 8))  # Teilnehmer-Nr GFGH
        parts.append(_fw_text(vals.get("kunden_nr"), 13))  # Kundennummer
        parts.append(_fw_text(vals.get("gln"), 13))        # GLN des Kunden (boş kalabilir)
        parts.append(_fw_text(vals.get("biztype"), 30))    # Geschäftstyp
        parts.append(_fw_text(vals.get("name1"), 40))      # Name-1
        parts.append(_fw_text(vals.get("name2"), 40))      # Name-2
        parts.append(_fw_text(vals.get("street1"), 40))    # Straße-1
        parts.append(_fw_text(vals.get("zip"), 15))        # PLZ
        parts.append(_fw_text(vals.get("city"), 30))       # Ort
        parts.append(_fw_text(vals.get("country"), 3))     # Land
        parts.append(_fw_text(vals.get("phone1"), 20))     # Telefon-1
        parts.append(_fw_text(vals.get("phone2"), 20))     # Telefon-2
        parts.append(_fw_text(vals.get("fax"), 20))        # Telefax
        parts.append(_fw_text(vals.get("date"), 8))        # Erstellungsdatum YYYYMMDD
        parts.append(_fw_text(vals.get("time"), 4))        # Erstellungszeit HHMM
        parts.append(_fw_text(vals.get("chain"), 13))      # Zentrale/Schiene
        parts.append(_fw_text(vals.get("tax"), 20))        # Steuernummer
        parts.append(_fw_text(vals.get("email"), 50))      # E-Mail
        parts.append(_fw_text(vals.get("branch_no"), 13))  # Filial-Nr
        parts.append(_fw_text(vals.get("member_no"), 13))  # Mitglieds-Nr
        parts.append(_fw_text(vals.get("street2"), 40))    # Straße-2
        parts.append(_fw_text(vals.get("po_box"), 15))     # Postfach
        parts.append(_fw_text(vals.get("ctype"), 30))      # Kundentyp
        parts.append(_fw_text(vals.get("status"), 1))      # Status
        parts.append(_fw_text("", 40))                     # Sonstiges/Memo
        parts.append(_fw_text(vals.get("sender_id"), 13))  # Absender (GLN veya Teilnehmer-Nr)
        line = "".join(parts)
        if len(line) != 407:
            line = (line + " " * 407)[:407]
        return line

    def _build_kunden_bytes(self):
        teilnehmer = self.env["z14.gedat.manufacturer"].z14_get_our_company_gedat_code()
        d, t = _today()

        domain = [("move_type","in",("out_invoice","out_refund"))]
        if self.move_types != "both":
            domain = [("move_type","=", self.move_types)]
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
                "teilnehmer": teilnehmer or "",
                "kunden_nr": _kundennr(p),
                "gln": "",  # kullanmıyoruz
                "biztype": "",
                "name1": p.name or "",
                "name2": p.parent_id.name if p.parent_id else "",
                "street1": p.street or "",
                "zip": p.zip or "",
                "city": p.city or "",
                "country": (p.country_id.code or "") if p.country_id else "DE",
                "phone1": p.phone or "",
                "phone2": p.mobile or "",
                "fax": p.fax or "",
                "date": d, "time": t,
                "chain": "",
                "tax": p.vat or "",
                "email": p.email or "",
                "branch_no": "",
                "member_no": "",
                "street2": p.street2 or "",
                "po_box": "",
                "ctype": "01",
                "status": "K",
                "sender_id": teilnehmer or "",
            }
            lines.append(self._kunden_line(vals))
        content = "\r\n".join(lines)
        return content.encode(ENCODING, errors="replace")

    # ---------- BWG.TXT (header + fixed-width 407) ----------
    def _bwg_line(self, V):
        parts = []
        parts.append(_fw_text("20", 2))                    # Satzart
        parts.append(_fw_text("02", 2))                    # Version
        parts.append(_fw_text(V["teilnehmer_gfgh"], 8))    # GFGH
        parts.append(_fw_text(V["teilnehmer_her"], 8))     # Hersteller
        parts.append(_fw_text(V["auslieferer"], 13))       # Auslieferer
        parts.append(_fw_text(V["warenempf"], 13))         # Warenempfänger
        parts.append(_fw_text(V["rechempf"], 13))          # Rechnungsempfänger
        parts.append(_fw_text(V["gtin"], 15))              # GTIN
        parts.append(_fw_text(V["artid_her"], 15))         # Hersteller-Artikel-ID
        parts.append(_fw_text(V["artid_gfgh"], 15))        # GFGH-Artikel-ID
        parts.append(_fw_text(V["artbez"], 70))            # Artikelbezeichnung
        parts.append(_fw_text(V["fuellungen"], 6))         # Füllungen (Text)
        parts.append(_dz5(V["inhalt"], 8))                 # Inhalt je Füllung (DZ5)
        parts.append(_fw_text(V["von"], 8))                # Von (YYYYMMDD)
        parts.append(_fw_text(V["bis"], 8))                # Bis (YYYYMMDD)
        parts.append(_dz4(V["abs_norm"], 15))              # Absatz normal
        parts.append(_dz4(V["abs_aktion"], 15))            # Absatz Aktion
        parts.append(_dz4(V["abs_gratis"], 15))            # Absatz Gratis
        parts.append(_dz4(V["abs_gesamt"], 15))            # Absatz gesamt
        parts.append(_num(V["anz_lief"], 4))               # Anzahl Lieferungen
        parts.append(_fw_text(V["melde"], 2))              # Meldeeinheit
        parts.append(_dz4(V["liters"], 15))                # Liter gesamt
        parts.append(_dz4(V["fillings"], 15))              # Füllungen gesamt
        parts.append(_fw_text(V["art_abs"], 2))            # Art des Absatzes
        parts.append(_fw_text(V["lager"], 13))             # Lager
        parts.append(_fw_text(V["schiene"], 13))           # Schiene
        parts.append(_fw_text(V["kunden_nr_her"], 13))     # Kundennr beim Hersteller
        parts.append(_fw_text(V["datenursprung"], 2))      # Datenursprung
        parts.append(_fw_text(V["meldezeitraum"], 2))      # Meldezeitraum
        parts.append(_fw_text(V["kw"], 6))                 # Kalenderwoche
        parts.append(_fw_text(V["faktura"], 8))            # Fakturadatum
        parts.append(_fw_text(V["anlief"], 8))             # Anlieferdatum
        parts.append(_fw_text(V["sales_inout"], 2))        # Absatzrichtung
        d, t = _today()
        parts.append(_fw_text(d, 8))                       # Erstellungsdatum
        parts.append(_fw_text(t, 4))                       # Erstellungszeit
        parts.append(_fw_text(V["gln_abs"], 13))           # GLN/ILN Absatzender (bizde Teiln-Nr)
        parts.append(_fw_text(V["gln_empf"], 13))          # GLN/ILN Empfänger
        line = "".join(parts)
        if len(line) != 407:
            line = (line + " " * 407)[:407]
        return line

    def _build_bwg_bytes(self):
        teilnehmer = self.env["z14.gedat.manufacturer"].z14_get_our_company_gedat_code()
        d, t = _today()

        date_from = self.date_from or date.today().replace(day=1)
        date_to = self.date_to or date.today()

        domain = [("move_type","in",("out_invoice","out_refund"))]
        if self.move_types != "both":
            domain = [("move_type","=", self.move_types)]
        if self.only_posted:
            domain += [("state","=","posted")]
        domain += [("invoice_date", ">=", date_from), ("invoice_date", "<=", date_to)]
        moves = self.env["account.move"].search(domain)

        agg = defaultdict(lambda: {"qty":0.0, "deliveries":0})
        for mv in moves:
            for ln in mv.invoice_line_ids:
                prod = ln.product_id
                if not prod:
                    continue
                tmpl = prod.product_tmpl_id
                man = tmpl.z14_gedat_man_id
                man_code = (man and (man.code or "").strip()) or ""
                if not man_code:
                    continue  # manufacturer zorunlu
                key = (man_code, mv.partner_id.id, prod.id)
                rec = agg[key]
                rec["qty"] += float(ln.quantity or 0.0)
                rec["deliveries"] += 1

        data_lines = []
        for (man_code, partner_id, product_id), rec in agg.items():
            partner = self.env["res.partner"].browse(partner_id)
            product = self.env["product.product"].browse(product_id)
            tmpl = product.product_tmpl_id

            fillings = (tmpl.z14_gedat_unitcount or 0) * rec["qty"]
            litres = fillings * (tmpl.z14_gedat_unitvol or 0.0)

            V = dict(
                teilnehmer_gfgh = (teilnehmer or "")[:8],
                teilnehmer_her = (man_code or "")[:8],
                auslieferer = _kundennr(partner),
                warenempf = _kundennr(partner),
                rechempf = _kundennr(partner),
                gtin = (product.barcode or "")[:15],
                artid_her = (tmpl.z14_gedat_vendcode or "")[:15],
                artid_gfgh = (product.default_code or "")[:15],
                artbez = (product.display_name or "")[:70],
                fuellungen = str(tmpl.z14_gedat_unitcount or 0)[:6],
                inhalt = tmpl.z14_gedat_unitvol or 0.0,
                von = date_from.strftime("%Y%m%d"),
                bis = date_to.strftime("%Y%m%d"),
                abs_norm = fillings,   # ME=02 -> fillings
                abs_aktion = 0.0,
                abs_gratis = 0.0,
                abs_gesamt = fillings,
                anz_lief = max(1, rec["deliveries"]),
                melde = self.meldeeinheit or "02",
                liters = litres,
                fillings = fillings,
                art_abs = "01",
                lager = (teilnehmer or "")[:13],
                schiene = "",
                kunden_nr_her = "",
                datenursprung = "01",
                meldezeitraum = "03",
                kw = "",
                faktura = "",
                anlief = "",
                sales_inout = "01",
                gln_abs = (teilnehmer or "")[:13],
                gln_empf = "",
            )
            data_lines.append(self._bwg_line(V))

        header = "KP;SLSRPT;{g};{seq};{cnt};{ts}".format(
            g=(teilnehmer or "").zfill(8)[:8],
            seq=str(self.seq_number).zfill(8)[:8],
            cnt=str(1 + len(data_lines)),
            ts=d + t
        )
        content = header + "\r\n" + ("\r\n".join(data_lines) if data_lines else "")
        return content.encode(ENCODING, errors="replace")
