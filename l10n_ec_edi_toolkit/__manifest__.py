# -*- coding: utf-8 -*-
# Módulo técnico de herramientas EDI Ecuador
# Compatible con Odoo 17 Community + localización ecuatoriana TRESCLOUD
{
    'name': 'Herramientas EDI Ecuador (Toolkit)',
    'version': '17.0.1.0.0',
    'summary': (
        'Botón "Pasar a borrador" seguro para facturas EC '
        'y gestión de errores de autorización SRI.'
    ),
    'description': "Botones de gestion segura de facturas EC: reset a borrador y manejo de errores SRI.",
    'author': 'PJFlow.io',
    'category': 'Accounting/Localizations/EDI',
    'license': 'LGPL-3',
    'depends': [
        'account_edi',
        'l10n_ec_edi',
        'l10n_ec_reports_ats',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/account_move_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
