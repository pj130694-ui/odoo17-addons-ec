# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_ec_withhold_total_amount = fields.Monetary(
        string='Total Retenido',
        compute='_compute_ec_withhold_total',
        store=True,
        currency_field='currency_id',
    )

    l10n_ec_edi_withhold_iva = fields.Monetary(
        string='Ret. IVA',
        compute='_compute_ec_withhold_iva_fuente',
        currency_field='currency_id',
    )
    l10n_ec_edi_withhold_fuente = fields.Monetary(
        string='Ret. Fuente',
        compute='_compute_ec_withhold_iva_fuente',
        currency_field='currency_id',
    )

    l10n_ec_edi_related_invoice_id = fields.Many2one(
        comodel_name='account.move',
        string='Factura relacionada',
        domain=[('move_type', 'in', ('out_invoice', 'out_refund', 'in_invoice', 'in_refund'))],
        copy=False,
        help='Factura a la que aplica esta retención (para conciliación manual).',
    )

    @api.depends('line_ids.debit')
    def _compute_ec_withhold_total(self):
        for move in self:
            move.l10n_ec_withhold_total_amount = sum(
                l.debit for l in move.line_ids if l.debit > 0
            )

    @api.depends('line_ids.debit', 'line_ids.tax_ids', 'line_ids.account_id')
    def _compute_ec_withhold_iva_fuente(self):
        for move in self:
            iva = 0.0
            fuente = 0.0
            for line in move.line_ids:
                if line.debit <= 0:
                    continue
                if line.tax_ids:
                    ec_types = set(line.tax_ids.mapped('tax_group_id.l10n_ec_type'))
                    if 'withhold_vat_sale' in ec_types:
                        iva += line.debit
                    elif 'withhold_income_sale' in ec_types:
                        fuente += line.debit
                else:
                    code = line.account_id.code or ''
                    if '101050201' in code:
                        iva += line.debit
                    elif '101050301' in code:
                        fuente += line.debit
            move.l10n_ec_edi_withhold_iva = iva
            move.l10n_ec_edi_withhold_fuente = fuente

    @api.model_create_multi
    def create(self, vals_list):
        moves = super().create(vals_list)
        for move in moves:
            if not move.l10n_ec_edi_related_invoice_id:
                inv = move.line_ids.l10n_ec_withhold_invoice_id[:1]
                if inv:
                    move.l10n_ec_edi_related_invoice_id = inv
        return moves
