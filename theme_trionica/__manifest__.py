# -*- coding: utf-8 -*-
{
    'name': 'Theme Trionica',
    'version': '17.0.1.0.0',
    'category': 'Theme/Website',
    'summary': 'Tema web oscuro y moderno para Trionica – tecnología, ventas y soporte.',
    'description': 'Tema personalizado para trionica.ec con diseño moderno dark-tech, homepage completa, animaciones y paleta de colores profesional.',
    'author': 'PJFlow.io',
    'website': 'https://trionica.ec',
    'depends': ['website', 'website_blog'],
    'data': [
        'views/assets.xml',
        'views/layout.xml',
        'views/homepage.xml',
        'data/cron.xml',
    ],
    'images': ['static/description/images/cover.png'],
    'installable': True,
    'auto_install': False,
    'application': False,
    'price': 59.99,
    'currency': 'USD',
    'license': 'LGPL-3',
}
