"""
NAC-DGERCGC26-00000009 — Post-init hook
========================================
Actualiza retenciones IR para Ecuador según resolución SRI vigente 01/03/2026.

Diseño:
- Todo el trabajo se hace aquí (sin archivos XML de datos).
- Idempotente: detecta si los taxes ya existen antes de crear.
- Sin IDs hardcodeados: busca por tipo fiscal, código ATS y empresa.
- Preserva datos históricos: archiva, no elimina.
"""

import logging
from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)

MODULE = 'l10n_ec_sri_2026'

# ---------------------------------------------------------------------------
# Definición de los nuevos impuestos
# ---------------------------------------------------------------------------
NEW_TAXES = [
    {
        # Reemplaza 1.75% 312 Transferencia Bienes
        'xml_suffix': 'tax_withhold_312_2pct',
        'name_es': '312 2% Bienes Muebles Corporales',
        'name_en': '2% 312',
        'amount': -2.0,
        'l10n_ec_code_base': '312',
        'l10n_ec_code_applied': '362',
        'l10n_ec_code_ats': '312',
        'account_code': '2114010203',   # Retenciones de la fuente 2%
        'sequence': 70,
        'company_field': 'l10n_ec_withhold_goods_tax_id',
        # Propiedades del tax obsoleto que reemplaza (para detectarlo sin XML ID fijo)
        'obsolete_amount': -1.75,
        'obsolete_code_ats': '312',
    },
    {
        # Reemplaza 2.75% 3440 Otras Retenciones
        'xml_suffix': 'tax_withhold_3440_3pct',
        'name_es': '3440 3% Otras Retenciones',
        'name_en': '3% 3440',
        'amount': -3.0,
        'l10n_ec_code_base': '3440',
        'l10n_ec_code_applied': '3940',
        'l10n_ec_code_ats': '3440',
        'account_code': '2114010211',   # Retenciones de la fuente 3%
        'sequence': 80,
        'company_field': 'l10n_ec_withhold_services_tax_id',
        'obsolete_amount': -2.75,
        'obsolete_code_ats': '3440',
    },
]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def post_init_hook(env):
    """
    Se ejecuta una sola vez al instalar el módulo.

    Idempotente: si se desinstala y reinstala, detecta el estado real de la BD
    y no crea duplicados.
    """
    _logger.info('[%s] *** Iniciando post_init_hook NAC-DGERCGC26-00000009 ***', MODULE)

    companies = _get_ec_companies(env)
    if not companies:
        _logger.warning(
            '[%s] No se encontraron empresas con localización Ecuador. '
            'Verifique que l10n_ec_edi esté instalado y configurado.', MODULE
        )
        return

    for company in companies:
        _logger.info('[%s] Procesando empresa: %s (ID=%s)', MODULE, company.name, company.id)

        tax_group = _get_withhold_income_tax_group(env, company)
        if not tax_group:
            _logger.warning(
                '[%s] No se encontró tax group withhold_income_purchase para %s. Saltando.',
                MODULE, company.name
            )
            continue

        country_ec = _get_ecuador_country(env)

        created_taxes = {}
        for tax_def in NEW_TAXES:
            new_tax = _get_or_create_tax(env, company, tax_group, country_ec, tax_def)
            if new_tax:
                created_taxes[tax_def['company_field']] = (new_tax, tax_def)

        _update_company_defaults(env, company, created_taxes)
        _archive_obsolete_taxes(env, company)

    _logger.info('[%s] *** post_init_hook completado. ***', MODULE)


# ---------------------------------------------------------------------------
# Helpers: búsqueda de entidades base
# ---------------------------------------------------------------------------

def _get_ec_companies(env):
    """Retorna solo las empresas que tienen localización Ecuador (tienen tax groups EC)."""
    all_companies = env['res.company'].search([])
    ec_companies = env['res.company']
    for company in all_companies:
        has_ec = bool(env['account.tax.group'].search([
            ('l10n_ec_type', '!=', False),
            ('company_id', '=', company.id),
        ], limit=1))
        if has_ec:
            ec_companies |= company
    return ec_companies


def _get_withhold_income_tax_group(env, company):
    return env['account.tax.group'].search([
        ('l10n_ec_type', '=', 'withhold_income_purchase'),
        ('company_id', '=', company.id),
    ], limit=1)


def _get_ecuador_country(env):
    country = env.ref('base.ec', raise_if_not_found=False)
    if not country:
        country = env['res.country'].search([('code', '=', 'EC')], limit=1)
    return country


