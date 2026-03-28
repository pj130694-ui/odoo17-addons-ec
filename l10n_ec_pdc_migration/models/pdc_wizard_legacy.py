# -*- coding: utf-8 -*-
from odoo import models, fields, api

class PdcWizardLegacy(models.Model):
    _inherit = 'pdc.wizard'

    legacy_model = fields.Char(
        string='Modelo Odoo 16',
        readonly=True,
        help='Modelo origen: check.customer.line o check.note',
    )
    legacy_id = fields.Integer(
        string='ID Odoo 16',
        readonly=True,
        index=True,
        help='ID del registro en el sistema Odoo 16 de origen',
    )
    legacy_state = fields.Char(
        string='Estado Original Odoo 16',
        readonly=True,
        help='Estado del cheque en Odoo 16 antes de la migración',
    )
    legacy_payment_ref = fields.Char(
        string='Referencia Pago Odoo 16',
        readonly=True,
        help='Nombre del account.payment en Odoo 16 (ej: PCHCLI/2024/00002)',
    )
    legacy_payment_id = fields.Integer(
        string='ID Pago Odoo 16',
        readonly=True,
        help='ID del account.payment en Odoo 16',
    )
    legacy_deposit_move = fields.Char(
        string='Asiento Depósito Odoo 16',
        readonly=True,
        help='Nombre del asiento de depósito en Odoo 16',
    )
    legacy_done_move = fields.Char(
        string='Asiento Acreditación Odoo 16',
        readonly=True,
        help='Nombre del asiento de acreditación en Odoo 16',
    )
    migration_status = fields.Selection([
        ('migrated', 'Migrado OK'),
        ('warning', 'Migrado con Advertencia'),
        ('manual_review', 'Requiere Revisión Manual'),
        ('error', 'Error de Migración'),
    ], string='Estado Migración', readonly=True, index=True)
    migration_note = fields.Text(
        string='Notas de Migración',
        readonly=True,
        help='Observaciones generadas durante el proceso de migración',
    )
    is_legacy = fields.Boolean(
        string='Registro Histórico',
        readonly=True,
        default=False,
        help='True si este registro fue migrado desde Odoo 16',
    )
