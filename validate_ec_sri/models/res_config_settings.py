# -*- coding: utf-8 -*-

from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    validate_ec_sri_api_url = fields.Char(
        string='URL del API SRI/RC',
        config_parameter='validate_ec_sri.api_url',
        help='URL base del API de consultas. Ej: https://cedula.trionica.ec',
    )
    validate_ec_sri_api_token = fields.Char(
        string='Token de Acceso',
        config_parameter='validate_ec_sri.api_token',
        help='Token admin del API (X-Credits-Token). No consume créditos.',
    )
