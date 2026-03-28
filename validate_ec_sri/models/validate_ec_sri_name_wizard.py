# -*- coding: utf-8 -*-

import requests
import logging

from odoo import models, api, fields
from odoo.exceptions import UserError
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)


class ValidateEcSriNameWizard(models.TransientModel):
    _name = 'validate.ec.sri.name.wizard'
    _description = 'Búsqueda por Nombre - SRI/RC'

    partner_id = fields.Many2one('res.partner', required=True, ondelete='cascade')
    name_query = fields.Char(string='Nombre a buscar')

    # Top result fields (populated by search)
    result_cedula = fields.Char(string='Cédula / RUC', readonly=True)
    result_nombre = fields.Char(string='Nombre', readonly=True)
    result_street = fields.Char(string='Dirección', readonly=True)
    result_phone = fields.Char(string='Teléfono', readonly=True)
    result_email = fields.Char(string='Correo', readonly=True)
    result_count = fields.Integer(string='Resultados', readonly=True, default=0)

    # Paginated multi-result support (up to 5 alternatives)
    alt1_cedula = fields.Char(readonly=True)
    alt1_nombre = fields.Char(readonly=True)
    alt2_cedula = fields.Char(readonly=True)
    alt2_nombre = fields.Char(readonly=True)
    alt3_cedula = fields.Char(readonly=True)
    alt3_nombre = fields.Char(readonly=True)
    alt4_cedula = fields.Char(readonly=True)
    alt4_nombre = fields.Char(readonly=True)

    # Which result the user picked (1-5)
    selected_index = fields.Integer(default=1)

    def _run_search(self, raise_on_empty=False):
        """Query /fetchdata and populate result fields. Returns number of results."""
        self.ensure_one()
        query = (self.name_query or '').strip()
        if not query:
            return 0

        api_url, api_token = self.partner_id._get_sri_api_config()
        if not api_token:
            return 0

        headers = {'X-Credits-Token': api_token}
        raw_results = []
        try:
            resp = requests.get(
                f'{api_url}/fetchdata',
                params={'name': query},
                headers=headers,
                timeout=15,
            )
            if resp.status_code == 200:
                data = resp.json()
                items = data.get('data', data)
                if isinstance(items, list):
                    raw_results = items
                elif isinstance(items, dict):
                    raw_results = [items]
            elif resp.status_code == 409:
                raw_results = resp.json().get('detail', {}).get('candidates', [])
        except Exception as e:
            _logger.warning('validate_ec_sri name wizard search error: %s', e)

        if not raw_results:
            self.write({
                'result_cedula': False, 'result_nombre': False, 'result_count': 0,
                'result_street': False, 'result_phone': False, 'result_email': False,
                'alt1_cedula': False, 'alt1_nombre': False,
                'alt2_cedula': False, 'alt2_nombre': False,
                'alt3_cedula': False, 'alt3_nombre': False,
                'alt4_cedula': False, 'alt4_nombre': False,
                'selected_index': 1,
            })
            if raise_on_empty:
                raise UserError(_('Sin resultados para "%s". Pruebe con otro nombre.') % query)
            return 0

        def _extract(item):
            datos = item.get('datos') if isinstance(item.get('datos'), dict) else {}
            cedula = (
                item.get('id') or item.get('ruc')
                or datos.get('dni') or datos.get('cedula') or datos.get('ruc')
                or item.get('dni') or item.get('cedula') or ''
            )
            nombre = (
                item.get('name') or item.get('nombre')
                or datos.get('nombres') or datos.get('nombre_completo') or datos.get('razon_social')
                or item.get('nombres') or item.get('nombre_completo') or item.get('razon_social') or ''
            ).strip()
            return cedula, nombre

        results = [_extract(r) for r in raw_results[:5]]
        # Enrich first result with full persona data if it's a cedula
        first_cedula, first_nombre = results[0]
        result_street, result_phone, result_email = '', '', ''
        if first_cedula and len(first_cedula) == 10 and first_cedula.isdigit():
            try:
                r = requests.get(
                    f'{api_url}/persona/{first_cedula}',
                    headers=headers, timeout=10,
                )
                if r.status_code == 200:
                    d = r.json()
                    datos = d.get('datos') or {}
                    result_street = (datos.get('direccion') or '').strip()
                    result_phone = (datos.get('celular1') or '').strip()
                    result_email = (datos.get('correo') or '').strip()
                    if not first_nombre:
                        first_nombre = (datos.get('nombres') or '').strip()
            except Exception as e:
                _logger.warning('validate_ec_sri _run_search enrich: %s', e)

        vals = {
            'result_cedula': first_cedula,
            'result_nombre': first_nombre,
            'result_street': result_street or False,
            'result_phone': result_phone or False,
            'result_email': result_email or False,
            'result_count': len(raw_results),
            'selected_index': 1,
            'alt1_cedula': False, 'alt1_nombre': False,
            'alt2_cedula': False, 'alt2_nombre': False,
            'alt3_cedula': False, 'alt3_nombre': False,
            'alt4_cedula': False, 'alt4_nombre': False,
        }
        alt_keys = [('alt1_cedula', 'alt1_nombre'), ('alt2_cedula', 'alt2_nombre'),
                    ('alt3_cedula', 'alt3_nombre'), ('alt4_cedula', 'alt4_nombre')]
        for i, (ck, nk) in enumerate(alt_keys):
            if i + 1 < len(results):
                vals[ck] = results[i + 1][0]
                vals[nk] = results[i + 1][1]
        self.write(vals)
        return len(raw_results)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            if rec.name_query:
                rec._run_search(raise_on_empty=False)
        return records

    def action_search(self):
        self.ensure_one()
        if not (self.name_query or '').strip():
            raise UserError(_('Ingrese un nombre para buscar.'))
        api_url, api_token = self.partner_id._get_sri_api_config()
        if not api_token:
            raise UserError(_('Configure el Token en Ajustes → SRI Ecuador.'))
        self._run_search(raise_on_empty=True)
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def _get_selected_result(self):
        """Return (cedula, nombre) for the currently selected result index."""
        idx = self.selected_index or 1
        if idx == 1:
            return self.result_cedula, self.result_nombre
        alts = [
            (self.alt1_cedula, self.alt1_nombre),
            (self.alt2_cedula, self.alt2_nombre),
            (self.alt3_cedula, self.alt3_nombre),
            (self.alt4_cedula, self.alt4_nombre),
        ]
        alt_idx = idx - 2
        if 0 <= alt_idx < len(alts) and alts[alt_idx][0]:
            return alts[alt_idx][0], alts[alt_idx][1]
        return self.result_cedula, self.result_nombre

    def action_select_1(self): self.selected_index = 1; return self._reopen()
    def action_select_2(self): self.selected_index = 2; return self._reopen()
    def action_select_3(self): self.selected_index = 3; return self._reopen()
    def action_select_4(self): self.selected_index = 4; return self._reopen()
    def action_select_5(self): self.selected_index = 5; return self._reopen()

    def _reopen(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_apply(self):
        self.ensure_one()
        if not self.result_cedula:
            raise UserError(_('Primero busque un nombre para poder aplicar.'))

        cedula, nombre = self._get_selected_result()
        cedula = (cedula or '').strip()

        partner = self.partner_id
        api_url, api_token = partner._get_sri_api_config()
        headers = {'X-Credits-Token': api_token}

        vals = {'sri_verified': True, 'sri_last_check': fields.Datetime.now()}

        if cedula and len(cedula) == 10 and cedula.isdigit():
            try:
                resp = requests.get(f'{api_url}/persona/{cedula}', headers=headers, timeout=15)
                if resp.status_code == 200:
                    persona_vals = partner._fill_vals_from_persona(resp.json(), 'persona')
                    vals.update(persona_vals)
                else:
                    if nombre:
                        vals['name'] = nombre
            except Exception as e:
                _logger.warning('validate_ec_sri wizard apply /persona/%s: %s', cedula, e)
                if nombre:
                    vals['name'] = nombre
            cedula_type, _ruc_type = partner._get_ec_id_types()
            id_type_vals = {'l10n_latam_identification_type_id': cedula_type.id} if cedula_type else {}
            vals.update({'vat': cedula, 'type_ref': 'cedula', 'company_type': 'person', **id_type_vals})

        elif cedula and len(cedula) == 13 and cedula.isdigit():
            try:
                resp = requests.get(f'{api_url}/empresa/{cedula}', headers=headers, timeout=15)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get('razon_social'):
                        vals['name'] = data['razon_social'].strip()
                    vals.update({'company_type': 'company', 'type_ref': 'ruc', 'vat': cedula})
                    for api_key, fld in [
                        ('nombre_comercial', 'sri_nombre_comercial'),
                        ('estado', 'sri_estado'), ('actividad', 'sri_actividad'),
                        ('regimen', 'sri_regimen'), ('tipo', 'sri_tipo'),
                        ('obligado_contabilidad', 'sri_obligado_contabilidad'),
                        ('agente_retencion', 'sri_agente_retencion'),
                        ('contribuyente_especial', 'sri_contribuyente_especial'),
                    ]:
                        if data.get(api_key):
                            vals[fld] = data[api_key]
                    if data.get('direccion'):
                        vals.update(partner._parse_ec_address(data['direccion']))
            except Exception as e:
                _logger.warning('validate_ec_sri wizard apply empresa: %s', e)
                if nombre:
                    vals['name'] = nombre
        else:
            if nombre:
                vals['name'] = nombre

        try:
            partner.write(vals)
        except Exception as e:
            err_str = str(e)
            if 'ya está registrado' in err_str or 'already registered' in err_str:
                vals_no_vat = {k: v for k, v in vals.items() if k not in ('vat', 'type_ref')}
                partner.write(vals_no_vat)
            else:
                raise

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner',
            'res_id': partner.id,
            'view_mode': 'form',
            'target': 'current',
        }


class ValidateEcSriNameWizardLine(models.TransientModel):
    """Kept for DB compatibility — no longer used in the UI."""
    _name = 'validate.ec.sri.name.wizard.line'
    _description = 'Resultado búsqueda SRI/RC (legacy)'

    wizard_id = fields.Many2one('validate.ec.sri.name.wizard', required=True, ondelete='cascade')
    selected = fields.Boolean(string='✓', default=False)
    cedula = fields.Char(string='Cédula / RUC')
    nombre = fields.Char(string='Nombre')
    direccion = fields.Char(string='Dirección')
    fecha_nacim = fields.Char(string='Fecha Nac.')
