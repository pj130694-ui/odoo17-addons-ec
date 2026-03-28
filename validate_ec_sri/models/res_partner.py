# -*- coding: utf-8 -*-

import requests
import logging
from datetime import datetime

from odoo import models, api, fields
from odoo.exceptions import UserError, ValidationError
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # ── Identification type detected from VAT ─────────────────────────────────
    type_ref = fields.Char(
        string='Tipo ID Ecuador',
        size=20,
        readonly=True,
        copy=False,
        help="Tipo detectado: cedula, ruc, passport",
    )

    # ── SRI extra fields ──────────────────────────────────────────────────────
    sri_nombre_comercial = fields.Char(
        string='Nombre Comercial',
        size=256,
    )
    sri_estado = fields.Char(
        string='Estado Contribuyente',
        readonly=True,
        copy=False,
    )
    sri_actividad = fields.Char(
        string='Actividad Económica',
        readonly=True,
        copy=False,
    )
    sri_regimen = fields.Char(
        string='Régimen',
        readonly=True,
        copy=False,
    )
    sri_obligado_contabilidad = fields.Char(
        string='Obligado a llevar Contabilidad',
        readonly=True,
        copy=False,
    )
    sri_agente_retencion = fields.Char(
        string='Agente de Retención',
        readonly=True,
        copy=False,
    )
    sri_contribuyente_especial = fields.Char(
        string='Contribuyente Especial',
        readonly=True,
        copy=False,
    )
    sri_tipo = fields.Char(
        string='Tipo de Contribuyente',
        readonly=True,
        copy=False,
        help="Tipo según el SRI: SOCIEDAD, PERSONA NATURAL, etc.",
    )
    sri_verified = fields.Boolean(
        string='Verificado SRI/RC',
        default=False,
        copy=False,
    )
    sri_last_check = fields.Datetime(
        string='Última Consulta SRI',
        readonly=True,
        copy=False,
    )

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _verifica_cedula(self, ced):
        """Ecuadorian cedula checksum. Returns True if valid."""
        try:
            coefs = [2, 1, 2, 1, 2, 1, 2, 1, 2]
            valores = [int(ced[i]) * coefs[i] for i in range(9)]
            valores = [v - 9 if v > 9 else v for v in valores]
            suma = sum(valores)
            dsup = ((suma // 10) + 1) * 10
            veri = dsup - suma
            if veri == 10:
                veri = 0
            return int(ced[9]) == veri
        except Exception:
            return False

    def _verifica_consumidor_final(self, vat):
        """Returns True if all digits are 9 (consumidor final pattern)."""
        try:
            return all(c == '9' for c in vat)
        except Exception:
            return False

    def _detect_type_ref(self, vat, id_type_rec):
        """
        Returns 'cedula', 'ruc', or 'passport'.
        Raises ValidationError on invalid format.
        """
        if not vat:
            return ''

        # sequence 90 = pasaporte, sequence 100 = extranjero/RUC exterior
        if id_type_rec and id_type_rec.sequence in (90, 100):
            return 'passport'

        if not vat.isdigit():
            # If identification type is passport, allow alphanumeric
            if id_type_rec and 'pasaporte' in (id_type_rec.name or '').lower():
                return 'passport'
            raise ValidationError(_(
                'El número de identificación "%s" solo debe contener dígitos para cédula/RUC. '
                'Si es pasaporte, seleccione el tipo correspondiente.'
            ) % vat)

        # Consumidor final: must be 13 nines
        if self._verifica_consumidor_final(vat):
            if len(vat) != 13:
                raise ValidationError(_(
                    'El consumidor final debe tener 13 dígitos (9999999999001). '
                    'No se permite la versión de 10 dígitos.'
                ))
            return 'ruc'

        id_name = (id_type_rec.name or '').lower() if id_type_rec else ''
        # When no ID type is selected, auto-detect by length (allows programmatic vat setting)
        auto_detect = not id_name

        if len(vat) == 10 and ('c' in id_name or auto_detect):  # Cédula
            if not self._verifica_cedula(vat):
                raise ValidationError(_(
                    'La cédula "%s" no es válida. Por favor verifique el número.'
                ) % vat)
            return 'cedula'

        if len(vat) == 13 and ('ruc' in id_name or auto_detect):
            # Validate the first 10 digits as cedula base
            tercero = int(vat[2])
            if tercero not in (0, 1, 6, 9):
                raise ValidationError(_(
                    'El RUC "%s" no tiene un tercer dígito válido (debe ser 0, 1, 6 o 9).'
                ) % vat)
            if tercero in (0, 1):
                # Persona natural or sociedades privadas: validate first 10 digits
                if not self._verifica_cedula(vat[:10]):
                    raise ValidationError(_(
                        'Los primeros 10 dígitos del RUC "%s" no son válidos.'
                    ) % vat)
            return 'ruc'

        raise ValidationError(_(
            'El número de identificación "%s" no corresponde al tipo seleccionado. '
            'Verifique la longitud y el tipo de identificación.'
        ) % vat)

    def _get_sri_api_config(self):
        """Returns (api_url, api_token) from ir.config_parameter."""
        ICP = self.env['ir.config_parameter'].sudo()
        url = ICP.get_param('validate_ec_sri.api_url', default='https://cedula.trionica.ec').rstrip('/')
        token = ICP.get_param('validate_ec_sri.api_token', default='')
        return url, token

    def _query_persona_api(self, vat, api_url, headers):
        """Query /persona/{vat} with /fetchdata fallback.
        Returns (data_dict, source) or (None, None) on failure.
        source is 'persona' or 'fetchdata'.
        """
        # Primary: /persona/{vat}
        try:
            resp = requests.get(f'{api_url}/persona/{vat}', headers=headers, timeout=15)
            if resp.status_code == 200:
                return resp.json(), 'persona'
        except Exception as e:
            _logger.warning('validate_ec_sri: /persona/%s error: %s', vat, e)

        # Fallback: /fetchdata?name={vat} (broader search, uses different source)
        try:
            resp = requests.get(
                f'{api_url}/fetchdata',
                params={'name': vat},
                headers=headers,
                timeout=15,
            )
            if resp.status_code == 200:
                data = resp.json()
                # fetchdata returns {status, data: [{...}]} — unwrap first result
                items = data.get('data', data)
                if isinstance(items, list) and items:
                    return items[0], 'fetchdata'
                elif isinstance(items, dict):
                    return items, 'fetchdata'
            elif resp.status_code == 409:
                # Multiple results — take first candidate
                detail = resp.json().get('detail', {})
                candidates = detail.get('candidates', [])
                if candidates:
                    return candidates[0], 'fetchdata'
        except Exception as e:
            _logger.warning('validate_ec_sri: /fetchdata/%s error: %s', vat, e)

        return None, None

    def _get_ec_id_types(self):
        """Return (cedula_type, ruc_type) l10n_latam.identification.type records for Ecuador."""
        ec = self.env['res.country'].search([('code', '=', 'EC')], limit=1)
        types = self.env['l10n_latam.identification.type'].search([('country_id', '=', ec.id)])
        cedula = types.filtered(lambda t: 'dula' in (t.name or '').lower())[:1]
        ruc = types.filtered(lambda t: (t.name or '').lower().strip() == 'ruc')[:1]
        return cedula, ruc

    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        ecuador = self.env['res.country'].search([('code', '=', 'EC')], limit=1)
        if 'country_id' in fields_list and not defaults.get('country_id') and ecuador:
            defaults['country_id'] = ecuador.id
        if 'lang' in fields_list and not defaults.get('lang'):
            defaults['lang'] = 'es_EC'
        return defaults

    def _parse_ec_address(self, direccion):
        """Parse SRI address 'PROVINCIA / CANTON / PARROQUIA / CALLE' into Odoo fields.
        Always sets country_id = Ecuador. Maps province to state_id, canton to city.
        Falls back to putting the full string in street if format is not recognized.
        """
        vals = {}
        if not direccion:
            return vals
        ecuador = self.env['res.country'].search([('code', '=', 'EC')], limit=1)
        if ecuador:
            vals['country_id'] = ecuador.id
        parts = [p.strip() for p in direccion.split('/') if p.strip()]
        if not parts:
            vals['street'] = direccion
            return vals
        # Try to identify first part as an Ecuadorian province
        state = self.env['res.country.state'].search([
            ('country_id.code', '=', 'EC'),
            ('name', 'ilike', parts[0]),
        ], limit=1)
        if state:
            vals['state_id'] = state.id
            if len(parts) >= 2:
                vals['city'] = parts[1].title()
            # Street = from index 3 onward (skip parroquia at index 2)
            if len(parts) >= 4:
                vals['street'] = ' / '.join(parts[3:])
            elif len(parts) == 3:
                vals['street'] = parts[2]
        else:
            # Province not recognized → put everything as street
            vals['street'] = direccion
        return vals

    def _fill_vals_from_persona(self, data, source):
        """Extract partner values from persona API response dict.
        Handles both flat and nested {tipo, datos:{nombres,...}} formats.
        """
        # Nested format: {tipo: "ciudadano", datos: {nombres, direccion, ...}}
        datos = data.get('datos') or {}
        nombre = (
            datos.get('nombres') or datos.get('nombre_completo')
            or data.get('nombre') or data.get('name')
            or data.get('nombres') or data.get('nombre_completo')
            or ''
        ).strip()
        vals = {
            'company_type': 'person',
            'type_ref': 'cedula',
            'sri_verified': True,
            'sri_last_check': fields.Datetime.now(),
        }
        if nombre:
            vals['name'] = nombre
        direccion = (datos.get('direccion') or data.get('direccion') or '').strip()
        if direccion:
            vals.update(self._parse_ec_address(direccion))
        celular1 = (datos.get('celular1') or data.get('celular1') or '').strip()
        if celular1:
            vals['phone'] = celular1
        celular2 = (datos.get('celular2') or data.get('celular2') or '').strip()
        if celular2:
            vals['mobile'] = celular2
        correo = (datos.get('correo') or data.get('correo') or '').strip()
        if correo:
            vals['email'] = correo
        return vals

    # ── Onchange: auto-fill when VAT is complete (10 or 13 digits) ───────────

    @api.onchange('vat', 'l10n_latam_identification_type_id')
    def _onchange_vat_auto_fetch(self):
        """Automatically query SRI/RC API when VAT is exactly 10 or 13 digits.
        Sets a preliminary name from the VAT itself so Odoo's required-field
        validation passes even before the API responds.
        """
        vat = (self.vat or '').strip()
        if not vat or len(vat) not in (10, 13) or not vat.isdigit():
            return

        # ── Step 1: auto-detect type (Cédula / RUC) and company_type ─────────
        cedula_type, ruc_type = self._get_ec_id_types()
        if len(vat) == 10:
            self.company_type = 'person'
            if cedula_type and self.l10n_latam_identification_type_id != cedula_type:
                self.l10n_latam_identification_type_id = cedula_type
        else:
            self.company_type = 'company'
            if ruc_type and self.l10n_latam_identification_type_id != ruc_type:
                self.l10n_latam_identification_type_id = ruc_type

        # ── Step 2: set preliminary name so "required" validation passes ─────
        if not self.name:
            self.name = vat  # will be replaced by real name if API responds

        # ── Step 3: query the API ─────────────────────────────────────────────
        api_url, api_token = self._get_sri_api_config()
        if not api_token:
            return {
                'warning': {
                    'title': 'API no configurada',
                    'message': (
                        'Configure el Token del API en '
                        'Ajustes → SRI Ecuador para auto-rellenar datos.'
                    ),
                }
            }

        headers = {'X-Credits-Token': api_token}

        if len(vat) == 10:
            data, source = self._query_persona_api(vat, api_url, headers)
            if not data:
                return  # Not found — keep preliminary name (= vat), user can edit
            vals = self._fill_vals_from_persona(data, source)
            for k, v in vals.items():
                setattr(self, k, v)
            return

        # RUC: single endpoint (SRI has full coverage)
        try:
            resp = requests.get(f'{api_url}/empresa/{vat}', headers=headers, timeout=12)
        except Exception as e:
            _logger.warning('validate_ec_sri: connection error on onchange: %s', e)
            return

        if resp.status_code != 200:
            _logger.warning('validate_ec_sri: API returned %s on onchange', resp.status_code)
            return

        try:
            data = resp.json()
        except Exception:
            return

        # Fill RUC fields
        razon_social = (data.get('razon_social') or '').strip()
        if razon_social:
            self.name = razon_social
        self.company_type = 'company'
        self.type_ref = 'ruc'
        if data.get('nombre_comercial'):
            self.sri_nombre_comercial = data['nombre_comercial']
        if data.get('estado'):
            self.sri_estado = data['estado']
        if data.get('actividad'):
            self.sri_actividad = data['actividad']
        if data.get('regimen'):
            self.sri_regimen = data['regimen']
        if data.get('obligado_contabilidad'):
            self.sri_obligado_contabilidad = data['obligado_contabilidad']
        if data.get('agente_retencion'):
            self.sri_agente_retencion = data['agente_retencion']
        if data.get('contribuyente_especial'):
            self.sri_contribuyente_especial = data['contribuyente_especial']
        if data.get('tipo'):
            self.sri_tipo = data['tipo']
        if data.get('direccion'):
            addr_vals = self._parse_ec_address(data['direccion'])
            for k, v in addr_vals.items():
                setattr(self, k, v)
        self.sri_verified = True
        self.sri_last_check = fields.Datetime.now()

    # ── Main button action ────────────────────────────────────────────────────

    def action_fetch_sri_data(self):
        """Query the SRI/RC API and fill partner fields."""
        self.ensure_one()

        if not self.vat:
            raise UserError(_('Ingrese el número de identificación antes de consultar.'))

        api_url, api_token = self._get_sri_api_config()

        if not api_token:
            raise UserError(_(
                'Configure el Token del API en Ajustes → Validación Ecuador SRI '
                'antes de usar esta función.'
            ))

        headers = {'X-Credits-Token': api_token}
        vat = self.vat.strip()

        if len(vat) not in (10, 13):
            raise UserError(_(
                'El número de identificación debe tener 10 dígitos (cédula) '
                'o 13 dígitos (RUC).'
            ))

        cedula_type, ruc_type = self._get_ec_id_types()
        vals = {'sri_verified': True, 'sri_last_check': fields.Datetime.now()}
        if len(vat) == 10:
            vals['company_type'] = 'person'
            if cedula_type:
                vals['l10n_latam_identification_type_id'] = cedula_type.id
        else:
            vals['company_type'] = 'company'
            if ruc_type:
                vals['l10n_latam_identification_type_id'] = ruc_type.id

        if len(vat) == 10:
            # Persona natural — try /persona then /fetchdata fallback
            data, source = self._query_persona_api(vat, api_url, headers)
            if not data:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('No encontrado'),
                        'message': _(
                            'La cédula "%s" no fue encontrada en el Registro Civil. '
                            'El contacto fue guardado, verifique el nombre manualmente.'
                        ) % vat,
                        'type': 'warning',
                        'sticky': True,
                    },
                }
            persona_vals = self._fill_vals_from_persona(data, source)
            vals.update(persona_vals)

        else:
            # Empresa / RUC — query SRI directly
            try:
                resp = requests.get(f'{api_url}/empresa/{vat}', headers=headers, timeout=15)
            except requests.exceptions.Timeout:
                raise UserError(_('El servicio SRI no respondió a tiempo. Intente nuevamente.'))
            except requests.exceptions.ConnectionError:
                raise UserError(_('No se pudo conectar al API. Verifique la URL en Ajustes.'))

            if resp.status_code == 401:
                raise UserError(_('Token inválido. Verifique el Token en Ajustes → SRI Ecuador.'))
            if resp.status_code == 429:
                raise UserError(_('Límite de consultas alcanzado. Intente en un momento.'))
            if resp.status_code == 404:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('No encontrado'),
                        'message': _('El RUC "%s" no fue encontrado en el SRI.') % vat,
                        'type': 'warning',
                        'sticky': True,
                    },
                }
            if resp.status_code != 200:
                raise UserError(_('El SRI devolvió un error (%s).') % resp.status_code)

            try:
                data = resp.json()
            except Exception:
                raise UserError(_('Respuesta inválida del API.'))

            razon_social = (data.get('razon_social') or '').strip()
            if razon_social:
                vals['name'] = razon_social
            vals['company_type'] = 'company'
            vals['type_ref'] = 'ruc'
            if data.get('nombre_comercial'):
                vals['sri_nombre_comercial'] = data['nombre_comercial']
            if data.get('estado'):
                vals['sri_estado'] = data['estado']
            if data.get('actividad'):
                vals['sri_actividad'] = data['actividad']
            if data.get('regimen'):
                vals['sri_regimen'] = data['regimen']
            if data.get('obligado_contabilidad'):
                vals['sri_obligado_contabilidad'] = data['obligado_contabilidad']
            if data.get('agente_retencion'):
                vals['sri_agente_retencion'] = data['agente_retencion']
            if data.get('contribuyente_especial'):
                vals['sri_contribuyente_especial'] = data['contribuyente_especial']
            if data.get('tipo'):
                vals['sri_tipo'] = data['tipo']
            if data.get('direccion'):
                vals.update(self._parse_ec_address(data['direccion']))

        self.write(vals)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Datos cargados'),
                'message': _(
                    'Información actualizada desde %s.'
                ) % ('Registro Civil' if len(vat) == 10 else 'SRI'),
                'type': 'success',
                'sticky': False,
            },
        }

    # ── Name-based search wizard ──────────────────────────────────────────────

    def action_open_name_search_wizard(self):
        """Open wizard to search by name and autofill partner data."""
        self.ensure_one()
        api_url, api_token = self._get_sri_api_config()
        if not api_token:
            raise UserError(_(
                'Configure el Token del API en Ajustes → Validación Ecuador SRI '
                'antes de usar esta función.'
            ))
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'validate.ec.sri.name.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_partner_id': self.id,
                'default_name_query': self.name or '',
            },
        }

    # ── Format / uniqueness constraints ──────────────────────────────────────

    @api.constrains('vat', 'l10n_latam_identification_type_id')
    def _check_vat_format(self):
        for rec in self:
            if not rec.vat:
                continue
            id_type = rec.l10n_latam_identification_type_id
            rec._detect_type_ref(rec.vat, id_type)

    # Uniqueness check removed — Odoo already shows a soft warning banner for
    # duplicate VATs, which allows the user to query/verify without being blocked.

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vat = vals.get('vat', '')
            if not vat:
                continue

            # Consumidor final: must be 13 digits
            if vat.isdigit() and self._verifica_consumidor_final(vat) and len(vat) == 10:
                raise ValidationError(_(
                    'No puede crear el consumidor final con 10 dígitos. '
                    'Use 9999999999001 (13 dígitos).'
                ))

            id_type_id = vals.get('l10n_latam_identification_type_id')
            id_type_rec = (
                self.env['l10n_latam.identification.type'].browse(int(id_type_id))
                if id_type_id else
                self.env['l10n_latam.identification.type'].browse()
            )
            try:
                vals['type_ref'] = self._detect_type_ref(vat, id_type_rec)
            except ValidationError:
                raise
        return super().create(vals_list)

    def write(self, vals):
        vat_changed = 'vat' in vals or 'l10n_latam_identification_type_id' in vals
        for rec in self:
            if not vat_changed:
                continue

            # Protect consumidor final from edits by non-admins
            if (rec.vat == '9999999999001'
                    and self.env.uid != self.env.ref('base.user_root').id
                    and ('vat' in vals or 'name' in vals)):
                raise UserError(_('No puede modificar los datos del Consumidor Final.'))

            vat = vals.get('vat', rec.vat)
            if not vat:
                continue

            id_type_id = vals.get(
                'l10n_latam_identification_type_id',
                rec.l10n_latam_identification_type_id.id,
            )
            id_type_rec = self.env['l10n_latam.identification.type'].browse(int(id_type_id)) if id_type_id else self.env['l10n_latam.identification.type'].browse()
            try:
                vals['type_ref'] = rec._detect_type_ref(vat, id_type_rec)
            except ValidationError:
                raise

        return super().write(vals)

    def copy_data(self, default=None):
        if default is None:
            default = {}
        default.update({'vat': False, 'type_ref': False, 'sri_verified': False})
        return super().copy_data(default)

    # ── Search by VAT / nombre comercial ─────────────────────────────────────

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        res = super().name_search(name, args, operator, limit)
        if not res and name:
            partners = self.search(
                ['|', ('vat', operator, name), ('sri_nombre_comercial', operator, name)]
                + (args or []),
                limit=limit,
            )
            if partners:
                res = partners.name_get()
        return res
