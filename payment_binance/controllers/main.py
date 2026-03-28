# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging
import pprint

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class BinancePayController(http.Controller):

    _webhook_url = '/payment/binance/webhook'
    _return_url = '/payment/binance/return'
    _cancel_url = '/payment/binance/cancel'

    @http.route(_webhook_url, type='http', auth='public', methods=['POST'],
                csrf=False, save_session=False)
    def binance_webhook(self):
        """Handle Binance Pay webhook notifications.

        Binance sends a JSON body with:
        - bizType: 'PAY' | 'PAY_REFUND' | 'PAYOUT'
        - bizStatus: 'PAY_SUCCESS' | 'PAY_CLOSED' | 'PAY_FAIL' | ...
        - data: JSON string with order details

        We must return {"returnCode": "SUCCESS"} to acknowledge.
        """
        try:
            raw_body = request.httprequest.data.decode('utf-8')
            data = json.loads(raw_body)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            _logger.error("Binance Pay webhook: invalid JSON body: %s", e)
            return request.make_json_response(
                {"returnCode": "FAIL", "returnMessage": "Invalid JSON"},
            )

        _logger.info("Binance Pay webhook received:\n%s", pprint.pformat(data))

        biz_type = data.get('bizType')
        biz_status = data.get('bizStatus')

        # Parse the nested data (it's a JSON string inside the JSON body)
        try:
            biz_data = json.loads(data.get('data', '{}'))
        except (json.JSONDecodeError, TypeError):
            biz_data = {}

        if biz_type == 'PAY':
            self._handle_payment_notification(biz_status, biz_data)
        elif biz_type == 'PAY_REFUND':
            self._handle_refund_notification(biz_status, biz_data)
        else:
            _logger.info("Binance Pay webhook: unhandled bizType '%s'", biz_type)

        return request.make_json_response(
            {"returnCode": "SUCCESS", "returnMessage": None},
        )

    def _handle_payment_notification(self, biz_status, biz_data):
        """Process a PAY-type webhook notification.

        :param str biz_status: PAY_SUCCESS, PAY_CLOSED, or PAY_FAIL
        :param dict biz_data: Parsed order data from webhook
        """
        merchant_trade_no = biz_data.get('merchantTradeNo')
        if not merchant_trade_no:
            _logger.warning("Binance Pay webhook: missing merchantTradeNo in PAY notification")
            return

        notification_data = {
            'bizStatus': biz_status,
            'merchantTradeNo': merchant_trade_no,
            'transactionId': biz_data.get('transactionId'),
            'commission': biz_data.get('commission', 0),
            'totalFee': biz_data.get('totalFee'),
            'currency': biz_data.get('currency'),
            'passThroughInfo': biz_data.get('passThroughInfo'),
        }

        try:
            tx = request.env['payment.transaction'].sudo()._handle_notification_data(
                'binance', notification_data,
            )
            _logger.info(
                "Binance Pay webhook: tx %s updated to state '%s'",
                tx.reference, tx.state,
            )
        except Exception as e:
            _logger.exception("Binance Pay webhook: error processing payment notification: %s", e)

    def _handle_refund_notification(self, biz_status, biz_data):
        """Process a PAY_REFUND-type webhook notification.

        :param str biz_status: REFUND_SUCCESS or REFUND_REJECTED
        :param dict biz_data: Parsed refund data from webhook
        """
        merchant_trade_no = biz_data.get('merchantTradeNo')
        refund_info = biz_data.get('refundInfo', {})

        _logger.info(
            "Binance Pay webhook: refund %s for merchantTradeNo %s, status: %s",
            refund_info.get('refundRequestId'), merchant_trade_no, biz_status,
        )

        if not merchant_trade_no:
            return

        notification_data = {
            'bizStatus': biz_status,
            'merchantTradeNo': merchant_trade_no,
            'refundInfo': refund_info,
        }

        try:
            request.env['payment.transaction'].sudo()._handle_notification_data(
                'binance', notification_data,
            )
        except Exception as e:
            _logger.exception("Binance Pay webhook: error processing refund notification: %s", e)

    @http.route(_return_url, type='http', auth='public', methods=['GET'])
    def binance_return(self, **kwargs):
        """Handle customer return from Binance Pay checkout (after successful payment)."""
        ref = kwargs.get('ref', '')
        _logger.info("Binance Pay return: ref=%s", ref)

        # Find the transaction by sanitized reference
        tx = request.env['payment.transaction'].sudo().search([
            ('binance_merchant_trade_no', '=', ref),
            ('provider_code', '=', 'binance'),
        ], limit=1)

        if tx and tx.state == 'draft':
            # The webhook may not have arrived yet; set pending so post-processing picks it up
            tx._set_pending(state_message="Customer returned from Binance Pay checkout")

        return request.redirect('/payment/status')

    @http.route(_cancel_url, type='http', auth='public', methods=['GET'])
    def binance_cancel(self, **kwargs):
        """Handle customer cancellation from Binance Pay checkout."""
        ref = kwargs.get('ref', '')
        _logger.info("Binance Pay cancel: ref=%s", ref)

        tx = request.env['payment.transaction'].sudo().search([
            ('binance_merchant_trade_no', '=', ref),
            ('provider_code', '=', 'binance'),
        ], limit=1)

        if tx and tx.state in ('draft', 'pending'):
            tx._set_canceled(state_message="Customer cancelled Binance Pay checkout")

        return request.redirect('/payment/status')