def _get_account_by_code(env, code, company):
    return env['account.account'].with_context(active_test=False).search([
        ('code', '=', code),
        ('company_id', '=', company.id),
    ], limit=1)


# ---------------------------------------------------------------------------
# Helpers: creación / búsqueda de impuestos
# ---------------------------------------------------------------------------

def _get_or_create_tax(env, company, tax_group, country_ec, tax_def):
    """
    Estrategia en 3 niveles (idempotencia):

    1. Busca por XML ID registrado por este módulo → ya instalado antes.
    2. Busca por propiedades funcionales (amount + code_ats + tax_group + company)
       → tax creado manualmente en BD o por una versión anterior del parche.
    3. Crea el tax desde cero.
    """
    xml_name = f"{tax_def['xml_suffix']}_{company.id}"
    AccountTax = env['account.tax'].with_context(active_test=False)

    # -- Nivel 1: buscar por XML ID del módulo --
    imd = env['ir.model.data'].search([
        ('module', '=', MODULE),
        ('name', '=', xml_name),
        ('model', '=', 'account.tax'),
    ], limit=1)

    if imd and imd.res_id:
        tax = AccountTax.browse(imd.res_id)
        if tax.exists():
            _logger.info(
                '[%s] Tax "%s" ya existe por XML ID %s.%s (ID=%s). Sin cambio.',
                MODULE, tax_def['name_es'], MODULE, xml_name, tax.id
            )
            return tax
        else:
            _logger.warning('[%s] XML ID %s.%s huérfano. Se eliminará para recrear.', MODULE, MODULE, xml_name)
            imd.unlink()

    # -- Nivel 2: buscar por propiedades funcionales --
    existing = AccountTax.search([
        ('amount', '=', tax_def['amount']),
        ('tax_group_id', '=', tax_group.id),
        ('company_id', '=', company.id),
        ('l10n_ec_code_ats', '=', tax_def['l10n_ec_code_ats']),
        ('type_tax_use', '=', 'none'),
        ('amount_type', '=', 'percent'),
    ], limit=1)

    if existing:
        _logger.info(
            '[%s] Tax "%s" encontrado por búsqueda funcional (ID=%s). '
            'Registrando XML ID sin duplicar.',
            MODULE, tax_def['name_es'], existing.id
        )
        if not existing.active:
            existing.write({'active': True})
            _logger.info('[%s] Tax ID=%s reactivado (estaba archivado).', MODULE, existing.id)
        _register_xml_id(env, xml_name, 'account.tax', existing.id)
        return existing

    # -- Nivel 3: crear nuevo --
    return _create_tax(env, company, tax_group, country_ec, tax_def, xml_name)


def _create_tax(env, company, tax_group, country_ec, tax_def, xml_name):
    account = _get_account_by_code(env, tax_def['account_code'], company)
    if not account:
        _logger.warning(
            '[%s] Cuenta contable %s no encontrada en %s. '
            'El impuesto se creará SIN cuenta; asígnela manualmente.',
            MODULE, tax_def['account_code'], company.name
        )

    tax_vals = {
        'name': tax_def['name_es'],
        'amount': tax_def['amount'],
        'amount_type': 'percent',
        'type_tax_use': 'none',
        'active': True,
        'tax_group_id': tax_group.id,
        'company_id': company.id,
        'sequence': tax_def['sequence'],
        'price_include': False,
        'include_base_amount': False,
        'l10n_ec_code_base': tax_def['l10n_ec_code_base'],
        'l10n_ec_code_applied': tax_def['l10n_ec_code_applied'],
        'l10n_ec_code_ats': tax_def['l10n_ec_code_ats'],
    }
    if country_ec:
        tax_vals['country_id'] = country_ec.id

    tax = env['account.tax'].create(tax_vals)

    # Intentar agregar traducción inglés (no crítico si falla)
    try:
        tax.with_context(lang='en_US').write({'name': tax_def['name_en']})
    except Exception:
        pass

    _logger.info('[%s] Tax creado: "%s" (ID=%s)', MODULE, tax_def['name_es'], tax.id)

    _create_repartition_lines(env, tax, account)
    _register_xml_id(env, xml_name, 'account.tax', tax.id)

    return tax


