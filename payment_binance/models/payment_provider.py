# Part of Odoo. See LICENSE file for full copyright and licensing details.

import hashlib
import hmac
import json
import logging
import random
import string
import time

import requests

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

BINANCE_PAY_BASE_URL = "https://bpay.binanceapi.com"


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('binance', "Binance Pay")],
        ondelete={'binance': 'set default'},
    )
    binance_api_key = fields.Char(
        string="API Identity Key",
        required_if_provider='binance',
        groups='base.group_system',
    )
    binance_secret_key = fields.Char(
        string="API Secret Key",
        required_if_provider='binance',
        groups='base.group_system',
    )
    binance_settlement_currency = fields.Selection(
        [('USDT', 'USDT'), ('USDC', 'USDC'), ('BTC', 'BTC'),
         ('BNB', 'BNB'), ('ETH', 'ETH'), ('FDUSD', 'FDUSD')],
        string="Settlement Currency",
        default='USDT',
        required_if_provider='binance',
        help="The cryptocurrency you will receive when a customer pays.",
    )
    binance_webhook_url = fields.Char(
        string="Webhook URL",
        compute='_compute_binance_webhook_url',
        help="Copy this URL into the Binance Merchant Portal → Developer → Webhook URL.",
    )

    @api.depends('code')
    def _compute_binance_webhook_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for rec in self:
            if rec.code == 'binance':
                rec.binance_webhook_url = f"{base_url}/payment/binance/webhook"
            else:
                rec.binance_webhook_url = False

    # === COMPUTE METHODS === #

    def _compute_feature_support_fields(self):
        """ Override to set Binance Pay feature support. """
        super()._compute_feature_support_fields()
        self.filtered(lambda p: p.code == 'binance').update({
            'support_refund': 'partial',
        })

    def _compute_view_configuration_fields(self):
        """ Override to hide irrelevant fields for Binance Pay. """
        super()._compute_view_configuration_fields()
        self.filtered(lambda p: p.code == 'binance').update({
            'show_allow_tokenization': False,
            'show_allow_express_checkout': False,
        })

    # === BUSINESS METHODS === #

    def _get_supported_currencies(self):
        """ Binance Pay supports all currencies (auto-converted at checkout). """
        supported_currencies = super()._get_supported_currencies()
        if self.code != 'binance':
            return supported_currencies
        return supported_currencies

    def _get_default_payment_method_codes(self):
        """ Return default payment method codes for Binance Pay. """
        self.ensure_one()
        if self.code != 'binance':
            return super()._get_default_payment_method_codes()
        return ['binance']

    # === BINANCE PAY API === #

    def _binance_make_request(self, endpoint, payload):
        """Make authenticated request to Binance Pay API.

        :param str endpoint: API endpoint path (e.g. '/binancepay/openapi/v3/order')
        :param dict payload: Request body
        :return: The response data dict
        :rtype: dict
        :raises ValidationError: If the API returns an error
        """
        self.ensure_one()
        body_json = json.dumps(payload)
        timestamp, nonce, signature = self._binance_sign(body_json)

        headers = {
            "content-type": "application/json",
            "BinancePay-Timestamp": timestamp,
            "BinancePay-Nonce": nonce,
            "BinancePay-Certificate-SN": self.binance_api_key,
            "BinancePay-Signature": signature,
        }

        url = f"{BINANCE_PAY_BASE_URL}{endpoint}"
        _logger.info("Binance Pay API request to %s: %s", endpoint, body_json)

        try:
            response = requests.post(url, headers=headers, data=body_json, timeout=30)
        except requests.exceptions.RequestException as e:
            _logger.error("Binance Pay API connection error: %s", e)
            raise ValidationError(_(
                "Could not connect to Binance Pay. Please try again later."
            )) from e

        try:
            result = response.json()
        except ValueError:
            _logger.error("Binance Pay API non-JSON response (%s): %s",
                          response.status_code, response.text[:500])
            raise ValidationError(_(
                "Binance Pay returned an invalid response (HTTP %(code)s).",
                code=response.status_code,
            ))
        _logger.info("Binance Pay API response: %s", result)

        if result.get('status') != 'SUCCESS':
            error_code = result.get('code', 'unknown')
            error_msg = result.get('errorMessage', result.get('data', 'Unknown error'))
            _logger.error("Binance Pay API error %s: %s", error_code, error_msg)
            raise ValidationError(_(
                "Binance Pay error (%(code)s): %(msg)s",
                code=error_code,
                msg=error_msg,
            ))

        return result.get('data', {})

    def _binance_sign(self, body_json):
        """Generate HMAC-SHA512 signature for Binance Pay API.

        :param str body_json: JSON-encoded request body
        :return: Tuple of (timestamp, nonce, signature)
        :rtype: tuple(str, str, str)
        """
        self.ensure_one()
        timestamp = str(int(time.time() * 1000))
        nonce = ''.join(random.choices(string.ascii_letters, k=32))
        payload = f"{timestamp}\n{nonce}\n{body_json}\n"
        signature = hmac.new(
            self.binance_secret_key.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha512,
        ).hexdigest().upper()
        return timestamp, nonce, signature

    def action_binance_test_connection(self):
        """Test the API connection by querying a non-existent order."""
        self.ensure_one()
        try:
            self._binance_make_request(
                '/binancepay/openapi/v2/order/query',
                {"merchantTradeNo": "__TEST_CONNECTION__"},
            )
        except ValidationError as e:
            # 400202 = ORDER_NOT_FOUND means connection works fine
            if '400202' in str(e):
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _("Connection Successful"),
                        'message': _("Successfully connected to Binance Pay API."),
                        'type': 'success',
                        'sticky': False,
                    },
                }
            raise
