# -*- coding: utf-8 -*-
# Override del ATS Ecuador — Personalización Trionica
from collections import defaultdict

from odoo import models
from odoo.tools import float_repr, float_round


LOCAL_PURCHASE_DOCUMENT_CODES = [
    '01', '02', '03', '04', '05', '09', '11', '12',
    '19', '20', '21', '43', '45', '47', '48',
]


class L10nECTaxReportATSToolkitHandler(models.AbstractModel):
    _inherit = 'account.tax.report.handler'

    # ── B1: Eliminar sección <anulados> ──────────────────────────────────────
    def _get_void_moves(self, date_start, date_finish, journals):
        """No reportar comprobantes anulados en el ATS.
        Las facturas electrónicas anuladas ya fueron tramitadas directamente
        en el portal SRI; no se deben duplicar en el XML del ATS."""
        return self.env['account.move']

    # ── B2: Excluir ventas electrónicas de <ventas> ──────────────────────────
    def _get_invoices_values(self, date_start, date_finish):
        """Excluir ventas electrónicas (tipoEmision='E') del ATS.
        Los comprobantes electrónicos ya son reportados directamente al SRI
        mediante el proceso de autorización EDI; incluirlos en el ATS
        genera duplicidad."""
        invoices_values, errors = super()._get_invoices_values(date_start, date_finish)
        invoices_values = [
            v for v in invoices_values
            if not (
                v.get('move_type') in ('out_invoice', 'out_refund')
                and v.get('tipoEmision') == 'E'
            )
        ]
        return invoices_values, errors

    # ── B4: Usar l10n_ec_tax_support_override cuando esté definido ───────────
    def _get_purchase_values(self, date_start, date_finish):
        """Override que respeta el campo l10n_ec_tax_support_override de la
        factura: si está definido, sobreescribe el código de sustento ATS para
        TODAS las líneas de esa factura."""
        from odoo.addons.l10n_ec_edi.models.account_move import (
            L10N_EC_VAT_TAX_NOT_ZERO_GROUPS,
        )

        def get_ec_type(taxes):
            return (taxes & ec_vat_taxes)[:1].tax_group_id.l10n_ec_type or 'zero_vat'

        def get_taxsupport(invoice, taxes):
            if invoice.l10n_ec_tax_support_override:
                return invoice.l10n_ec_tax_support_override
            return (taxes & ec_vat_taxes)[:1].l10n_ec_code_taxsupport or '02'

        ec_vat_taxes = self.env['account.tax'].with_context(active_test=False).search([
            ('tax_group_id.l10n_ec_type', 'not in', (False, 'ice', 'irbpnr', 'other')),
            ('company_id', '=', self.env.company.id),
        ])

        errors = []
        withhold_taxes_no_code = self.env['account.tax']

        purchase_invoices = self.env['account.move'].search(
            [
                ('move_type', 'in', ('in_invoice', 'in_refund')),
                ('state', '=', 'posted'),
                ('l10n_latam_document_type_id.code', 'in', LOCAL_PURCHASE_DOCUMENT_CODES),
                ('date', '>=', date_start),
                ('date', '<=', date_finish),
                ('company_id', '=', self.env.company.id),
            ],
            order='invoice_date, move_type, l10n_latam_document_type_id, create_date',
        )

        purchase_vals = []
        for in_inv in purchase_invoices:
            is_from_ecuador = (
                in_inv.commercial_partner_id.country_id == self.env.ref('base.ec')
            )
            invoice_lines = in_inv.invoice_line_ids.filtered(
                lambda l: l.display_type not in ('line_section', 'line_note')
            )
            if is_from_ecuador and any(
                len(l.tax_ids & ec_vat_taxes) != 1 for l in invoice_lines
            ):
                errors.append(
                    f'{in_inv.name} : Invoice lines should have exactly one VAT tax.'
                )
            if not is_from_ecuador and any(
                len(l.tax_ids & ec_vat_taxes) > 1 for l in invoice_lines
            ):
                errors.append(
                    f'{in_inv.name} : Import invoice lines should have at most one VAT tax.'
                )

            sign = 1 if in_inv.move_type == 'in_invoice' else -1
            base_by_support = defaultdict(lambda: defaultdict(float))
            tax_by_support = defaultdict(lambda: defaultdict(float))

            for line in invoice_lines:
                ts = get_taxsupport(in_inv, line.tax_ids)
                ec_type = get_ec_type(line.tax_ids)
                base_by_support[ts][ec_type] += sign * line.balance

            tax_lines = in_inv.line_ids.filtered(
                lambda l: l.tax_line_id & ec_vat_taxes
            )
            for tl in tax_lines:
                ts = get_taxsupport(in_inv, tl.tax_line_id)
                ec_type = get_ec_type(tl.tax_line_id)
                tax_by_support[ts][ec_type] += sign * tl.balance

            all_ts = set(base_by_support) | set(tax_by_support)
            if not all_ts:
                all_ts = {get_taxsupport(in_inv, self.env['account.tax'])}

            withhold_moves = in_inv._l10n_ec_get_purchase_withholdings()

            for ts in sorted(all_ts):
                b = base_by_support.get(ts, defaultdict(float))
                t = tax_by_support.get(ts, defaultdict(float))

                air_vals = []
                for wh in withhold_moves:
                    for wl in wh.line_ids.filtered(
                        lambda l: l.tax_line_id.l10n_ec_type == 'withhold_income_purchase'
                    ):
                        air_tax = wl.tax_line_id
                        if not air_tax.l10n_ec_code_ats:
                            withhold_taxes_no_code |= air_tax
                            continue
                        air_vals.append({
                            'codRetAir': air_tax.l10n_ec_code_ats,
                            'baseImpAir': float_repr(
                                float_round(abs(wl.tax_base_amount), 2), 2
                            ),
                            'porcentajeAir': float_repr(
                                float_round(abs(air_tax.amount), 2), 2
                            ),
                            'valRetAir': float_repr(
                                float_round(abs(wl.balance), 2), 2
                            ),
                        })

                vat_wh_vals = []
                for wh in withhold_moves:
                    for wl in wh.line_ids.filtered(
                        lambda l: l.tax_line_id.l10n_ec_type == 'withhold_vat_purchase'
                    ):
                        vat_wh_vals.append({
                            'codRetIva': wl.tax_line_id.l10n_ec_code_ats or '',
                            'baseImpIva': float_repr(
                                float_round(abs(wl.tax_base_amount), 2), 2
                            ),
                            'valRetIva': float_repr(
                                float_round(abs(wl.balance), 2), 2
                            ),
                        })

                purchase_vals.append({
                    'move': in_inv,
                    'codSustento': ts,
                    'baseNoGraIva': float_repr(float_round(
                        b.get('exempt_vat', 0) + b.get('not_charged_vat', 0), 2
                    ), 2),
                    'baseImponible': float_repr(float_round(b.get('zero_vat', 0), 2), 2),
                    'baseImpGrav': float_repr(float_round(
                        sum(b.get(ec_type, 0) for ec_type in L10N_EC_VAT_TAX_NOT_ZERO_GROUPS),
                        2,
                    ), 2),
                    'montoIva': float_repr(float_round(
                        sum(t.get(ec_type, 0) for ec_type in L10N_EC_VAT_TAX_NOT_ZERO_GROUPS),
                        2,
                    ), 2),
                    'air_vals': air_vals,
                    'vat_withhold_vals': vat_wh_vals,
                    'is_from_ecuador': is_from_ecuador,
                    'valIsdAir': '0.00',
                })

        if withhold_taxes_no_code:
            errors.append(
                'Withholding taxes without ATS code: '
                + ', '.join(withhold_taxes_no_code.mapped('name'))
            )

        return purchase_vals, errors
