{
    'name': 'Google Sheet Product Importer',
    'version': '17.0.2.1.2',
    'author': 'PJFlow.io',
    'website': 'https://pjflow.io',
    'summary': 'Sync product variants from Google Sheets — with catalog archiving',
    'description': """
        Creates, updates, and archives product templates/variants by reading rows
        from a configured Google Sheet.

        v2 features:
        - gs_managed flag on product.template and product.product
        - Archive-missing sync: variants/templates removed from the sheet are
          auto-archived (active=False), never physically deleted
        - Auto-create missing product categories from full path (e.g.
          "Mining Hardware / BTC Miners / Antminer Air Cooling")
        - Smart UoM resolution with common aliases
        - Richer import log: archived variants/templates, categories created
        - Re-activation of previously archived gs_managed records when they
          reappear in the sheet
        - Enhanced Settings: sync mode toggle, category auto-create toggle
    """,
    'category': 'Inventory',
    'author': 'PJFlow.io',
    'price': 49.99,
    'currency': 'USD',
    'license': 'LGPL-3',
    'depends': ['stock', 'product', 'base_setup'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron.xml',
        'views/res_config_settings_views.xml',
        'views/import_log_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
