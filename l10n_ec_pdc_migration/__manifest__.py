{
    'name': 'Ecuador PDC Migration (Odoo 16 → 17)',
    'version': '17.0.1.0.0',
    'author': 'PJFlow.io',
    'website': 'https://pjflow.io',
    'category': 'Accounting',
    'summary': 'Migración de cheques ec_payment_check (Odoo 16) a sh_pdc (Odoo 17)',
    'depends': ['sh_pdc', 'sh_pdc_trionica_check_printing'],
    'data': [
        'security/ir.model.access.csv',
        'views/pdc_wizard_legacy_views.xml',
        'wizard/check_migration_wizard_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'price': 49.99,
    'currency': 'USD',
    'license': 'LGPL-3',
}
