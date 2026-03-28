# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models

from odoo.addons.payment import setup_provider, reset_payment_provider


def post_init_hook(env):
    setup_provider(env, 'binance')
    _create_binance_journal(env)


def _create_binance_journal(env):
    """Auto-create a Bank journal named 'Binance Pay' if it doesn't exist."""
    journal = env['account.journal'].search([
        ('code', '=', 'BNCP'),
        ('company_id', '=', env.company.id),
    ], limit=1)
    if journal:
        return journal

    # Find or create the currency (USD by default, since crypto settles in USD equiv)
    currency = env['res.currency'].search([('name', '=', 'USD')], limit=1)

    journal = env['account.journal'].create({
        'name': 'Binance Pay',
        'code': 'BNCP',
        'type': 'bank',
        'currency_id': currency.id if currency else False,
        'company_id': env.company.id,
    })
    return journal


def uninstall_hook(env):
    reset_payment_provider(env, 'binance')