def _create_repartition_lines(env, tax, account):
    """
    Crea 4 líneas de repartición: base+tax para invoice y base+tax para refund.
    company_id es campo related desde tax_id.company_id — Odoo lo calcula solo.
    """
    RLine = env['account.tax.repartition.line']
    account_id = account.id if account else False

    for doc_type in ('invoice', 'refund'):
        RLine.create({
            'tax_id': tax.id,
            'repartition_type': 'base',
            'factor_percent': 100,
            'document_type': doc_type,
            'use_in_tax_closing': False,
        })
        RLine.create({
            'tax_id': tax.id,
            'repartition_type': 'tax',
            'factor_percent': 100,
            'document_type': doc_type,
            'use_in_tax_closing': True,
            'account_id': account_id,
        })

    _logger.info('[%s] Repartition lines creadas para tax ID=%s', MODULE, tax.id)


# ---------------------------------------------------------------------------
# Helpers: registro de XML IDs
# ---------------------------------------------------------------------------

def _register_xml_id(env, name, model, res_id):
    IrModelData = env['ir.model.data']
    existing = IrModelData.search([
        ('module', '=', MODULE),
        ('name', '=', name),
    ], limit=1)
    if not existing:
        IrModelData.create({
            'module': MODULE,
            'name': name,
            'model': model,
            'res_id': res_id,
            'noupdate': True,
        })
    else:
        existing.write({'res_id': res_id, 'model': model})


# ---------------------------------------------------------------------------
# Helpers: defaults de empresa
# ---------------------------------------------------------------------------

def _update_company_defaults(env, company, created_taxes):
    """
    Actualiza l10n_ec_withhold_goods_tax_id y l10n_ec_withhold_services_tax_id
    SOLO si el campo apunta al tax obsoleto correspondiente o está vacío.
    No modifica configuraciones que el usuario haya personalizado.
    """
    update_vals = {}

    for field_name, (new_tax, tax_def) in created_taxes.items():
        current_tax = company[field_name]

        # Buscar el tax obsoleto por propiedades (sin depender de XML ID fijo)
        old_tax = _find_obsolete_tax(
            env, company,
            tax_def['obsolete_amount'],
            tax_def['obsolete_code_ats'],
        )

        if current_tax == new_tax:
            _logger.info(
                '[%s] %s.%s ya apunta al nuevo tax "%s". Sin cambio.',
                MODULE, company.name, field_name, new_tax.name
            )
        elif not current_tax or current_tax == old_tax:
            update_vals[field_name] = new_tax.id
            _logger.info(
                '[%s] %s.%s: "%s" → "%s"',
                MODULE, company.name, field_name,
                old_tax.name if old_tax else 'vacío',
                new_tax.name,
            )
        else:
            _logger.info(
                '[%s] %s.%s apunta a "%s" (no es el tax obsoleto esperado). '
                'Se respeta la configuración actual sin modificar.',
                MODULE, company.name, field_name, current_tax.name,
            )

    if update_vals:
        company.write(update_vals)


def _find_obsolete_tax(env, company, amount, code_ats):
    """Busca un tax por sus propiedades fiscales, independiente del ID de BD."""
    return env['account.tax'].with_context(active_test=False).search([
        ('amount', '=', amount),
        ('tax_group_id.l10n_ec_type', '=', 'withhold_income_purchase'),
        ('company_id', '=', company.id),
        ('l10n_ec_code_ats', '=', code_ats),
        ('type_tax_use', '=', 'none'),
        ('amount_type', '=', 'percent'),
    ], limit=1)


# ---------------------------------------------------------------------------
# Helpers: archivado de taxes obsoletos
# ---------------------------------------------------------------------------

def _archive_obsolete_taxes(env, company):
    """
    Archiva (active=False) los taxes 1.75% y 2.75% si están activos.
    NO los elimina. Los asientos históricos vinculados quedan intactos
    porque las FK en account_move_line_account_tax_rel y
    account_tax_repartition_line son a IDs de BD, independientes de active.
    """
    obsolete_defs = [
        {'amount': -1.75, 'code_ats': '312'},
        {'amount': -2.75, 'code_ats': '3440'},
    ]

    for defn in obsolete_defs:
        tax = _find_obsolete_tax(env, company, defn['amount'], defn['code_ats'])
        if not tax:
            _logger.info(
                '[%s] Tax obsoleto %.2f%% code=%s no encontrado en %s. Saltando.',
                MODULE, abs(defn['amount']), defn['code_ats'], company.name
            )
            continue

        if not tax.active:
            _logger.info(
                '[%s] Tax "%s" (ID=%s) ya está archivado. Sin cambio.',
                MODULE, tax.name, tax.id
            )
        else:
            tax.write({'active': False})
            _logger.info(
                '[%s] Tax "%s" (ID=%s) archivado correctamente.',
                MODULE, tax.name, tax.id
            )
