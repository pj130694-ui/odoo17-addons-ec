{
    'name': 'Nuevos Impuestos Ecuador 2026 Actualizados',
    'version': '17.0.1.0.0',
    'author': 'PJFlow.io',
    'website': 'https://pjflow.io',
    'category': 'Accounting/Localizations/Ecuador',
    'summary': (
        'Actualiza impuestos de retención IR según resolución SRI '
        'NAC-DGERCGC26-00000009, vigente el 01/03/2026. '
        'Reemplaza NAC-DGERCGC24-00000008.'
    ),
    'description': """
Parche fiscal para Ecuador - Resolución NAC-DGERCGC26-00000009
==============================================================

Cambios aplicados (vigencia 01/03/2026):
- Bienes muebles corporales (código 312): 1.75% → 2%
- Otras retenciones / residual (código 3440): 2.75% → 3%

Qué hace este módulo:
1. Crea el impuesto "312 2% Bienes Muebles Corporales" con XML ID persistente.
2. Crea el impuesto "3440 3% Otras Retenciones" con XML ID persistente.
3. Asigna las líneas de repartición contable correctas.
4. Actualiza res.company.l10n_ec_withhold_goods_tax_id → nuevo 2%.
5. Actualiza res.company.l10n_ec_withhold_services_tax_id → nuevo 3%.
6. Archiva (active=False) los impuestos 1.75% y 2.75% sin eliminar datos históricos.

Idempotente: si ya existen los taxes (por instalación previa o SQL manual),
los detecta y registra sus XML IDs sin crear duplicados.

No afecta:
- Documentos históricos (asientos ya contabilizados).
- RIMPE (1% y 0% sin cambio).
- Tipos de contribuyente con override específico.
- Retenciones de IVA.
    """,
    'author': 'PJFlow.io',
    'depends': ['l10n_ec_edi'],
    'data': [],
    'installable': True,
    'auto_install': False,
    'price': 19.99,
    'currency': 'USD',
    'license': 'LGPL-3',
    'images': ['static/description/images/cover.png'],
    'post_init_hook': 'post_init_hook',
}
