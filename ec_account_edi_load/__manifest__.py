# -*- coding: utf-8 -*-#
##############################################################################
#                                                                            #
# Copyright (C) Crystal Clear Solutions EP - All Rights Reserved             #
# Unauthorized copying of this file, via any medium is strictly prohibited   #
# Proprietary and confidential                                               #
# Written by CCS-EP, 2025              		     		 	                 #
#                                                                            #
##############################################################################

{
    'name': 'PJ Flow EDI Loader EC',
    # Upgrade the module to target Odoo 17.  The major version (17) reflects
    # the Odoo release and the minor/patch numbers can be incremented for
    # subsequent functional or bug‑fix releases.
    'version': '17.0.1.1',
    'author': 'PJFlow.io',
    'summary': 'Carga masiva de documentos electrónicos SRI para Odoo Ecuador',
    'category': 'Account',
    'sequence': 11,
    'description': """
Módulo desarrollado por PJ Flow para importar documentos electrónicos del SRI en Odoo Ecuador.

Características principales:
- Importación de facturas y retenciones desde archivos TXT y XML.
- Creación de retenciones de clientes por RUC como créditos aplicables.
- Creación de retenciones bancarias y de tarjeta como asientos contables.
- Compatibilidad con Odoo 17 Community y localización ecuatoriana.
- Diseñado para simplificar la carga masiva, reducir errores manuales y agilizar procesos contables.
""",
    'website': 'https://pjflow.io/',
    # Update dependencies for Odoo 17 Community and the official Ecuadorian localisation.
    # The legacy modules `ec_account_edi` and `ec_withholding` used in the v16 release
    # are replaced by the standard localisation modules `l10n_ec_edi` and
    # `l10n_ec_reports`.  In the original v16 module there was an extra dependency
    # on a custom module named ``ec_sri_authorizathions`` which provided menu
    # entries and mappings for SRI authorisations.  As those menus are now
    # provided elsewhere in your system and the code in this module does not
    # reference any objects from ``ec_sri_authorizathions``, that dependency has
    # been removed.  The module `account_accountant` is included to provide
    # additional accounting features available in the community edition.
    'depends': [
        'base',
        'account',
        'l10n_ec',
        'l10n_ec_edi',
        'l10n_ec_reports',
        'account_accountant',
        'stock',
        'sale',
    ],
    # Las dependencias externas de Python (suds, xmlsig, xades, etc.) se
    # gestionan con try/except en cada archivo que las usa, mostrando un
    # UserError descriptivo si faltan.  No se declaran en external_dependencies
    # para evitar que Odoo bloquee la instalación/actualización del módulo
    # cuando las librerías opcionales no están presentes en el entorno.
    'data': [
        'security/ir.model.access.csv',
        'views/account_edi_load_view.xml',
        'views/res_partner.xml',
        'views/report_payment_receipt.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}