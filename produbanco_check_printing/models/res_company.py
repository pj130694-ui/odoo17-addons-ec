from odoo import fields, models

class ResCompany(models.Model):
    _inherit = "res.company"

    # Adds the layout option to the standard check printing layout selection.
    # NOTE: If your database uses a different field name than `account_check_printing_layout`,
    # adjust this accordingly.
    # Extend the check printing layout selection to include Trionica and Pacífico.
    account_check_printing_layout = fields.Selection(
        selection_add=[
            ("produbanco_check_printing.report_check_produbanco", "Produbanco (EC)"),
            ("produbanco_check_printing.report_check_trionica", "Trionica (EC)"),
            ("produbanco_check_printing.report_check_pacifico", "Pacífico (EC)"),
        ]
    )

    # Global offsets (mm) to fine-tune alignment without editing QWeb
    # Offsets (in millimetres) to fine‑tune alignment for each cheque layout.  These
    # values can be set in the Company settings and will shift all elements on
    # the printed cheque without editing the QWeb templates.
    produbanco_check_dx = fields.Float(string="Produbanco Check X Offset (mm)", default=0.0)
    produbanco_check_dy = fields.Float(string="Produbanco Check Y Offset (mm)", default=0.0)
    trionica_check_dx = fields.Float(string="Trionica Check X Offset (mm)", default=0.0)
    trionica_check_dy = fields.Float(string="Trionica Check Y Offset (mm)", default=0.0)
    pacifico_check_dx = fields.Float(string="Pacífico Check X Offset (mm)", default=0.0)
    pacifico_check_dy = fields.Float(string="Pacífico Check Y Offset (mm)", default=0.0)
