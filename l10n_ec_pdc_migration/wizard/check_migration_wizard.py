# -*- coding: utf-8 -*-
import xmlrpc.client
import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class CheckMigrationWizard(models.TransientModel):
    _name = 'check.migration.wizard'
    _description = 'Asistente de Migración de Cheques Odoo 16 → 17'

    # Conexión Odoo 16
    odoo16_url = fields.Char(
        string='URL Odoo 16', default='https://trionica.ec', required=True)
    odoo16_db = fields.Char(
        string='Base de datos Odoo 16', default='root', required=True)
    odoo16_user = fields.Char(
        string='Usuario Odoo 16', default='contabilidad@trionica.ec', required=True)
    odoo16_password = fields.Char(
        string='Contraseña Odoo 16', default='x', required=True)

    # Opciones
    migrate_customer_checks = fields.Boolean(
        string='Migrar cheques de clientes (check.customer.line)', default=True)
    migrate_vendor_checks = fields.Boolean(
        string='Migrar cheques de proveedores (check.note)', default=True)
    only_active_checks = fields.Boolean(
        string='Solo cheques activos (no-done)', default=False,
        help='Si activado, solo migra cheques no finalizados. Si desactivado, migra todo el histórico.')
    dry_run = fields.Boolean(
        string='Simulación (no crear registros)', default=True,
        help='Ejecuta el proceso sin crear nada. Ver resultado antes de aplicar.')

    # Journals destino
    customer_journal_id = fields.Many2one(
        'account.journal', string='Journal cheques clientes (Odoo 17)',
        domain=[('type', 'in', ['bank', 'cash'])],
        help='Journal CHQ en Odoo 17 (id=42)',
    )
    vendor_journal_id = fields.Many2one(
        'account.journal', string='Journal cheques proveedores (Odoo 17)',
        domain=[('type', 'in', ['bank', 'cash'])],
        help='Journal BPROD en Odoo 17 (id=49)',
    )

    # Resultados
    result_summary = fields.Text(string='Resumen de Resultados', readonly=True)
    result_customer_total = fields.Integer(string='Total cheques clientes', readonly=True)
    result_customer_migrated = fields.Integer(string='Migrados OK', readonly=True)
    result_customer_warning = fields.Integer(string='Con advertencia', readonly=True)
    result_customer_manual = fields.Integer(string='Revisión manual', readonly=True)
    result_customer_skipped = fields.Integer(string='Omitidos', readonly=True)
    result_vendor_total = fields.Integer(string='Total cheques proveedores', readonly=True)
    result_vendor_migrated = fields.Integer(string='Migrados OK (proveedores)', readonly=True)
    result_vendor_manual = fields.Integer(string='Revisión manual (proveedores)', readonly=True)

    def _connect_odoo16(self):
        """Conecta a Odoo 16 via XMLRPC y devuelve (uid, models_proxy)."""
        try:
            common = xmlrpc.client.ServerProxy(
                f'{self.odoo16_url}/xmlrpc/2/common', allow_none=True)
            uid = common.authenticate(
                self.odoo16_db, self.odoo16_user, self.odoo16_password, {})
            if not uid:
                raise UserError(_('No se pudo autenticar en Odoo 16. Verifica credenciales.'))
            models_proxy = xmlrpc.client.ServerProxy(
                f'{self.odoo16_url}/xmlrpc/2/object', allow_none=True)
            _logger.info('Conexión a Odoo 16 exitosa. UID=%s', uid)
            return uid, models_proxy
        except Exception as e:
            raise UserError(_(f'Error conectando a Odoo 16: {str(e)}'))

    def _get_or_create_partner(self, vat, name):
        """Busca partner por VAT. Si no existe, retorna None (no crea sin datos completos)."""
        if not vat:
            return None
        partner = self.env['res.partner'].search([('vat', '=', vat)], limit=1)
        return partner or None

    def _map_customer_state(self, legacy_state):
        """Mapea estado check.customer.line → pdc.wizard state."""
        mapping = {
            'draft': 'registered',
            'deposited': 'deposited',
            'done': 'done',
            'protested': 'bounced',
            'changed': 'cancel',
            'cancel': 'cancel',
        }
        return mapping.get(legacy_state, 'registered')

    def _map_vendor_state(self, legacy_state):
        """Mapea estado check.note → pdc.wizard state."""
        mapping = {
            'assigned': 'registered',
            'done': 'done',
            'cancel': 'cancel',
            'hibernate': 'cancel',
        }
        return mapping.get(legacy_state, 'registered')

    def _already_migrated(self, legacy_model, legacy_id):
        """Verifica si ya existe un pdc.wizard con estos datos legacy."""
        existing = self.env['pdc.wizard'].search([
            ('legacy_model', '=', legacy_model),
            ('legacy_id', '=', legacy_id),
        ], limit=1)
        return existing

    def _migrate_customer_checks(self, uid, models_proxy, dry_run=True):
        """Migra check.customer.line de Odoo 16 a pdc.wizard."""
        db = self.odoo16_db
        pw = self.odoo16_password

        fields_to_read = [
            'number', 'amount', 'state', 'payment_id', 'partner_id',
            'reception_date', 'send_deposit_date', 'deposit_date', 'done_date',
            'protested_date', 'deposit_move_id', 'done_move_id',
            'accounting_bank_id', 'check_back_id', 'debit_note_id',
        ]

        # Determinar dominio según opción
        domain = [] if not self.only_active_checks else [('state', 'not in', ['done', 'cancel'])]

        records = models_proxy.execute_kw(
            db, uid, pw, 'check.customer.line', 'search_read',
            [domain], {'fields': fields_to_read})

        _logger.info('check.customer.line a procesar: %s', len(records))

        journal = self.customer_journal_id
        if not journal:
            raise UserError(_('Debes seleccionar el journal para cheques de clientes.'))

        results = {'total': len(records), 'migrated': 0, 'warning': 0,
                   'manual': 0, 'skipped': 0, 'details': []}

        for rec in records:
            legacy_model = 'check.customer.line'
            legacy_id = rec['id']

            # Verificar si ya existe
            if self._already_migrated(legacy_model, legacy_id):
                results['skipped'] += 1
                continue

            # Buscar partner
            partner = None
            if rec.get('payment_id'):
                partner_id = self._resolve_partner_from_payment(models_proxy, uid, rec)
                if partner_id:
                    partner = self.env['res.partner'].browse(partner_id)

            # Resolver banco
            bank = None
            if rec.get('accounting_bank_id'):
                bank_name = rec['accounting_bank_id'][1] if isinstance(
                    rec['accounting_bank_id'], list) else ''
                bank = self.env['res.bank'].search(
                    [('name', 'ilike', bank_name[:20])], limit=1) if bank_name else None

            # Resolver fechas (NOT NULL en pdc_wizard)
            payment_date = rec.get('reception_date') or rec.get('deposit_date') or rec.get('done_date')
            due_date = rec.get('deposit_date') or rec.get('done_date') or payment_date
            done_date = rec.get('done_date')

            if not payment_date:
                results['manual'] += 1
                results['details'].append(
                    f'[MANUAL] check.customer.line ID={legacy_id} sin fechas válidas')
                continue

            # Determinar estado migrado
            mapped_state = self._map_customer_state(rec['state'])
            migration_status = 'migrated'
            migration_note = f"Migrado desde Odoo16. Estado original: {rec['state']}."

            if rec['state'] == 'protested':
                migration_status = 'manual_review'
                migration_note += (' CHEQUE PROTESTADO: Verificar nota de débito y gestión '
                                   'pendiente con el cliente. Estado mapeado a bounced.')
                results['manual'] += 1
            elif rec['state'] in ('draft',):
                migration_status = 'manual_review'
                migration_note += ' Cheque recibido sin depositar. Requiere gestión.'
                results['manual'] += 1
            elif rec['state'] == 'changed':
                migration_status = 'warning'
                migration_note += (f' Cheque reemplazado. Cheque anterior ID Odoo16='
                                   f'{rec.get("check_back_id", [None])[0] if rec.get("check_back_id") else "?"}')
                results['warning'] += 1
            else:
                results['migrated'] += 1

            # Referencia pago Odoo 16
            pay_ref = rec['payment_id'][1] if isinstance(rec.get('payment_id'), list) else ''
            pay_id_16 = rec['payment_id'][0] if isinstance(rec.get('payment_id'), list) else 0
            deposit_move_name = (rec['deposit_move_id'][1] if isinstance(
                rec.get('deposit_move_id'), list) else '')
            done_move_name = (rec['done_move_id'][1] if isinstance(
                rec.get('done_move_id'), list) else '')

            vals = {
                'payment_type': 'receive_money',
                'partner_id': partner.id if partner else False,
                'payment_amount': rec.get('amount', 0.0),
                'reference': rec.get('number', ''),
                'journal_id': journal.id,
                'bank_id': bank.id if bank else False,
                'payment_date': payment_date,
                'due_date': due_date,
                'done_date': done_date or False,
                'memo': f"Migrado Odoo16 | {pay_ref} | Cheque #{rec.get('number', '')}",
                'state': mapped_state,
                # Campos legacy
                'legacy_model': legacy_model,
                'legacy_id': legacy_id,
                'legacy_state': rec['state'],
                'legacy_payment_ref': pay_ref,
                'legacy_payment_id': pay_id_16,
                'legacy_deposit_move': deposit_move_name,
                'legacy_done_move': done_move_name,
                'migration_status': migration_status,
                'migration_note': migration_note,
                'is_legacy': True,
            }

            if not dry_run:
                try:
                    self.env['pdc.wizard'].create(vals)
                    _logger.info('Creado pdc.wizard para check.customer.line ID=%s', legacy_id)
                except Exception as e:
                    _logger.error('Error creando pdc.wizard para ID=%s: %s', legacy_id, str(e))
                    results['details'].append(f'[ERROR] ID={legacy_id}: {str(e)}')
                    results['manual'] += 1
                    if migration_status == 'migrated':
                        results['migrated'] -= 1

        return results

    def _resolve_partner_from_payment(self, models_proxy, uid, rec):
        """Resuelve partner_id en Odoo 17 a partir del pago en Odoo 16."""
        db = self.odoo16_db
        pw = self.odoo16_password

        if not rec.get('payment_id'):
            return False

        pay_id = rec['payment_id'][0] if isinstance(rec['payment_id'], list) else rec['payment_id']
        try:
            pay = models_proxy.execute_kw(
                db, uid, pw, 'account.payment', 'read',
                [[pay_id]], {'fields': ['partner_id']})[0]
            if pay.get('partner_id'):
                partner_id_16 = pay['partner_id'][0]
                # Get VAT from Odoo 16
                partner_16 = models_proxy.execute_kw(
                    db, uid, pw, 'res.partner', 'read',
                    [[partner_id_16]], {'fields': ['vat', 'name']})[0]
                vat = partner_16.get('vat')
                if vat:
                    partner_17 = self.env['res.partner'].search(
                        [('vat', '=', vat)], limit=1)
                    if partner_17:
                        return partner_17.id
        except Exception as e:
            _logger.warning('No se pudo resolver partner para payment %s: %s', pay_id, e)
        return False

    def _migrate_vendor_checks(self, uid, models_proxy, dry_run=True):
        """Migra check.note (done y assigned) de Odoo 16 a pdc.wizard."""
        db = self.odoo16_db
        pw = self.odoo16_password

        fields_to_read = [
            'number', 'amount', 'state', 'payment_id',
            'date_emission', 'date_done', 'move_id', 'check_book_id', 'partner_id',
        ]
        domain = [('state', 'in', ['assigned', 'done', 'hibernate', 'cancel'])]

        records = models_proxy.execute_kw(
            db, uid, pw, 'check.note', 'search_read',
            [domain], {'fields': fields_to_read})

        _logger.info('check.note a procesar: %s', len(records))

        journal = self.vendor_journal_id
        if not journal:
            raise UserError(_('Debes seleccionar el journal para cheques de proveedores.'))

        results = {'total': len(records), 'migrated': 0, 'manual': 0, 'skipped': 0}

        for rec in records:
            legacy_model = 'check.note'
            legacy_id = rec['id']

            if self._already_migrated(legacy_model, legacy_id):
                results['skipped'] += 1
                continue

            payment_date = rec.get('date_emission')
            due_date = rec.get('date_done') or payment_date

            if not payment_date:
                results['manual'] += 1
                continue

            mapped_state = self._map_vendor_state(rec['state'])
            migration_status = 'migrated' if rec['state'] == 'done' else 'manual_review'
            migration_note = f"Migrado desde Odoo16. Estado original: {rec['state']}."

            if rec['state'] == 'assigned':
                migration_note += ' Cheque asignado a pago en Odoo 16. Verificar estado real.'
            elif rec['state'] == 'hibernate':
                migration_note += ' Cheque hibernado/inactivo en Odoo 16.'

            # Partner
            partner_id = False
            if rec.get('partner_id'):
                partner_id_16 = rec['partner_id'][0]
                try:
                    partner_16 = models_proxy.execute_kw(
                        db, uid, pw, 'res.partner', 'read',
                        [[partner_id_16]], {'fields': ['vat']})[0]
                    if partner_16.get('vat'):
                        p17 = self.env['res.partner'].search(
                            [('vat', '=', partner_16['vat'])], limit=1)
                        partner_id = p17.id if p17 else False
                except Exception:
                    pass

            pay_ref = rec['payment_id'][1] if isinstance(rec.get('payment_id'), list) else ''
            pay_id_16 = rec['payment_id'][0] if isinstance(rec.get('payment_id'), list) else 0
            done_move_name = (rec['move_id'][1] if isinstance(rec.get('move_id'), list) else '')

            vals = {
                'payment_type': 'send_money',
                'partner_id': partner_id or False,
                'payment_amount': abs(rec.get('amount', 0.0)),
                'reference': rec.get('number', ''),
                'journal_id': journal.id,
                'payment_date': payment_date,
                'due_date': due_date,
                'done_date': rec.get('date_done') or False,
                'memo': f"Migrado Odoo16 | {pay_ref} | Cheque #{rec.get('number', '')}",
                'state': mapped_state,
                'legacy_model': legacy_model,
                'legacy_id': legacy_id,
                'legacy_state': rec['state'],
                'legacy_payment_ref': pay_ref,
                'legacy_payment_id': pay_id_16,
                'legacy_done_move': done_move_name,
                'migration_status': migration_status,
                'migration_note': migration_note,
                'is_legacy': True,
            }

            if not dry_run:
                try:
                    self.env['pdc.wizard'].create(vals)
                    results['migrated'] += 1 if rec['state'] == 'done' else 0
                    results['manual'] += 1 if rec['state'] != 'done' else 0
                except Exception as e:
                    _logger.error('Error creando pdc.wizard para check.note ID=%s: %s', legacy_id, str(e))
                    results['manual'] += 1
            else:
                if rec['state'] == 'done':
                    results['migrated'] += 1
                else:
                    results['manual'] += 1

        return results

    def action_run_migration(self):
        """Ejecuta la migración (o simulación si dry_run=True)."""
        uid, models_proxy = self._connect_odoo16()
        dry_run = self.dry_run

        summary_lines = []
        summary_lines.append(f'{"=== SIMULACIÓN ===" if dry_run else "=== MIGRACIÓN REAL ==="}')
        summary_lines.append(f'Fecha/hora: {fields.Datetime.now()}')
        summary_lines.append('')

        cust_results = {'total': 0, 'migrated': 0, 'warning': 0, 'manual': 0, 'skipped': 0}
        vend_results = {'total': 0, 'migrated': 0, 'manual': 0, 'skipped': 0}

        if self.migrate_customer_checks:
            cust_results = self._migrate_customer_checks(uid, models_proxy, dry_run)
            summary_lines.append('--- CHEQUES DE CLIENTES (check.customer.line) ---')
            summary_lines.append(f'  Total en Odoo 16:     {cust_results["total"]}')
            summary_lines.append(f'  Migrados OK:          {cust_results["migrated"]}')
            summary_lines.append(f'  Con advertencia:      {cust_results["warning"]}')
            summary_lines.append(f'  Revisión manual:      {cust_results["manual"]}')
            summary_lines.append(f'  Omitidos (ya exist.): {cust_results["skipped"]}')
            if cust_results.get('details'):
                summary_lines.append('  Detalles:')
                for d in cust_results['details'][:20]:
                    summary_lines.append(f'    {d}')
            summary_lines.append('')

        if self.migrate_vendor_checks:
            vend_results = self._migrate_vendor_checks(uid, models_proxy, dry_run)
            summary_lines.append('--- CHEQUES DE PROVEEDORES (check.note) ---')
            summary_lines.append(f'  Total en Odoo 16:     {vend_results["total"]}')
            summary_lines.append(f'  Migrados OK:          {vend_results["migrated"]}')
            summary_lines.append(f'  Revisión manual:      {vend_results["manual"]}')
            summary_lines.append(f'  Omitidos (ya exist.): {vend_results["skipped"]}')

        self.write({
            'result_summary': '\n'.join(summary_lines),
            'result_customer_total': cust_results['total'],
            'result_customer_migrated': cust_results['migrated'],
            'result_customer_warning': cust_results.get('warning', 0),
            'result_customer_manual': cust_results['manual'],
            'result_customer_skipped': cust_results['skipped'],
            'result_vendor_total': vend_results['total'],
            'result_vendor_migrated': vend_results['migrated'],
            'result_vendor_manual': vend_results['manual'],
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
