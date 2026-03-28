from odoo import models
from odoo.addons.payment_stripe import const


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    def _stripe_get_country(self, country_code):
        """Map Ecuador (EC) to US so Stripe Connect country validation passes.
        The business has a US Stripe account; EC is not natively supported by Stripe Connect.
        """
        if country_code == 'EC':
            return 'US'
        return super()._stripe_get_country(country_code)
