/** @odoo-module **/

import { _t } from '@web/core/l10n/translation';
import paymentForm from '@payment/js/payment_form';

paymentForm.include({
    // Binance Pay uses redirect flow (via redirect_form template),
    // so no special inline form handling is needed.
    // This file exists as a placeholder for future enhancements
    // (e.g., inline QR code display).
});
