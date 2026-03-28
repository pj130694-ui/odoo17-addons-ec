# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging
import re

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    binance_prepay_id = fields.Char(
        string="Binance Prepay ID", readonly=True,
    )
    binance_merchant_trade_no = fields.Char(
        string="Binance Merchant Trade No", readonly=True,
        help="The sanitized reference sent to Binance Pay (alphanumeric, max 32 chars).",
    )
    binance_transaction_id = fields.Char(
        string="Binance Transaction ID", readonly=True,
    )
    binance_commission = fields.Float(
        string="Binance Commission", readonly=True, digits=(16, 8),
    )

    # === BUSINESS METHODS - RENDERING === #

    def _get_specific_rendering_values(self, processing_values):
        """ Override to create a Binance Pay order and return checkout data. """
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider_code != 'binance':
            return res

        # Create the order on Binance Pay
        order_data = self._binance_create_order()

        self.write({
            'binance_prepay_id': order_data.get('prepayId'),
            'binance_merchant_trade_no': self._binance_sanitize_reference(self.reference),
        })

        res.update({
            'checkout_url': order_data.get('checkoutUrl', ''),
            'qrcode_link': order_data.get('qrcodeLink', ''),
            'api_url': '/payment/binance/redirect',
        })
        return res

    def _get_specific_processing_values(self, processing_values):
        """ Override to add Binance-specific processing values. """
        res = super()._get_specific_processing_values(processing_values)
        if self.provider_code != 'binance':
            return res
        return res

    # === BUSINESS METHODS - NOTIFICATION === #

    @api.model
    def _get_tx_from_notification_data(self, provider_code, notification_data):
        """ Override to find transaction from Binance Pay webhook data. """
        tx = super()._get_tx_from_notification_data(provider_code, notification_data)
        if provider_code != 'binance' or len(tx) == 1:
            return tx

        merchant_trade_no = notification_data.get('merchantTradeNo')
        if not merchant_trade_no:
            raise ValidationError(_(
                "Binance Pay: Received notification with missing merchantTradeNo."
            ))

        # Search by the sanitized reference stored in binance_merchant_trade_no
        tx = self.search([
            ('binance_merchant_trade_no', '=', merchant_trade_no),
            ('provider_code', '=', 'binance'),
        ], limit=1)

        if not tx:
            # Fallback: try matching the original reference
            tx = self.search([
                ('reference', '=', merchant_trade_no),
                ('provider_code', '=', 'binance'),
            ], limit=1)

        if not tx:
            raise ValidationError(_(
                "Binance Pay: No transaction found for merchantTradeNo %(ref)s.",
                ref=merchant_trade_no,
            ))

        return tx

    def _process_notification_data(self, notification_data):
        """ Override to process Binance Pay webhook data and update transaction state. """
        super()._process_notification_data(notification_data)
        if self.provider_code != 'binance':
            return

        biz_status = notification_data.get('bizStatus')
        transaction_id = notification_data.get('transactionId')
        commission = notification_data.get('commission', 0)

        if transaction_id:
            self.provider_reference = transaction_id

        vals = {}
        if transaction_id:
            vals['binance_transaction_id'] = transaction_id
        if commission:
            vals['binance_commission'] = float(commission)
        if vals:
            self.write(vals)

        if biz_status == 'PAY_SUCCESS':
            self._set_done()
        elif biz_status in ('PAY_CLOSED', 'PAY_FAIL'):
            self._set_canceled(state_message=_("Binance Pay: %s", biz_status))
        elif biz_status == 'REFUND_SUCCESS':
            self._set_canceled(
                state_message=_("Refunded via Binance Pay"),
                extra_allowed_states=('done',),
            )
        else:
            _logger.info(
                "Binance Pay: received unhandled bizStatus '%s' for tx %s",
                biz_status, self.reference,
            )

    # === BINANCE PAY ORDER CREATION === #

    def _binance_create_order(self):
        """Create an order on Binance Pay and return the response data.

        :return: Order data from Binance Pay API
        :rtype: dict
        """
        self.ensure_one()
        provider = self.provider_id
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        merchant_trade_no = self._binance_sanitize_reference(self.reference)

        # Build description from sale order or invoice if available
        description = self._binance_get_order_description()

        payload = {
            "env": {"terminalType": "WEB"},
            "merchantTradeNo": merchant_trade_no,
            "orderAmount": self._binance_format_amount(self.amount),
            "currency": provider.binance_settlement_currency,
            "description": description[:256],
            "goodsDetails": [{
                "goodsType": "02",
                "goodsCategory": "Z000",
                "referenceGoodsId": merchant_trade_no,
                "goodsName": self._binance_sanitize_goods_name(description)[:256],
            }],
            "returnUrl": f"{base_url}/payment/binance/return?ref={merchant_trade_no}",
            "cancelUrl": f"{base_url}/payment/binance/cancel?ref={merchant_trade_no}",
            "webhookUrl": f"{base_url}/payment/binance/webhook",
            "passThroughInfo": json.dumps({
                "odoo_reference": self.reference,
                "odoo_tx_id": self.id,
            }),
        }

        return provider._binance_make_request(
            '/binancepay/openapi/v3/order', payload,
        )

    def _binance_query_order(self):
        """Query order status from Binance Pay.

        :return: Order data from Binance Pay API
        :rtype: dict
        """
        self.ensure_one()
        merchant_trade_no = self.binance_merchant_trade_no or \
            self._binance_sanitize_reference(self.reference)

        return self.provider_id._binance_make_request(
            '/binancepay/openapi/v2/order/query',
            {"merchantTradeNo": merchant_trade_no},
        )

    # === CRON: POLL PENDING TRANSACTIONS === #

    @api.model
    def _cron_binance_poll_pending(self):
        """Poll Binance Pay for status updates on pending/draft transactions.

        This is a fallback in case webhooks are missed or delayed.
        """
        pending_txs = self.search([
            ('provider_code', '=', 'binance'),
            ('state', 'in', ('draft', 'pending')),
            ('binance_merchant_trade_no', '!=', False),
        ], limit=50)

        for tx in pending_txs:
            try:
                order_data = tx._binance_query_order()
                status = order_data.get('status')

                if status == 'PAID':
                    notification_data = {
                        'bizStatus': 'PAY_SUCCESS',
                        'merchantTradeNo': tx.binance_merchant_trade_no,
                        'transactionId': order_data.get('transactionId'),
                        'commission': order_data.get('commission', 0),
                    }
                    tx._process_notification_data(notification_data)
                elif status in ('CANCELED', 'EXPIRED', 'ERROR'):
                    tx._set_canceled(
                        state_message=_("Binance Pay order status: %s", status),
                    )

                self.env.cr.commit()
            except Exception as e:
                _logger.warning(
                    "Binance Pay: failed to poll tx %s: %s", tx.reference, e,
                )
                self.env.cr.rollback()

    # === HELPERS === #

    @staticmethod
    def _binance_sanitize_reference(reference):
        """Sanitize Odoo reference for Binance Pay merchantTradeNo.

        Binance Pay requires alphanumeric only, max 32 characters.

        :param str reference: The Odoo transaction reference
        :return: The sanitized reference
        :rtype: str
        """
        sanitized = re.sub(r'[^a-zA-Z0-9]', '', reference or '')
        return sanitized[:32] or 'TX0'

    @staticmethod
    def _binance_format_amount(amount):
        """Format amount for Binance Pay (max 8 decimal places).

        :param float amount: The amount
        :return: The formatted amount
        :rtype: float
        """
        return round(float(amount), 8)

    def _binance_get_order_description(self):
        """Build a human-readable description for the Binance Pay order.

        :return: The description string
        :rtype: str
        """
        self.ensure_one()
        if hasattr(self, 'sale_order_ids') and self.sale_order_ids:
            names = ', '.join(self.sale_order_ids.mapped('name'))
            return f"Order {names}"
        if hasattr(self, 'invoice_ids') and self.invoice_ids:
            names = ', '.join(self.invoice_ids.mapped('name'))
            return f"Invoice {names}"
        return f"Payment {self.reference}"

    @staticmethod
    def _binance_sanitize_goods_name(name):
        r"""Remove characters forbidden in Binance Pay goodsName (\\, \", emoji).

        :param str name: The goods name
        :return: The sanitized name
        :rtype: str
        """
        # Remove backslash, double quote, and non-BMP characters (emoji)
        sanitized = re.sub(r'[\\"]', '', name or '')
        sanitized = re.sub(r'[^\u0000-\uFFFF]', '', sanitized)
        return sanitized.strip() or 'Payment'
