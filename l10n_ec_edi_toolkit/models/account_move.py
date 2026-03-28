# -*- coding: utf-8 -*-
# Herramientas EDI Ecuador - Gestión segura de facturas
from datetime import datetime, time, timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_SRI_DAILY_LIMIT_KEYWORDS = ('limite de intentos', 'límite de intentos')


def _contains_daily_limit_error(error_text):
    if not error_text:
        return False
    lower = error_text.lower()
    return any(kw in lower for kw in _SRI_DAILY_LIMIT_KEYWORDS)


class AccountMove(models.Model):
    _inherit = 'account.move'

    # ─── Campo sustento: override por factura para el ATS ────────────────────
    l10n_ec_tax_support_override = fields.Selection(
        selection=[
            ('01', '01 - Crédito tributario IVA (bienes y servicios)'),
            ('02', '02 - Costo o gasto para IR (bienes y servicios)'),
            ('03', '03 - Activo Fijo - Crédito tributario IVA'),
            ('04', '04 - Activo Fijo - Costo o gasto para IR'),
            ('05', '05 - Liquidación gastos de viaje, alojamiento y alimentación'),
            ('06', '06 - Inventario - Crédito tributario IVA'),
            ('07', '07 - Inventario - Costo o gasto para IR'),
            ('08', '08 - Valor pagado para solicitar Reembolso de Gastos'),
            ('09', '09 - Reembolso por Siniestros'),
            ('10', '10 - Distribución de Dividendos, Beneficios o Utilidades'),
            ('15', '15 - Pagos por servicios digitales'),
            ('00', '00 - Casos especiales'),
        ],
        string='Cód. Sustento ATS',
        copy=False,
        help=(
            'Si se especifica, sobreescribe el código de sustento del ATS '
            'para TODAS las líneas de esta factura de compra. '
            'Dejar vacío para usar el código configurado en cada impuesto.'
        ),
    )

    # ─── Único campo custom: fecha de protección de reintento SRI ─────────────
    # Campo stored (Datetime) → siempre presente en BD → siempre en fields_dict.
    # Lo usan los botones directamente en invisible= sin necesidad de compute booleans.
    l10n_ec_edi_retry_not_before = fields.Datetime(
        string='Reintento SRI desde',
        copy=False,
        readonly=True,
        tracking=True,
        help=(
            "Fecha/hora mínima para reintentar el envío al SRI. "
            "Se establece automáticamente cuando el SRI rechaza por "
            "'límite de intentos diarios'. Mientras sea futura, el "
            "cron y el reintento manual están bloqueados."
        ),
    )

    # ─── OVERRIDE: proteger _process_edi_documents del cron ──────────────────
    def _process_edi_documents(self):
        """
        Excluye del cron EDI las facturas EC que tengan una fecha de reintento SRI futura.
        """
        now = fields.Datetime.now()
        moves_on_hold = self.filtered(
            lambda m: m.country_code == 'EC'
            and m.l10n_ec_edi_retry_not_before
            and m.l10n_ec_edi_retry_not_before > now
        )
        if moves_on_hold:
            return super(AccountMove, self - moves_on_hold)._process_edi_documents()
        return super()._process_edi_documents()

    # ─── ACCIÓN A: Pasar a borrador con validaciones Ecuador ──────────────────
    def action_l10n_ec_toolkit_reset_to_draft(self):
        self.ensure_one()

        if self.l10n_ec_authorization_date:
            raise UserError(_(
                "No es posible pasar a borrador: este documento fue AUTORIZADO por el SRI.\n\n"
                "Número de autorización: %(auth_num)s\n"
                "Fecha de autorización: %(auth_date)s\n\n"
                "Para anularlo debe:\n"
                "  1. Tramitar la anulación en el portal SRI (sri.gob.ec).\n"
                "  2. Luego usar el botón 'Cancelar' en Odoo.\n\n"
                "No se puede pasar a borrador un documento ya autorizado por el SRI.",
                auth_num=self.l10n_ec_authorization_number or 'N/A',
                auth_date=self.l10n_ec_authorization_date,
            ))

        if self.l10n_ec_withhold_count > 0:
            raise UserError(_(
                "No es posible pasar a borrador: la factura tiene %(count)d "
                "retención(es) de compra asociada(s).\n\n"
                "Debe anular o eliminar las retenciones primero.\n"
                "Use el botón 'Retenciones' (%(count)d) para verlas.",
                count=self.l10n_ec_withhold_count,
            ))

        reconciled_lines = self.line_ids.filtered(
            lambda l: l.account_type in ('asset_receivable', 'liability_payable')
            and l.reconciled
        )
        if reconciled_lines:
            raise UserError(_(
                "No es posible pasar a borrador: la factura tiene pagos o créditos "
                "aplicados (líneas contables reconciliadas).\n\n"
                "Primero debe cancelar los pagos o eliminar la reconciliación.\n\n"
                "Cuentas afectadas: %(accounts)s",
                accounts=', '.join(reconciled_lines.mapped('account_id.display_name')),
            ))

        blocking_edi = self.edi_document_ids.filtered(
            lambda d: d.edi_format_id.code == 'ecuadorian_edi'
            and d.state in ('sent', 'to_cancel')
        )
        if blocking_edi:
            raise UserError(_(
                "No es posible pasar a borrador: existe un documento electrónico "
                "del SRI en estado '%(edi_state)s'.\n\n"
                "Si ya fue cancelado en el SRI, use el botón 'Cancelar' de Odoo primero.",
                edi_state=blocking_edi[0].state,
            ))

        if self.l10n_ec_edi_retry_not_before:
            self.l10n_ec_edi_retry_not_before = False

        return self.button_draft()

    # ─── ACCIÓN B: Limpiar error EDI del SRI ─────────────────────────────────
    def action_l10n_ec_toolkit_clear_sri_error(self):
        self.ensure_one()

        sri_error_docs = self.edi_document_ids.filtered(
            lambda d: d.edi_format_id.code == 'ecuadorian_edi'
            and d.blocking_level == 'error'
        )

        if self.l10n_ec_authorization_date:
            sri_error_docs = sri_error_docs.filtered(lambda d: d.state == 'to_cancel')
            if not sri_error_docs:
                raise UserError(_(
                    "Este documento ya fue AUTORIZADO por el SRI "
                    "(Núm.: %(auth_num)s).\n\n"
                    "Use el botón 'Cancelar' para gestionar la anulación.",
                    auth_num=self.l10n_ec_authorization_number or 'N/A',
                ))

        if not sri_error_docs:
            raise UserError(_(
                "No se encontró ningún error EDI del SRI activo en este documento."
            ))

        previous_errors = '\n'.join(filter(None, sri_error_docs.mapped('error')))
        is_daily_limit = _contains_daily_limit_error(previous_errors)

        if is_daily_limit:
            retry_dt = self._l10n_ec_toolkit_next_retry_datetime()
            self.l10n_ec_edi_retry_not_before = retry_dt
            sri_error_docs.write({'error': False})
            self.with_context(no_new_invoice=True).message_post(
                body=_(
                    "<strong>Error de límite diario SRI — Reintento diferido.</strong><br/>"
                    "<b>Ejecutado por:</b> %(user)s<br/>"
                    "<b>Error detectado:</b><br/><pre>%(prev_error)s</pre>"
                    "<b>Diagnóstico:</b> El SRI impone máximo 2 intentos por comprobante por día. "
                    "Este límite es externo a Odoo (web service SOAP del SRI).<br/><br/>"
                    "<b>Reintento habilitado desde:</b> <strong>%(retry_date)s</strong><br/><br/>"
                    "Cuando aparezca el botón <em>'Reintentar Envío al SRI'</em> "
                    "podrá reenviar el comprobante.",
                    user=self.env.user.name,
                    prev_error=previous_errors or '(sin detalle)',
                    retry_date=retry_dt,
                ),
            )
        else:
            self.l10n_ec_edi_retry_not_before = False
            sri_error_docs.write({'error': False, 'blocking_level': False})
            self.with_context(no_new_invoice=True).message_post(
                body=_(
                    "<strong>Error EDI del SRI limpiado — Reintento habilitado.</strong><br/>"
                    "<b>Ejecutado por:</b> %(user)s<br/>"
                    "<b>Error eliminado:</b><br/><pre>%(prev_error)s</pre>"
                    "Use <em>'Enviar &amp; Imprimir'</em> para reenviar "
                    "o espere el siguiente ciclo del cron de EDI.",
                    user=self.env.user.name,
                    prev_error=previous_errors or '(sin detalle)',
                ),
            )
        return True

    # ─── ACCIÓN C: Habilitar reintento tras expirar fecha de espera ──────────
    def action_l10n_ec_toolkit_enable_retry(self):
        self.ensure_one()
        now = fields.Datetime.now()

        if not self.l10n_ec_edi_retry_not_before:
            raise UserError(_("Este documento no tiene una fecha de reintento pendiente."))

        if self.l10n_ec_edi_retry_not_before > now:
            raise UserError(_(
                "Aún no es posible reintentar. Fecha mínima: %(retry_date)s\n\n"
                "Espere hasta esa fecha antes de reintentar el envío al SRI.",
                retry_date=self.l10n_ec_edi_retry_not_before,
            ))

        held_docs = self.edi_document_ids.filtered(
            lambda d: d.edi_format_id.code == 'ecuadorian_edi'
            and d.blocking_level == 'error'
        )
        held_docs.write({'blocking_level': False, 'error': False})
        self.l10n_ec_edi_retry_not_before = False

        self.with_context(no_new_invoice=True).message_post(
            body=_(
                "<strong>Reintento SRI habilitado.</strong><br/>"
                "<b>Habilitado por:</b> %(user)s<br/>"
                "Use <em>'Enviar &amp; Imprimir'</em> para reintentar, "
                "o el cron de EDI lo procesará automáticamente.",
                user=self.env.user.name,
            ),
        )
        return True

    # ─── OVERRIDE: permitir código de sustento override en wizard de retenciones ─
    def _l10n_ec_get_inv_taxsupports_and_amounts(self):
        """
        Override: si l10n_ec_tax_support_override está definido, consolida todos
        los códigos de sustento del impuesto bajo ese código override.
        Esto permite que el wizard de retenciones acepte el código override como
        válido, sin bloquear con el error 'no está en los sustentos tributarios'.
        """
        taxsupports = super()._l10n_ec_get_inv_taxsupports_and_amounts()
        override = self.l10n_ec_tax_support_override
        if not override or override in taxsupports:
            return taxsupports
        merged = {'amount_base': 0.0, 'amount_vat': 0.0}
        for v in taxsupports.values():
            merged['amount_base'] += v['amount_base']
            merged['amount_vat'] += v['amount_vat']
        return {override: merged}

    # ─── OVERRIDE: corregir payment_amount en docSustento (Error 52 SRI) ─────
    def _l10n_ec_get_withhold_edi_data_lines(self):
        """Garantiza que payment_amount == invoice_amount_total en cada docSustento,
        evitando el error 52 del SRI (ValidadorDocSustentoPago):
        0 < pagos.total <= docSustento.importeTotal
        """
        result = super()._l10n_ec_get_withhold_edi_data_lines()
        if isinstance(result, list):
            for taxsupport in result:
                invoice_total = taxsupport.get('invoice_amount_total', 0.0)
                for payment in taxsupport.get('invoice_payments', []):
                    payment['payment_amount'] = invoice_total
        return result

    # ─── ACCIÓN D: Forzar borrador en facturas anuladas en portal SRI ─────────
    def action_l10n_ec_force_draft_annulled(self):
        """Fuerza el paso a borrador para documentos anulados en el portal SRI pero
        que aún aparecen como AUTORIZADOS en la API del SRI.
        SOLO usar después de haber tramitado la anulación en sri.gob.ec.
        """
        for move in self:
            move.edi_document_ids.write({
                'state': 'cancelled',
                'error': False,
                'blocking_level': False,
            })
        self.button_draft()

    # ─── Helper privado ───────────────────────────────────────────────────────
    def _l10n_ec_toolkit_next_retry_datetime(self):
        from pytz import timezone as pytz_tz
        ec_tz = pytz_tz('America/Guayaquil')
        now_ec = datetime.now(tz=ec_tz)
        next_day_ec = ec_tz.localize(
            datetime.combine(now_ec.date(), time(0, 1))
        ) + timedelta(days=1)
        return next_day_ec.astimezone(pytz_tz('UTC')).replace(tzinfo=None)
