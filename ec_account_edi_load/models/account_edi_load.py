# -*- coding: utf-8 -*-#
#############################################################################
#                                                                           #
#Copyright (C) HackSystem, Inc - All Rights Reserved                        #
#Unauthorized copying of this file, via any medium is strictly prohibited   #
#Proprietary and confidential                                               #
#Written by Ing. Harry Alvarez <halvarezg@hacksystem.es>, 2023              #
#                                                                           #
#############################################################################


import os
import re
import time
import logging
import traceback
from lxml import etree
from xml.etree.ElementTree import Element, SubElement, tostring
from datetime import datetime, timedelta
# --------------------------------------------------------------------------
# Suds SOAP client dependency
# --------------------------------------------------------------------------
try:
    from suds import WebFault  # type: ignore
    from suds.client import Client  # type: ignore
except Exception:
    # ``suds`` (or ``suds-py3``) is not available.  Define a dummy Client
    # that raises a helpful UserError if someone tries to instantiate it.  We
    # also alias WebFault to a base Exception so that any ``except
    # WebFault`` clauses still catch the error class when suds is missing.
    WebFault = Exception  # type: ignore
    class Client:  # type: ignore
        def __init__(self, *args, **kwargs) -> None:
            from odoo.exceptions import UserError  # local import
            from odoo.tools.translate import _  # local import
            raise UserError(_(
                "La librería de cliente SOAP 'suds' no está instalada. "
                "Instale 'suds-py3' mediante pip para poder utilizar las "
                "funcionalidades de descarga de comprobantes electrónicos del SRI."
            ))
from pprint import pformat
# --------------------------------------------------------------------------
# py4j gateway dependency
# --------------------------------------------------------------------------
try:
    from py4j.java_gateway import JavaGateway, GatewayClient  # type: ignore
except Exception:
    # If ``py4j`` is missing, provide stubs that raise a helpful error on use.
    def _missing_py4j(*args, **kwargs):
        from odoo.exceptions import UserError
        from odoo.tools.translate import _
        raise UserError(_(
            "La librería 'py4j' no está instalada. "
            "Instale 'py4j' (por ejemplo, con pip) para poder utilizar la "
            "pasarela Java necesaria para la firma de documentos."
        ))
    class JavaGateway:  # type: ignore
        def __init__(self, *args, **kwargs) -> None:
            _missing_py4j()
    class GatewayClient:  # type: ignore
        def __init__(self, *args, **kwargs) -> None:
            _missing_py4j()
from odoo import models, api, fields, Command
from odoo import tools
from odoo.tools.translate import _
import odoo.addons
from odoo.tools.safe_eval import safe_eval as eval
# `except_orm` was removed in modern Odoo versions.  Import only
# the supported exception classes.  The `Warning` class is deprecated
# and can be replaced with `UserError` for user‑facing messages.
from odoo.exceptions import UserError, ValidationError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DTF
from odoo.tools import float_compare
import base64
# ``modules_mapping`` was imported from a custom module named
# ``ec_sri_authorizathions`` in the original v16 implementation.  That module
# provided additional mappings for SRI authorisations.  In the v17 upgrade
# this import is no longer required because the code does not make use of
# ``modules_mapping``.  Removing the import avoids an unnecessary
# dependency on an external module that is not installed in your system.
# --------------------------------------------------------------------------
# OpenSSL dependency
# --------------------------------------------------------------------------
try:
    from OpenSSL import crypto  # type: ignore
except Exception:
    class _MissingOpenSSL:  # type: ignore
        def __getattr__(self, name: str):
            from odoo.exceptions import UserError
            from odoo.tools.translate import _
            raise UserError(_(
                "La librería 'pyopenssl' (paquete OpenSSL) no está instalada. "
                "Instale 'pyopenssl' para poder procesar certificados digitales."
            ))
    crypto = _MissingOpenSSL()  # type: ignore
from random import randrange
try:
    import xmlsig  # type: ignore
except Exception:
    class _MissingXmlSig:  # type: ignore
        def __getattr__(self, name: str):
            from odoo.exceptions import UserError
            from odoo.tools.translate import _
            raise UserError(_(
                "La librería 'xmlsig' no está instalada. "
                "Instale 'xmlsig' para poder firmar documentos XML."
            ))
    xmlsig = _MissingXmlSig()  # type: ignore
try:
    from xades import template, XAdESContext  # type: ignore
    from xades.policy import GenericPolicyId, ImpliedPolicy  # type: ignore
except Exception:
    def _missing_xades(*args, **kwargs):
        from odoo.exceptions import UserError
        from odoo.tools.translate import _
        raise UserError(_(
            "La librería 'xades' no está instalada. "
            "Instale 'xades' (por ejemplo, con pip) para firmar documentos XML con XAdES."
        ))
    class _MissingXadesModule:
        def __getattr__(self, name: str):
            return _missing_xades
    template = _MissingXadesModule()  # type: ignore
    XAdESContext = _MissingXadesModule()  # type: ignore
    GenericPolicyId = _MissingXadesModule()  # type: ignore
    ImpliedPolicy = _MissingXadesModule()  # type: ignore
import json
try:
    import xmltodict  # type: ignore
except Exception:
    class _MissingXmlToDict:  # type: ignore
        def __getattr__(self, name: str):
            from odoo.exceptions import UserError
            from odoo.tools.translate import _
            raise UserError(_(
                "La librería 'xmltodict' no está instalada. "
                "Instale 'xmltodict' para poder procesar documentos XML como diccionarios."
            ))
    xmltodict = _MissingXmlToDict()  # type: ignore
from xml.etree.ElementTree import XML, Element

_logger = logging.getLogger(__name__)


class EcSriLoadEdi(models.Model):
    _name = 'ec.sri.load.edi'

    @api.model
    def new_import(self, *args, **kwargs):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'ec.sri.load.edi',
            'view_mode': 'form',
            'view_type': 'form',
            'views': [(False, 'form')],
            'target': 'new',
        }

    company_id = fields.Many2one("res.company","Compañia",default=lambda self: self.env.company)
    data_file = fields.Binary(string="Upload File")
    filename = fields.Char(string="File Name")
    results = fields.Text()
    process = fields.Boolean(default=False)
    type = fields.Selection([('txt','Txt'),
                             ('xml','XML'),], default='txt', string='Tipo')
    xmls_ids = fields.Many2many('ir.attachment', string='XMLs')
    file_name = fields.Char(string="Nombre del Archivo")
    file_data = fields.Binary(string="Archivo para Descarga", readonly=True)

    def create_line_retention(self,impuesto,is_credit_card,invoice_multiple_id=None):
        data = False
        try:
            porcentaje = float(impuesto.find('porcentajeRetener').text)
        except Exception:
            porcentaje = 0.0
        if impuesto.find('codigo').text == '1':
            description = 'retencion_renta'
            # Para retenciones de renta recibidas de clientes (out_withhold) debemos preferir
            # los impuestos con type_tax_use='sale', ya que estos tienen configurada la cuenta
            # de crédito tributario (activo corriente, p. ej. 101050301 "Reten. Fte. Imp. Rta.
            # Clientes") en su repartición de impuestos.  Los impuestos de tipo 'purchase'
            # apuntan a una cuenta de pasivo (retención a pagar a proveedores) que es incorrecta
            # para este flujo.
            # IMPORTANTE: si existen varias versiones del mismo código (ej. 312 al 1.75% y al 2%)
            # se prioriza la que tiene el porcentaje exacto del XML, evitando usar tasas antiguas.
            code_retencion = impuesto.find('codigoRetencion').text
            tax_id = self.env['account.tax'].browse()
            if porcentaje:
                tax_id = self.env['account.tax'].search([
                    ('l10n_ec_code_base', '=', code_retencion),
                    ('type_tax_use', '=', 'sale'),
                    ('amount', 'in', [porcentaje, -porcentaje]),
                ], limit=1)
            if not tax_id:
                tax_id = self.env['account.tax'].search([
                    ('l10n_ec_code_base', '=', code_retencion),
                    ('type_tax_use', '=', 'sale'),
                ], limit=1)
            if not tax_id:
                tax_id = self.env['account.tax'].search([('l10n_ec_code_base', '=', code_retencion)])
        else:
            description = 'retencion_iva'
            code_retencion = impuesto.find('codigoRetencion').text
            tax_id = self.env['account.tax'].browse()
            if porcentaje:
                tax_id = self.env['account.tax'].search([
                    ('l10n_ec_code_ats', '=', code_retencion),
                    ('type_tax_use', '=', 'sale'),
                    ('amount', 'in', [porcentaje, -porcentaje]),
                ], limit=1)
            if not tax_id:
                tax_id = self.env['account.tax'].search([('l10n_ec_code_ats', '=', code_retencion)])
        if not tax_id:
            return False
        if not is_credit_card:
            data = (0, 0, {'description': description,
                           'tax_id': tax_id[0].id if len(tax_id) > 0 else False,
                           'tax_base': float(impuesto.find('baseImponible').text),
                           'retention_percentage': float(impuesto.find('porcentajeRetener').text)})
            if invoice_multiple_id:
                data[2].update({'invoice_multiple_id': invoice_multiple_id.id})
        else:
            data = (0, 0, {'description': description,
                           'tax_id': tax_id[0].id if len(tax_id) > 0 else False,
                           'tax_base': float(impuesto.find('baseImponible').text),
                           'retention_percentage_manual'
                           : float(impuesto.find('porcentajeRetener').text)})

        return data

    # ------------------------------------------------------------------
    # Helpers for retentions in Odoo 17 (l10n_ec_edi)
    #
    # Odoo 17 no longer defines the model ``account.withhold``.  In the
    # modern localisation, retentions are regular ``account.move`` records
    # created through the wizard ``l10n_ec.wizard.account.withhold``.  The
    # following helper methods encapsulate the logic to locate the
    # appropriate journal, check for existing retentions and create a
    # retention using the wizard.
    def _find_withhold_journal(self, withhold_type: str = 'out_withhold'):
        """Locate a retention journal for the current company.

        The Ecuadorian localisation distinguishes between sales and purchase
        retentions via the ``l10n_ec_withhold_type`` field on journals.  For
        sales (the typical case for this module), the value is
        ``'out_withhold'``.  If no journal is found, a UserError is raised
        prompting the administrator to configure one.
        """
        journal = self.env['account.journal'].search([
            ('company_id', '=', self.company_id.id),
            ('l10n_ec_withhold_type', '=', withhold_type),
        ], limit=1)
        if not journal:
            raise UserError(_(
                "No existe un diario de retenciones configurado para %s. "
                "Cree o configure un diario con l10n_ec_withhold_type = %s." % (withhold_type, withhold_type)
            ))
        return journal

    def _withhold_exists(self, access_key: str, withhold_type: str = 'out_withhold') -> bool:
        """Determine whether a retention with the given SRI access key already exists.

        In Odoo 17 the ``account.withhold`` model is gone; instead, we search
        for an ``account.move`` whose journal's ``l10n_ec_withhold_type``
        matches and whose ``l10n_ec_authorization_number`` equals the access
        key.  Returns True if such a move exists.
        """
        return bool(self.env['account.move'].search([
            ('company_id', '=', self.company_id.id),
            ('journal_id.l10n_ec_withhold_type', '=', withhold_type),
            ('l10n_ec_authorization_number', '=', access_key),
        ], limit=1))

    def _create_withhold_l10n_ec(
        self,
        invoices,
        document_number: str,
        access_key: str,
        date_retention: str,
        impuestos_invoice_lines,
        withhold_type: str = 'out_withhold',
        remove_reconcile: bool = True,
        invoice_doc_number: str = '',
    ):
        """Create and post a retention via the l10n_ec_edi wizard.

        :param invoices: Recordset of account.move invoices to attach to
            the retention.
        :param document_number: The formatted retention number
        :param access_key: SRI access key for the retention.
        :param date_retention: ISO date string of issuance.
        :param impuestos_invoice_lines: List of (0,0,vals) triplets from
            create_line_retention.
        :param withhold_type: 'out_withhold' (sales) or 'in_withhold'
        :param remove_reconcile: When True (default) remove the automatic
            reconciliations created by the wizard so that the retention
            remains as an unapplied credit.  When False, leave the
            reconciliations in place to automatically apply the
            withholding amount to the invoices provided.  This option
            allows reproducing the behaviour from Odoo 16 where
            retentions on unpaid invoices are automatically matched and
            reduce the residual of the invoice.

        :return: Posted account.move representing the retention.
        """
        journal = self._find_withhold_journal(withhold_type=withhold_type)
        wiz = self.env['l10n_ec.wizard.account.withhold'].with_context(
            active_model='account.move',
            active_ids=invoices.ids,
            default_journal_id=journal.id,
        ).create({
            'journal_id': journal.id,
            'document_number': document_number,
            'date': date_retention,
        })
        # remove any auto‑generated lines
        wiz.withhold_line_ids = [Command.clear()]
        commands = []
        for line in impuestos_invoice_lines:
            values = line[2]
            tax_id = values.get('tax_id')
            if not tax_id:
                continue
            inv = invoices[0]
            if values.get('invoice_multiple_id'):
                inv = values['invoice_multiple_id']
            base_amt = float(values.get('tax_base', 0.0))
            pct = float(values.get('retention_percentage', 0.0) or values.get('retention_percentage_manual', 0.0))
            amount = round(base_amt * (pct / 100.0), 2)
            commands.append(Command.create({
                'invoice_id': inv.id,
                'tax_id': tax_id,
                'base': base_amt,
                'amount': amount,
            }))
        wiz.withhold_line_ids = commands
        # create and post the retention
        withhold_move = wiz.action_create_and_post_withhold()
        # ------------------------------------------------------------------
        # En Odoo 17 el wizard de retenciones (l10n_ec.wizard.account.withhold)
        # permite especificar el número del documento mediante el campo
        # ``document_number``.  Sin embargo, una vez creado el asiento
        # contable de retención (account.move) el número puede no quedar
        # reflejado en el campo estándar ``l10n_latam_document_number`` que
        # utilizan los listados y vistas para identificar documentos.
        #
        # Para garantizar que la retención quede correctamente vinculada y
        # sea buscable por su número, se asigna explícitamente el número
        # formateado a ``l10n_latam_document_number`` en el asiento creado.
        # Además, se asigna la clave de autorización del SRI al campo
        # ``l10n_ec_authorization_number`` para que el registro pueda
        # localizarse en futuras importaciones y evitar duplicados.
        # ------------------------------------------------------------------
        # Usamos SQL directo para asignar l10n_ec_authorization_number y ref
        # en el asiento de retención recién creado.  El ORM write() sobre un
        # asiento posted dispara recomputaciones de campos de secuencia
        # (_compute_name, _constrains_date_sequence) que fallan porque la
        # secuencia fue emitida en un período anterior (ej. RVNTA/2026/02
        # cuando la fecha de importación es marzo 2026).  SQL directo evita
        # toda esa maquinaria de restricciones del ORM.
        ref_value = document_number

        sql_fields = {
            'l10n_ec_authorization_number': access_key,
            'ref': ref_value,
        }
        if invoices:
            sql_fields['l10n_ec_edi_related_invoice_id'] = invoices[0].id
        set_clause = ', '.join('%s=%%s' % k for k in sql_fields)
        self.env.cr.execute(
            'UPDATE account_move SET ' + set_clause + ' WHERE id=%s',
            list(sql_fields.values()) + [withhold_move.id],
        )
        # Invalidar la caché ORM para que lecturas posteriores lean de DB.
        withhold_move.invalidate_recordset(list(sql_fields.keys()))

        # ------------------------------------------------------------------
        # Controlar la conciliación automática de la retención.
        #
        # El wizard de retenciones (`l10n_ec.wizard.account.withhold`) en Odoo 17
        # reconcilia de forma automática las líneas de la retención con las
        # facturas que se le pasan como contexto.  Si «remove_reconcile» es
        # True se elimina dicha conciliación de modo que la retención quede
        # como crédito pendiente del cliente (comportamiento heredado de
        # Odoo 16).  Si es False, la conciliación se mantiene para reducir
        # automáticamente el saldo de la factura.
        if remove_reconcile:
            try:
                for line in withhold_move.line_ids:
                    partials = line.matched_debit_ids | line.matched_credit_ids
                    if partials:
                        partials.remove_move_reconcile()
            except Exception:
                # Si por alguna razón no podemos eliminar la conciliación
                # (por ejemplo, por permisos), no interrumpimos el flujo.
                pass

        return withhold_move

    # ------------------------------------------------------------------
    # Helpers for electronic authorization in Odoo 17+.
    #
    # In Odoo 17 the access key for electronic documents is stored in the
    # field ``l10n_ec_authorization_number`` on account.move.  Earlier
    # versions used ``electronic_authorization``.  These helpers detect
    # which field exists at runtime and provide unified search and write
    # semantics.  They allow the same codebase to work against Odoo 16
    # installations (with the legacy field) and Odoo 17 (with the new
    # localisation field).
    def _authorization_field(self):
        """Return the account.move field used to store the SRI access key.

        This method inspects the model definition of ``account.move`` to
        determine which field should be used to record the electronic
        authorisation key (also known as the SRI access key).  In
        localisation v17 this field is named ``l10n_ec_authorization_number``;
        older implementations used ``electronic_authorization``.  If neither
        field exists, ``None`` is returned and no search on access key will
        be performed.

        :return: A string representing the field name, or ``None`` if no
            suitable field is present.
        """
        fields_move = self.env['account.move']._fields
        if 'l10n_ec_authorization_number' in fields_move:
            return 'l10n_ec_authorization_number'
        if 'electronic_authorization' in fields_move:
            return 'electronic_authorization'
        return None

    def _search_move_by_auth(self, move_type: str, access_key: str):
        """Search ``account.move`` by move type and SRI access key.

        This helper builds a domain that matches the provided ``move_type``
        and filters on the appropriate access key field if it exists.  It
        returns a recordset of ``account.move`` matching the criteria.

        :param move_type: The type of move to filter on (e.g. 'in_invoice',
            'in_refund').
        :param access_key: The SRI access key to search for.
        :return: A recordset of ``account.move`` objects.
        """
        domain = [('move_type', '=', move_type)]
        field_name = self._authorization_field()
        if field_name and access_key:
            domain.append((field_name, '=', access_key))
        return self.env['account.move'].search(domain)

    def _find_retention_tax(self, codigo_impuesto: str, codigo_retencion: str,
                             prefer_type_tax_use: str = 'sale'):
        """Locate a retention tax using exact fields and tolerant fallbacks.

        Some bank/card retentions come with codes like ``323B1`` while the
        configured tax may be stored as ``323 2% ...`` and may even be
        archived. This helper searches archived taxes too and tries
        progressively looser matches.

        :param prefer_type_tax_use: When multiple taxes share the same SRI code
            (e.g. one purchase tax for in_withhold and one sale tax for
            out_withhold), prefer the one matching this type.  Default 'sale'
            so that out_withhold paths pick the tax with the crédito tributario
            asset account instead of the liability account used for purchases.
        """
        import re

        Tax = self.env['account.tax'].with_context(active_test=False)
        code = (codigo_retencion or '').strip().upper()
        if not code:
            return Tax.browse()

        tax = Tax.browse()
        if codigo_impuesto == '1':
            # Prefer the tax whose type_tax_use matches the withhold direction
            # (sale = out_withhold = crédito tributario asset account).
            # Also exclude zero-amount taxes (0% stub taxes used for other purposes).
            tax = Tax.search([
                ('l10n_ec_code_base', '=', code),
                ('type_tax_use', '=', prefer_type_tax_use),
                ('amount', '!=', 0),
            ], limit=1)
            if not tax:
                # Relax: accept zero-amount if that is all we have for this type
                tax = Tax.search([
                    ('l10n_ec_code_base', '=', code),
                    ('type_tax_use', '=', prefer_type_tax_use),
                ], limit=1)
            if not tax:
                # Last resort: any tax with this code regardless of type
                tax = Tax.search([('l10n_ec_code_base', '=', code)], limit=1)
        else:
            tax = Tax.search([
                ('l10n_ec_code_ats', '=', code),
                ('type_tax_use', '=', prefer_type_tax_use),
                ('amount', '!=', 0),
            ], limit=1)
            if not tax:
                tax = Tax.search([
                    ('l10n_ec_code_ats', '=', code),
                    ('type_tax_use', '=', prefer_type_tax_use),
                ], limit=1)
            if not tax:
                tax = Tax.search([('l10n_ec_code_ats', '=', code)], limit=1)
        if tax:
            return tax[:1]

        candidates = [code]
        m = re.match(r'^(\d+)', code)
        if m:
            candidates.append(m.group(1))
        digits_only = ''.join(ch for ch in code if ch.isdigit())
        if digits_only:
            candidates.append(digits_only)
            if len(digits_only) >= 3:
                candidates.append(digits_only[:3])

        seen = set()
        candidates = [c for c in candidates if c and not (c in seen or seen.add(c))]
        for cand in candidates:
            tax = Tax.search([
                '|', '|', '|',
                ('name', 'ilike', cand),
                ('description', 'ilike', cand),
                ('invoice_label', 'ilike', cand),
                ('name', '=ilike', f'{cand} %'),
            ], limit=1)
            if tax:
                return tax[:1]

        return Tax.browse()

    def import_retention(self, xml_data, type, type_import):
        results_retentions = {'no_invoice': []}
        new_retentions = 0
        new_retentions_credit_card = 0
        found_retentions = 0
        invoice_amount_residual = 0
        rt_id = False
        invoice = False
        invoices = []
        is_credit_card = False
        infoTributaria = xml_data.find("infoTributaria")
        infoCompRetencion = xml_data.find("infoCompRetencion")
        electronic_authorization = infoTributaria.find('claveAcceso').text
        l10n_latam_document_number = infoTributaria.find('estab').text + "-" + infoTributaria.find('ptoEmi').text + "-" + infoTributaria.find('secuencial').text
        # Buscar si hay retenciones ingresadas mediante l10n_ec_edi
        if self._withhold_exists(electronic_authorization, withhold_type='out_withhold'):
            if type_import == 'xml':
                raise UserError(_("La Retención ya se encuentra ingresada!!"))
            if type_import == 'txt':
                found_retentions += 1
        else:
            # Preparar contenedor para las líneas de impuestos de la retención
            impuestos_invoice_lines = []

            ruc = infoTributaria.find('ruc').text
            partner = self.env['res.partner'].search([('vat', '=', ruc)])
            if len(partner) == 0:
                # Crear proveedor con datos aleatorio
                name = infoTributaria.find('razonSocial').text
                l10n_latam_identification_type_id = self.env['l10n_latam.identification.type'].search([('name', '=', 'Ruc')])
                partner = self.env['res.partner'].create({'name': name,
                                                          'vat': ruc,
                                                          'l10n_latam_identification_type_id': l10n_latam_identification_type_id.id,
                                                          'email': self.env.company.partner_id.email})
                if type_import == 'xml':
                    result_str = "Se debe completar los datos del proveedor: %s" % name
                if type_import == 'txt':
                    results_retentions['no_invoice'].append('Se debe completar los datos del proveedor: %s' % name)
            else:
                partner = partner[0]
            if partner.is_bank_partner:
                is_credit_card = True

            if xml_data.attrib['version'] == '1.0.0':
                impuestos = xml_data.findall("impuestos")[0] if xml_data.findall("impuestos") else []
                
                #Verificar si es una retencion multiple
                for impuesto in impuestos:
                    # Obtener el número de factura sustentante y formatearlo en segmentos 3-3-resto.
                    # En la versión 16, el número de documento sustentante puede tener menos de 15 dígitos
                    # (por ejemplo, "26764852091"). En estos casos, Odoo lo interpreta como
                    # código de establecimiento, punto de emisión y secuencial, cada uno con longitud
                    # variable excepto los dos primeros que siempre ocupan 3 dígitos. Por ello, aquí
                    # removemos cualquier guion y separamos los tres primeros dígitos, los siguientes
                    # tres y el resto sin añadir ceros a la izquierda.
                    number_invoice_raw = (impuesto.find('numDocSustento').text or '').strip()
                    # Si el número ya contiene guiones, removerlos antes de procesar
                    number_invoice_raw = number_invoice_raw.replace('-', '')
                    # Comprobar que tiene al menos 7 caracteres para evitar errores de slicing
                    if len(number_invoice_raw) >= 7:
                        number_invoice = (
                            number_invoice_raw[:3] + "-" + number_invoice_raw[3:6] + "-" + number_invoice_raw[6:]
                        )
                    else:
                        number_invoice = number_invoice_raw  # fallback si el número es demasiado corto
                    if not is_credit_card:
                        # Buscar la factura solo si no es retención de tarjeta.  Evitar agregar recordsets vacíos
                        invoice = self.env['account.move'].search([
                            ('move_type', '=', 'out_invoice'),
                            ('l10n_latam_document_number', '=', number_invoice),
                        ])
                        # Añadir solo las facturas encontradas al listado de invoices
                        if invoice:
                            invoices.append(invoice)
                # Eliminar los recordsets vacíos de la lista de facturas.  Evitamos usar set() ya que
                # los recordsets de Odoo no son hashables y producirían un error.  Los duplicados
                # no afectan porque posteriormente construimos un recordset único a partir de sus ids.
                invoices = [inv for inv in invoices if inv]
                is_multiple_retention = False
                if len(invoices)>1:
                    is_multiple_retention = True

                for impuesto in impuestos:
                    # Formatear el número de factura sustentante (3-3-resto) para localizar la factura.
                    number_invoice_raw = (impuesto.find('numDocSustento').text or '').strip()
                    number_invoice_raw = number_invoice_raw.replace('-', '')
                    if len(number_invoice_raw) >= 7:
                        number_invoice = (
                            number_invoice_raw[:3] + "-" + number_invoice_raw[3:6] + "-" + number_invoice_raw[6:]
                        )
                    else:
                        number_invoice = number_invoice_raw
                    # Identificar si se trata de retención de tarjeta (número de factura "000-000-000000000")
                    if number_invoice == '000-000-000000000':
                        is_credit_card = True
                    if not is_credit_card:
                        invoice = self.env['account.move'].search([
                            ('move_type', '=', 'out_invoice'),
                            ('l10n_latam_document_number', '=', number_invoice),
                        ])
                        # Solo proceder si la factura existe
                        if invoice:
                            invoices.append(invoice)
                            if len(invoice) > 0:
                                # Crear línea de retención; para retención múltiple usar la factura en contexto
                                if is_multiple_retention:
                                    line_retention = self.create_line_retention(impuesto, is_credit_card, invoice[0])
                                else:
                                    line_retention = self.create_line_retention(impuesto, is_credit_card, None)
                                if line_retention:
                                    impuestos_invoice_lines.append(line_retention)
                                else:
                                    # Reportar cuando no se encuentra el código de retención
                                    if type_import == 'xml':
                                        raise UserError(
                                            _("El Código de Retención %s no se encuentra en el sistema!!" % impuesto.find('codigoRetencion').text)
                                        )
                                    if type_import == 'txt':
                                        results_retentions['no_invoice'].append(
                                            'El Código de Retención %s no se encuentra en el sistema' % impuesto.find('codigoRetencion').text
                                        )
                        else:
                            # Cuando la factura no existe, informar pero no agregar a invoices
                            if type_import == 'xml':
                                raise UserError(_("La Factura no se encuentra ingresada en el sistema!!"))
                            if type_import == 'txt':
                                text = 'La Factura %s no esta ingresada' % number_invoice
                                if text not in results_retentions['no_invoice']:
                                    results_retentions['no_invoice'].append(text)
                    else:
                        # Retención de tarjeta: crear línea de retención sin factura
                        impuestos_invoice_lines.append(self.create_line_retention(impuesto, is_credit_card, None))
                # Eliminar los recordsets vacíos de la lista de facturas (los duplicados
                # no afectan, ya que más adelante se utilizan los ids para construir
                # un recordset único)
                invoices = [inv for inv in invoices if inv]

            if xml_data.attrib['version'] == '2.0.0':
                docsSustentos = xml_data.findall("docsSustento")[0] if xml_data.findall("docsSustento") else []
                
                #Verificar si es una retencion multiple
                is_multiple_retention = False
                if len(docsSustentos) > 1:
                    is_multiple_retention = True

                for docsSustento in docsSustentos:
                    # Formatear el número de documento: quitar guiones y dividir en segmentos 3-3-resto.
                    number_invoice_raw = (docsSustento.find('numDocSustento').text or '').strip()
                    number_invoice_raw = number_invoice_raw.replace('-', '')
                    if len(number_invoice_raw) >= 7:
                        number_invoice = (
                            number_invoice_raw[:3] + "-" + number_invoice_raw[3:6] + "-" + number_invoice_raw[6:]
                        )
                    else:
                        number_invoice = number_invoice_raw
                    # Determinar si se trata de retención de tarjeta
                    if number_invoice == '000-000-000000000':
                        is_credit_card = True

                    # Inicializar la variable de factura para este documento de sustento
                    invoice_current = False
                    if not is_credit_card:
                        invoice_current = self.env['account.move'].search([
                            ('move_type', '=', 'out_invoice'),
                            ('l10n_latam_document_number', '=', number_invoice),
                        ])
                        if not invoice_current:
                            # Si no se encuentra la factura, registrar el mensaje pero no agregar a invoices
                            if type_import == 'xml':
                                raise UserError(_("La Factura no se encuentra ingresada en el sistema!!"))
                            if type_import == 'txt':
                                results_retentions['no_invoice'].append('La Factura %s no esta ingresada' % number_invoice)
                        else:
                            invoices.append(invoice_current)

                    impuestos = docsSustento.findall("retenciones")[0] if docsSustento.findall("retenciones") else []
                    for impuesto in impuestos:
                        # Utilizar la factura encontrada sólo si existe; de lo contrario enviar None
                        if is_multiple_retention and not is_credit_card and invoice_current:
                            line_retention = self.create_line_retention(impuesto, is_credit_card, invoice_current[0])
                        else:
                            line_retention = self.create_line_retention(impuesto, is_credit_card, None)
                        if not line_retention:
                            if type_import == 'xml':
                                raise UserError(
                                    _("El Código de Retención %s no se encuentra en el sistema!!" % impuesto.find('codigoRetencion').text)
                                )
                            if type_import == 'txt':
                                results_retentions['no_invoice'].append(
                                    'El Código de Retención %s no se encuentra en el sistema' % impuesto.find('codigoRetencion').text
                                )
                        else:
                            impuestos_invoice_lines.append(line_retention)

            if len(partner) > 0 and len(invoices) > 0:
                # Construir un recordset unificado de facturas desde la lista de recordsets
                invoice_ids = []
                for inv in invoices:
                    if inv:
                        invoice_ids.append(inv[0].id)
                invoices_rs = self.env['account.move'].browse(invoice_ids)

                # Asegurarse de que las autofacturas internas estén correctamente marcadas.
                # Si la factura tiene como partner a la misma compañía y no está marcada
                # como autofactura interna, activamos el flag para evitar el error de
                # validación del módulo account_internal_self_invoice.
                try:
                    for inv in invoices_rs:
                        # La validación se basa en la coincidencia entre partner y compañía
                        if inv.partner_id and inv.company_id and inv.partner_id.id == inv.company_id.partner_id.id:
                            if not getattr(inv, 'is_internal_self_invoice', False):
                                inv.write({'is_internal_self_invoice': True})
                except Exception:
                    # Si hay problemas al acceder o escribir el campo, lo ignoramos para no
                    # interrumpir la importación de la retención.  La validación se producirá
                    # únicamente en facturas donde el campo exista.
                    pass
                # Convertir la fecha de emisión a formato ISO
                date_retention = (infoCompRetencion.find('fechaEmision').text).split("/")
                date_retention = date_retention[2] + "-" + date_retention[1] + "-" + date_retention[0]
                # Antes de crear la retención, obtenemos el saldo pendiente
                # del primer documento en la lista.  Esto nos permitirá
                # decidir si la retención debe aplicarse automáticamente o
                # quedar como crédito.
                invoice_amount_residual = invoices_rs and invoices_rs[0].amount_residual or 0.0
                # Si el monto residual es mayor que cero, no remover la
                # conciliación para que el crédito se aplique de inmediato;
                # de lo contrario, se eliminarán las conciliaciones para
                # conservar el crédito como saldo a favor.
                remove_reconcile = False if invoice_amount_residual > 0.0 else True
                # Crear y aprobar la retención mediante el wizard oficial.
                withhold_move = self._create_withhold_l10n_ec(
                    invoices=invoices_rs,
                    document_number=l10n_latam_document_number,
                    access_key=electronic_authorization,
                    date_retention=date_retention,
                    impuestos_invoice_lines=impuestos_invoice_lines,
                    withhold_type='out_withhold',
                    remove_reconcile=remove_reconcile,
                    invoice_doc_number=locals().get('number_invoice', ''),
                )
                rt_id = withhold_move
                new_retentions += 1
            else:
                # Si no hay facturas asociadas y no es retención de tarjeta, intentamos asociar la retención
                # a las facturas abiertas del cliente.  En Odoo 17 las retenciones de cliente se aplican
                # mediante el wizard de retenciones sobre facturas de venta.  Sin embargo, cuando el
                # número de factura sustentante no coincide con ninguna factura en el sistema, buscamos
                # todas las facturas de venta no pagadas del cliente y, si existen, usamos esas facturas
                # como base para crear la retención.  De esta manera, la retención queda vinculada
                # al cliente y puede aplicarse manualmente a cualquiera de sus facturas.
                if len(partner) > 0 and not invoices and not is_credit_card:
                    # Buscar facturas de venta publicadas del cliente que no estén totalmente pagadas
                    open_invoices = self.env['account.move'].search([
                        ('move_type', '=', 'out_invoice'),
                        ('partner_id', '=', partner.id),
                        ('state', '=', 'posted'),
                        ('payment_state', '!=', 'paid'),
                    ])
                    # Determinar la fecha de emisión de la retención en formato ISO (YYYY-MM-DD)
                    date_retention_parts = (infoCompRetencion.find('fechaEmision').text).split('/')
                    date_retention = f"{date_retention_parts[2]}-{date_retention_parts[1]}-{date_retention_parts[0]}"
                    # Recopilar nodos de impuestos para crear las líneas de retención
                    impuesto_nodes = []
                    if xml_data.attrib.get('version') == '1.0.0':
                        impuestos_elem = xml_data.find('impuestos')
                        if impuestos_elem is not None:
                            impuesto_nodes.extend(impuestos_elem.findall('impuesto'))
                    elif xml_data.attrib.get('version') == '2.0.0':
                        docs_elem = xml_data.find('docsSustento')
                        if docs_elem is not None:
                            for doc in docs_elem.findall('docSustento'):
                                retenciones_elem = doc.find('retenciones')
                                if retenciones_elem is not None:
                                    impuesto_nodes.extend(retenciones_elem.findall('retencion'))
                    # Construir líneas de retención a partir de los impuestos, sin asociarlas a una
                    # factura específica (invoice_multiple_id=None).  Posteriormente el wizard
                    # asignará las líneas a la primera factura del conjunto, pero se eliminarán
                    # las conciliaciones automáticas para permitir su aplicación manual.
                    impuestos_invoice_lines = []
                    for imp in impuesto_nodes:
                        line_ret = self.create_line_retention(imp, is_credit_card, None)
                        if line_ret:
                            impuestos_invoice_lines.append(line_ret)
                        else:
                            # Si no se encuentra el código de retención, reportar y omitir
                            if type_import == 'xml':
                                raise UserError(_(
                                    "El Código de Retención %s no se encuentra en el sistema!!" % imp.find('codigoRetencion').text
                                ))
                            if type_import == 'txt':
                                results_retentions['no_invoice'].append(
                                    'El Código de Retención %s no se encuentra en el sistema' % imp.find('codigoRetencion').text
                                )
                    if open_invoices:
                        # Crear la retención vinculada a las facturas abiertas del cliente
                        withhold_move = self._create_withhold_l10n_ec(
                            invoices=open_invoices,
                            document_number=l10n_latam_document_number,
                            access_key=electronic_authorization,
                            date_retention=date_retention,
                            impuestos_invoice_lines=impuestos_invoice_lines,
                            withhold_type='out_withhold',
                            remove_reconcile=True,
                            invoice_doc_number=locals().get('number_invoice', ''),
                        )
                        rt_id = withhold_move
                        new_retentions += 1
                        # Preparar mensaje de retorno para XML o TXT
                        msg = _("Se cargó la retención de venta: %s vinculada a facturas pendientes del cliente" % l10n_latam_document_number)
                        if type_import == 'xml':
                            return msg
                        if type_import == 'txt':
                            results_retentions['no_invoice'].append(msg)
                            return results_retentions['no_invoice'], found_retentions, new_retentions, new_retentions_credit_card
                    else:
                        # Si no existen facturas abiertas, crear la retención como saldo a favor del cliente
                        withhold_move = self._create_unlinked_sale_withhold(
                            partner=partner,
                            document_number=l10n_latam_document_number,
                            access_key=electronic_authorization,
                            date_retention=date_retention,
                            impuesto_nodes=impuesto_nodes,
                            invoice_doc_number=locals().get('number_invoice', ''),
                        )
                        rt_id = withhold_move
                        new_retentions += 1
                        msg = _("Se cargó la retención de venta: %s como saldo a favor" % l10n_latam_document_number)
                        if type_import == 'xml':
                            return msg
                        if type_import == 'txt':
                            results_retentions['no_invoice'].append(msg)
                            return results_retentions['no_invoice'], found_retentions, new_retentions, new_retentions_credit_card
                # Si la retención es de tarjeta de crédito/banco, crear un asiento contable simple en lugar de vincular factura.
                if is_credit_card:
                    # Determinar la fecha de emisión de la retención en formato ISO (YYYY-MM-DD)
                    date_retention_parts = (infoCompRetencion.find('fechaEmision').text).split('/')
                    date_retention = f"{date_retention_parts[2]}-{date_retention_parts[1]}-{date_retention_parts[0]}"
                    # Reunir los nodos de impuestos para calcular los montos retenidos.  Dependiendo de la versión
                    # del XML, los impuestos se encuentran en etiquetas distintas.
                    impuesto_nodes = []
                    if xml_data.attrib.get('version') == '1.0.0':
                        impuestos_elem = xml_data.find('impuestos')
                        if impuestos_elem is not None:
                            impuesto_nodes.extend(impuestos_elem.findall('impuesto'))
                    elif xml_data.attrib.get('version') == '2.0.0':
                        docs_elem = xml_data.find('docsSustento')
                        if docs_elem is not None:
                            for doc in docs_elem.findall('docSustento'):
                                retenciones_elem = doc.find('retenciones')
                                if retenciones_elem is not None:
                                    impuesto_nodes.extend(retenciones_elem.findall('retencion'))
                    # Crear la retención tipo tarjeta de crédito.  Esta función creará y publicará un asiento
                    # contable en el diario de retenciones de ventas (o el disponible) sin asociar la retención a una factura.
                    withhold_move = self._create_credit_card_withhold(
                        partner=partner,
                        document_number=l10n_latam_document_number,
                        access_key=electronic_authorization,
                        date_retention=date_retention,
                        impuesto_nodes=impuesto_nodes,
                    )
                    rt_id = withhold_move
                    # Preparar el mensaje de retorno según el tipo de importación
                    if type_import == 'xml':
                        result_str = _("Se cargó la retención de tarjeta de crédito: %s") % l10n_latam_document_number
                        return result_str
                    if type_import == 'txt':
                        results_retentions['no_invoice'].append(
                            _("Se cargó la retención de tarjeta de crédito: %s") % l10n_latam_document_number
                        )
                        return results_retentions['no_invoice'], found_retentions, new_retentions, 0
                    return
            # Fin de tarjeta de crédito
        if type_import == 'xml':
            # Comparar contra el importe total de la retención.  El campo
            # ``amount_total`` en account.move refleja el valor retenido.
            if rt_id and invoice_amount_residual < rt_id.amount_total:
                result_str = "Se cargo la retención de venta: %s como saldo a Favor" % l10n_latam_document_number
            else:
                result_str = "Se cargo la retención de venta: %s" % l10n_latam_document_number
            return result_str
        if type_import == 'txt':
            if rt_id and invoice_amount_residual < rt_id.amount_total:
                results_retentions['no_invoice'].append('Se cargo la retención de venta: %s como saldo a Favor' % l10n_latam_document_number)
            return results_retentions['no_invoice'],found_retentions,new_retentions, new_retentions_credit_card
        return

    # ------------------------------------------------------------------
    # Credit Card / Bank Withhold Creation
    #
    # Las retenciones de tarjeta de crédito o de bancos no se asocian a
    # ninguna factura en Odoo.  Este método genera un movimiento de
    # contabilidad ('account.move') tipo 'out_withhold' con líneas que
    # reflejan el monto retenido por cada impuesto y un contrapartida en
    # la cuenta predeterminada del diario.  El diario se elige entre los
    # disponibles para retenciones de ventas (``l10n_ec_withhold_type`` =
    # 'out_withhold') de tipo 'cash' o 'bank'.
    #
    # :param partner: Record de ``res.partner`` correspondiente al banco
    #                 emisor de la retención.
    # :param document_number: Número de documento formateado (ej. 001-001-000000123).
    # :param access_key: Clave de acceso del SRI (autorización electrónica).
    # :param date_retention: Fecha de emisión (YYYY-MM-DD) de la retención.
    # :param impuesto_nodes: Lista de nodos XML ``retencion`` con los datos
    #                        de base, porcentaje y valor retenido.
    # :return: Movimiento contable creado (account.move).
    def _create_credit_card_withhold(self, partner, document_number, access_key, date_retention, impuesto_nodes):
        # Buscar un diario adecuado para retenciones bancarias/tarjetas.
        # En la práctica conviene priorizar diarios específicos de tarjetas
        # de crédito del cliente antes que diarios genéricos de retenciones,
        # porque estos suelen tener la cuenta predeterminada configurada.
        Journal = self.env['account.journal']
        company = self.env.company

        def _pick_journal_with_account(recordset):
            for j in recordset:
                if j.default_account_id:
                    return j
            return recordset[:1]

        # 1) Priorizar diarios explícitos de tarjeta / clientes
        preferred = Journal.search([
            ('company_id', '=', company.id),
            '|', '|', '|', '|',
            ('code', 'in', ['TJCRE', 'TjCre', 'TJCREC', 'TJC', 'DRV']),
            ('name', 'ilike', 'TARJETAS DE CREDITO CLIENTE'),
            ('name', 'ilike', 'TARJETAS DE CREDITO'),
            ('name', 'ilike', 'tarjeta'),
            ('name', 'ilike', 'credito cliente'),
        ])
        journal = _pick_journal_with_account(preferred)

        # 2) Luego diarios de retención de venta que sí tengan cuenta
        if not journal:
            candidates = Journal.search([
                ('company_id', '=', company.id),
                ('l10n_ec_withhold_type', '=', 'out_withhold'),
                ('type', 'in', ['cash', 'bank', 'general']),
            ])
            journal = _pick_journal_with_account(candidates)

        # 3) Luego cualquier diario de retención de venta
        if not journal:
            candidates = Journal.search([
                ('company_id', '=', company.id),
                ('l10n_ec_withhold_type', '=', 'out_withhold'),
            ])
            journal = _pick_journal_with_account(candidates)

        # 4) Finalmente cualquier diario utilizable con cuenta por defecto
        if not journal:
            candidates = Journal.search([
                ('company_id', '=', company.id),
                ('type', 'in', ['cash', 'bank', 'general']),
            ])
            journal = _pick_journal_with_account(candidates)

        if not journal:
            raise UserError(_(
                "No se encontró un diario utilizable para retenciones bancarias/tarjetas. Configure un diario como 'TARJETAS DE CREDITO CLIENTE' o uno de retenciones de ventas."
            ))

        # Construir las líneas contables.  Para cada impuesto calculamos el importe retenido
        # según el valor indicado en el XML (``valorRetenido``) o bien base * porcentaje.
        line_vals = []
        total_amount = 0.0
        taxes_not_found = []
        # Para cada nodo de retención, obtenemos el impuesto en Odoo
        for impuesto in impuesto_nodes:
            # Código del impuesto: '1' para impuesto a la renta, otro valor para IVA u otros
            codigo_impuesto = impuesto.find('codigo')
            codigo_retencion = impuesto.find('codigoRetencion')
            base_text = impuesto.find('baseImponible')
            porcentaje_text = impuesto.find('porcentajeRetener')
            valor_text = impuesto.find('valorRetenido')
            if codigo_impuesto is None or codigo_retencion is None or base_text is None or porcentaje_text is None:
                continue
            try:
                base = float(base_text.text)
            except Exception:
                base = 0.0
            try:
                porcentaje = float(porcentaje_text.text)
            except Exception:
                porcentaje = 0.0
            try:
                valor = float(valor_text.text) if (valor_text is not None and valor_text.text) else 0.0
            except Exception:
                valor = 0.0
            # Obtener el impuesto de la base de datos; utilizamos los mismos criterios que
            # ``create_line_retention``: l10n_ec_code_base para impuestos de renta (codigo = '1')
            # y l10n_ec_code_ats para IVA
            Tax = self.env['account.tax']
            tax_id = False
            if codigo_impuesto.text == '1':
                tax_id = self._find_retention_tax(codigo_impuesto.text, codigo_retencion.text)
            else:
                tax_id = self._find_retention_tax(codigo_impuesto.text, codigo_retencion.text)
            if not tax_id:
                taxes_not_found.append(codigo_retencion.text)
                continue
            tax = tax_id[0]
            # Calcular el valor retenido si no viene indicado
            if valor == 0.0:
                valor = base * porcentaje / 100.0
            # Buscar la cuenta contable para la retención de tarjeta/banco.
            # Para retenciones recibidas (out_withhold), la RTE FTE idealmente debe ir a
            # una cuenta de activo (crédito tributario).  Si la config del impuesto solo
            # tiene cuentas de pasivo, se acepta como último recurso para no bloquear el import.
            account_id = False
            fallback_liability_id = False
            for repart in tax.invoice_repartition_line_ids:
                if repart.account_id:
                    acc = self.env['account.account'].browse(repart.account_id.id)
                    if acc.account_type not in ('liability_payable', 'liability_current'):
                        account_id = repart.account_id.id
                        break
                    elif not fallback_liability_id:
                        fallback_liability_id = repart.account_id.id
            if not account_id:
                for repart in tax.refund_repartition_line_ids:
                    if repart.account_id:
                        acc = self.env['account.account'].browse(repart.account_id.id)
                        if acc.account_type not in ('liability_payable', 'liability_current'):
                            account_id = repart.account_id.id
                            break
                        elif not fallback_liability_id:
                            fallback_liability_id = repart.account_id.id
            if not account_id and journal.default_account_id:
                account_id = journal.default_account_id.id
            if not account_id:
                account_id = fallback_liability_id
            if not account_id:
                raise UserError(_(
                    "No se encontró una cuenta contable de activo para el impuesto de retención %s "
                    "ni una cuenta predeterminada en el diario %s. "
                    "Verifique que el impuesto tenga configurada la cuenta de crédito tributario."
                ) % (codigo_retencion.text, journal.display_name))
            # Generar línea debitando el importe retenido en la cuenta del impuesto
            line_vals.append((0, 0, {
                'name': _('Retención %s') % (tax.name or codigo_retencion.text),
                'account_id': account_id,
                'debit': valor,
                'credit': 0.0,
                'partner_id': partner.id,
            }))
            total_amount += valor

        # Si no se encontró ningún impuesto válido, detener con un mensaje
        if not line_vals:
            raise UserError(_(
                "No se encontró ningún impuesto válido para crear la retención de tarjeta de crédito."
            ))

        # Añadir la contrapartida acreditando el total retenido.
        # Se prioriza la cuenta por defecto del diario (cuenta transitoria de tarjetas).
        # Si no está configurada en el diario, se usa la cuenta por cobrar del partner.
        if journal.default_account_id:
            credit_account_id = journal.default_account_id.id
        else:
            credit_account_id = partner.with_company(company).property_account_receivable_id.id
            if not credit_account_id:
                raise UserError(_(
                    "El partner %s no tiene configurada una cuenta por cobrar." % partner.display_name
                ))
        line_vals.append((0, 0, {
            'name': _('Retenciones de tarjeta de crédito %s') % document_number,
            'account_id': credit_account_id,
            'debit': 0.0,
            'credit': total_amount,
            'partner_id': partner.id,
        }))

        # Valores de cabecera del movimiento de retención
        move_vals = {
            'move_type': 'entry',
            'journal_id': journal.id,
            'date': date_retention,
            'l10n_ec_withhold_date': date_retention,
            'l10n_latam_document_number': document_number,
            'ref': document_number,
            'invoice_date': date_retention,
            'partner_id': partner.id,
            'line_ids': line_vals,
        }
        auth_field = self._authorization_field()
        if auth_field:
            move_vals[auth_field] = access_key
        # Crear y publicar el asiento contable
        withhold_move = self.env['account.move'].create(move_vals)
        withhold_move.action_post()
        return withhold_move

    # ------------------------------------------------------------------
    # Unlinked Sale Withhold Creation
    #
    # Cuando una retención de cliente (venta) no puede vincularse a una factura
    # concreta (por ejemplo, porque la factura aún no está cargada en Odoo),
    # es deseable registrar igualmente la retención como un saldo a favor del
    # cliente.  En la versión 16 del módulo se presentaban dichas retenciones
    # para que el usuario las aplicara manualmente a cualquier factura.
    # Este método genera un movimiento contable ('account.move') de tipo
    # 'out_withhold' con líneas que reflejan el importe retenido por cada
    # impuesto y una contrapartida en la cuenta de clientes (cuenta por cobrar)
    # del partner.  De esta manera, la retención queda registrada como un
    # crédito disponible para el cliente sin asociarse a ninguna factura.
    #
    # :param partner: Record de ``res.partner`` correspondiente al cliente.
    # :param document_number: Número de documento formateado (ej. 001-001-000000123).
    # :param access_key: Clave de acceso del SRI (autorización electrónica).
    # :param date_retention: Fecha de emisión (YYYY-MM-DD) de la retención.
    # :param impuesto_nodes: Lista de nodos XML ``impuesto`` o ``retencion`` con los
    #                        datos de base, porcentaje y valor retenido.
    # :return: Movimiento contable creado (account.move).
    def _create_unlinked_sale_withhold(self, partner, document_number, access_key, date_retention, impuesto_nodes, invoice_doc_number=''):
        Journal = self.env['account.journal']
        company = self.env.company
        # Buscar un diario de retenciones de ventas configurado para la compañía
        journal = Journal.search([
            ('l10n_ec_withhold_type', '=', 'out_withhold'),
            ('company_id', '=', company.id)
        ], limit=1)
        if not journal:
            raise UserError(_(
                "No se encontró un diario configurado para retenciones de ventas."
            ))

        # Construir las líneas de la retención.  Para cada impuesto calculamos
        # el valor retenido (valorRetenido o baseImponible * porcentajeRetener).
        line_vals = []
        total_amount = 0.0
        taxes_not_found = []
        for impuesto in impuesto_nodes:
            codigo_impuesto = impuesto.find('codigo')
            codigo_retencion = impuesto.find('codigoRetencion')
            base_text = impuesto.find('baseImponible')
            porcentaje_text = impuesto.find('porcentajeRetener')
            valor_text = impuesto.find('valorRetenido')
            # Saltar nodos incompletos
            if codigo_impuesto is None or codigo_retencion is None or base_text is None or porcentaje_text is None:
                continue
            try:
                base = float(base_text.text)
            except Exception:
                base = 0.0
            try:
                porcentaje = float(porcentaje_text.text)
            except Exception:
                porcentaje = 0.0
            try:
                valor = float(valor_text.text) if (valor_text is not None and valor_text.text) else 0.0
            except Exception:
                valor = 0.0
            # Buscar el impuesto correspondiente en Odoo
            Tax = self.env['account.tax']
            tax_id = False
            if codigo_impuesto.text == '1':
                tax_id = self._find_retention_tax(codigo_impuesto.text, codigo_retencion.text)
            else:
                tax_id = self._find_retention_tax(codigo_impuesto.text, codigo_retencion.text)
            if not tax_id:
                taxes_not_found.append(codigo_retencion.text)
                continue
            tax = tax_id[0]
            # Calcular el valor retenido si no viene proporcionado
            if valor == 0.0:
                valor = base * porcentaje / 100.0
            # Obtener la cuenta contable para la retención de venta (out_withhold).
            # Para retenciones RECIBIDAS de clientes, la RTE FTE idealmente debe ir a
            # una cuenta de ACTIVO (crédito tributario).  Sin embargo, si la configuración
            # de impuestos solo tiene cuentas de pasivo, se acepta como último recurso para
            # evitar que el import falle (el usuario deberá corregir la config del impuesto).
            account_id = False
            fallback_liability_id = False
            for repart in tax.invoice_repartition_line_ids:
                if repart.account_id:
                    acc = self.env['account.account'].browse(repart.account_id.id)
                    if acc.account_type not in ('liability_payable', 'liability_current'):
                        account_id = repart.account_id.id
                        break
                    elif not fallback_liability_id:
                        fallback_liability_id = repart.account_id.id
            if not account_id:
                for repart in tax.refund_repartition_line_ids:
                    if repart.account_id:
                        acc = self.env['account.account'].browse(repart.account_id.id)
                        if acc.account_type not in ('liability_payable', 'liability_current'):
                            account_id = repart.account_id.id
                            break
                        elif not fallback_liability_id:
                            fallback_liability_id = repart.account_id.id
            if not account_id and journal.default_account_id:
                account_id = journal.default_account_id.id
            if not account_id:
                account_id = fallback_liability_id
            if not account_id:
                raise UserError(_(
                    "No se encontró ninguna cuenta contable para el impuesto de retención %s "
                    "ni una cuenta predeterminada en el diario %s. "
                    "Verifique la configuración del impuesto en Odoo."
                ) % (codigo_retencion.text, journal.display_name))
            # Crear línea debitando el importe retenido en la cuenta del impuesto (activo)
            line_vals.append((0, 0, {
                'name': _('Retención %s') % (tax.name or codigo_retencion.text),
                'account_id': account_id,
                'debit': valor,
                'credit': 0.0,
                'partner_id': partner.id,
            }))
            total_amount += valor

        if not line_vals:
            raise UserError(_(
                "No se encontró ningún impuesto válido para crear la retención de venta."
            ))
        # Línea de contrapartida acreditando el total en la cuenta por cobrar del cliente.
        # Así la retención queda como crédito pendiente aplicable a sus facturas.
        receivable_account_id = partner.with_company(company).property_account_receivable_id.id
        if not receivable_account_id:
            raise UserError(_(
                "El cliente %s no tiene una cuenta por cobrar configurada."
            ) % partner.display_name)
        line_vals.append((0, 0, {
            'name': _('Retención %s') % document_number,
            'account_id': receivable_account_id,
            'debit': 0.0,
            'credit': total_amount,
            'partner_id': partner.id,
        }))
        ref_value = document_number
        # Valores del encabezado del movimiento
        move_vals = {
            'move_type': 'entry',
            'journal_id': journal.id,
            'date': date_retention,
            'invoice_date': date_retention,
            'l10n_ec_withhold_date': date_retention,
            'l10n_latam_document_number': document_number,
            'ref': ref_value,
            'partner_id': partner.id,
            'line_ids': line_vals,
        }
        # Asignar clave de autorización
        auth_field = self._authorization_field()
        if auth_field:
            move_vals[auth_field] = access_key
        # Marcar como autofactura interna si corresponde
        try:
            if (
                'is_internal_self_invoice' in self.env['account.move']._fields and
                partner and company.partner_id and partner.id == company.partner_id.id
            ):
                move_vals['is_internal_self_invoice'] = True
        except Exception:
            pass
        withhold_move = self.env['account.move'].create(move_vals)
        withhold_move.action_post()
        return withhold_move

    def import_file_txt(self):
        has_invoice = False
        has_retention = False
        has_credit_note = False
        new_invoices = 0
        new_retentions = 0
        new_retentions_credit_card = 0
        new_credit_notes = 0
        found_invoices = 0
        found_retentions = 0
        found_credit_notes = 0
        no_invoice_credit_note = 0
        results_invoices = {'exists_invoices': [], 'no_partner': []}
        results_retentions = {'no_invoice': []}
        results_credit_note = {'no_exists_invoice_credit_note': [], 'exists_credit_note': []}
        # ------------------------------------------------------------------
        # Inicializar el cliente SOAP del SRI
        #
        # El servicio de autorización de comprobantes electrónicos del SRI
        # (AutorizacionComprobantesOffline) puede encontrarse en distintos
        # dominios dependiendo de la infraestructura del SRI.  Además, la
        # librería ``suds`` no viene instalada por defecto en las
        # distribuciones modernas de Python/Odoo.  Si ``suds`` está
        # ausente, el import inicial en la cabecera de este módulo crea
        # una clase ficticia que lanza un ``UserError`` con un mensaje de
        # ayuda.  A fin de diferenciar un problema de red de la ausencia
        # de dependencias, intentamos conectar a dos endpoints diferentes y
        # examinamos el mensaje de error.  Si ambos fallan, evaluamos
        # si se trata de una falta de la librería SOAP; de lo contrario
        # indicamos que no se pudo establecer conexión con el SRI.  Esta
        # lógica proporciona al usuario una retroalimentación más clara
        # sobre la causa del fallo.
        primary_wsdl = "https://cel.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline?wsdl"
        secondary_wsdl = "https://celcer.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline?wsdl"
        timeout = 120
        client_ws_auth = None
        last_exception = None
        for wsdl_url in (primary_wsdl, secondary_wsdl):
            try:
                client_ws_auth = Client(wsdl_url)
                client_ws_auth.set_options(timeout=timeout)
                # Si la inicialización se completa, salimos del bucle
                break
            except Exception as exc:
                # Guardamos la última excepción para diagnosticar después
                last_exception = exc
                client_ws_auth = None
                continue
        if client_ws_auth is None:
            # Si no se pudo inicializar el cliente SOAP, analizamos la causa.
            err_msg = str(last_exception) if last_exception else ""
            # Cuando la librería suds no está instalada, el stub definido
            # más arriba genera un UserError con un mensaje específico.  Al
            # propagarse hasta aquí, ese UserError queda encapsulado como
            # excepción genérica con el texto del mensaje original.  Si
            # detectamos esa situación, informamos al usuario cómo
            # instalar la dependencia faltante.
            if 'suds' in err_msg.lower():
                raise UserError(_(
                    "La librería de cliente SOAP 'suds-py3' no está instalada. "
                    "Instale el paquete 'suds-py3' (por ejemplo, con pip) para "
                    "utilizar las funcionalidades de descarga de comprobantes "
                    "electrónicos del SRI."
                ))
            # De igual forma, si la biblioteca de OpenSSL u otras
            # dependencias faltan, delegamos a sus mensajes de ayuda.
            if err_msg:
                raise UserError(_(
                    "No se pudo conectar al servicio de autorización del SRI. "
                    "Detalle del error: %s" % err_msg
                ))
            # En última instancia informamos que el servidor podría estar
            # fuera de línea o inaccesible.
            raise UserError(_(u'El Servidor del SRI está fuera de línea o no es accesible actualmente.'))
        self.ensure_one()
        datas = base64.b64decode(self.data_file or b"").decode("latin1", errors="ignore").splitlines()
        list_invoices = []
        list_retentions = []
        list_credit_notes = []
        for data in datas:
            line = data.split('\t')
            # Formato Tipo 1: line[0] = tipo de documento, line[9] = clave de acceso.
            # Guard de longitud para evitar IndexError ("índice fuera de rango") cuando
            # la línea tiene menos de 10 columnas (líneas de encabezado, vacías o malformadas).
            if line[0] == 'Factura' and len(line) > 9:
                list_invoices.append(line[9])
            elif line[0] == 'Comprobante de Retención' and len(line) > 9:
                list_retentions.append(line[9])
            elif line[0] == 'Notas de Crédito' and len(line) > 9:
                list_credit_notes.append(line[9])

        if len(list_invoices)==0:
            for data in datas:
                line = data.split('\t')
                # Formato Tipo 2 (Recibidos SRI): line[2] = tipo, line[4] = clave de acceso.
                # Guard len > 4 para evitar IndexError en líneas cortas o malformadas.
                if len(line) > 4:
                    if line[2] == 'Factura':
                        list_invoices.append(line[4])

        if len(list_retentions)==0:
            for data in datas:
                line = data.split('\t')
                if len(line) > 4:
                    if line[2] == 'Comprobante de Retención':
                        list_retentions.append(line[4])

        if len(list_credit_notes)==0:
            for data in datas:
                line = data.split('\t')
                if len(line) > 4:
                    if line[2] == 'Notas de Crédito':
                        list_credit_notes.append(line[4])


        for auth_invoice in list_invoices:
            has_invoice = True
            responseAuth = client_ws_auth.service.autorizacionComprobante(claveAccesoComprobante=auth_invoice)
            if len(responseAuth['autorizaciones']) > 0:
                if responseAuth['autorizaciones']['autorizacion'][0]['estado'] == 'AUTORIZADO':
                    # DATOS INICIALES
                    xml_string = responseAuth['autorizaciones']['autorizacion'][0]['comprobante']
                    xml_data = etree.fromstring(bytes(xml_string, encoding='utf-8'))
                    infoTributaria = xml_data.findall("infoTributaria")[0]
                    infoFactura = xml_data.findall("infoFactura")[0]
                    detalles = xml_data.findall("detalles")[0]
                    electronic_authorization = infoTributaria.find('claveAcceso').text
                    l10n_latam_document_number = infoTributaria.find('estab').text + "-" + infoTributaria.find(
                        'ptoEmi').text + "-" + infoTributaria.find('secuencial').text

                    # Buscar si hay facturas ingresadas utilizando el campo de autorización correcto
                    exists_invoices = self._search_move_by_auth('in_invoice', electronic_authorization)
                    if len(exists_invoices) > 0:
                        found_invoices = found_invoices + 1
                        continue

                    # Buscar si no existe el Proveedor
                    ruc = infoTributaria.find('ruc').text
                    razon_social = infoTributaria.find('razonSocial').text
                    partner_invoice = self.env['res.partner'].search([('vat', '=', ruc)])
                    if len(partner_invoice) == 0:
                        results_invoices['no_partner'].append('El proveedor %s con Ruc: %s no esta creado en el sistema' % (razon_social, ruc))
                        continue
                    if len(partner_invoice) != 0:
                        invoice_date = (infoFactura.find('fechaEmision').text).split("/")
                        invoice_date = invoice_date[2] + "-" + invoice_date[1] + "-" + invoice_date[0]
                        # Build the invoice values.  Assign the SRI access key to the
                        # appropriate field on account.move depending on the
                        # localisation installed (Odoo 17 uses
                        # ``l10n_ec_authorization_number`` instead of
                        # ``electronic_authorization``).
                        vals = {
                            'partner_id': partner_invoice[0].id,
                            'invoice_date': invoice_date,
                            'l10n_latam_document_number': (
                                infoTributaria.find('estab').text + '-' +
                                infoTributaria.find('ptoEmi').text + '-' +
                                infoTributaria.find('secuencial').text
                            ),
                            'move_type': 'in_invoice',
                        }
                        # Si el proveedor es la misma compañía (autofactura interna),
                        # activar la casilla correspondiente para evitar la validación
                        # ``Internal Self-Invoice" del módulo account_internal_self_invoice.
                        try:
                            company_partner = self.env.company.partner_id
                            if partner_invoice and partner_invoice[0].id == company_partner.id:
                                vals['is_internal_self_invoice'] = True
                        except Exception:
                            # Si no se puede determinar la compañía, omitir la asignación
                            pass
                        auth_field = self._authorization_field()
                        if auth_field:
                            vals[auth_field] = infoTributaria.find('claveAcceso').text
                        invoice = self.env['account.move'].create(vals)

                        lines = []
                        for detalle in detalles:
                            impuestos = detalle.find('impuestos')
                            tax_ids = []
                            # import pdb
                            # pdb.set_trace()
                            for tax in impuestos.findall("impuesto"):
                                code_tax = tax.find('codigo').text
                                if code_tax == '0':
                                    tax_id = self.env['account.tax'].search(
                                        [('l10n_ec_code_base', '=', '515'), ('type_tax_use', '=', 'purchase')])
                                if code_tax == '2':
                                    tax_id = self.env['account.tax'].search(
                                        [('l10n_ec_code_base', '=', '510'), ('type_tax_use', '=', 'purchase')])
                                if code_tax == '4':
                                    tax_id = self.env['account.tax'].search(
                                        [('l10n_ec_code_base', '=', '510'),
                                         ('amount', '=', float(tax.find('tarifa').text)),
                                         ('type_tax_use', '=', 'purchase')])

                                if tax_id:
                                    for tax_id_ in tax_id:
                                        tax_ids.append(tax_id_.id)

                            quantity = float(detalle.find('cantidad').text)
                            price_unit = float(detalle.find('precioUnitario').text)
                            descuento = float(detalle.find('descuento').text)
                            if descuento == 0:
                                discount = 0.00
                            else:
                                discount = round(((descuento * 100) / (quantity * price_unit)), 2)

                            product = []
                            if detalle.find('codigoPrincipal') != None:
                                product = self.env['product.product'].search(
                                    [('default_code', '=', detalle.find('codigoPrincipal').text)])

                            lines.append((0, 0, {'name': detalle.find('descripcion').text if detalle.find('descripcion') != None else detalle.find('codigoPrincipal').text,
                                                 'product_id': product[0].id if len(product) > 0 else False,
                                                 'account_id': invoice.journal_id.default_account_id.id,
                                                 'quantity': detalle.find('cantidad').text,
                                                 'price_unit': detalle.find('precioUnitario').text,
                                                 'tax_ids': [(6, 0, tax_ids)] if len(tax_ids) > 0 else False,
                                                 'discount': discount, }))

                        invoice.write({'invoice_line_ids': lines})
                        # invoice.button_reset_taxes()
                        new_invoices = new_invoices + 1
                    else:
                        continue

        processed_invoices = []
        missing_invoices = set()
        total_processed = []
        duplicated_keys = []
        unauthorized_keys = []
        failed_keys = []
        missing_invoice = []
        missing_invoice_retentions = {}
        out_range_retentions = []

        for auth_retention in list_retentions:
            has_retention = True

            # Verificar si la retención ya está ingresada en el sistema mediante l10n_ec_edi
            if self._withhold_exists(auth_retention, withhold_type='out_withhold'):
                _logger.info("La retención con clave %s ya está registrada en el sistema.", auth_retention)
                duplicated_keys.append(auth_retention)
                found_retentions = found_retentions + 1
                continue

            try:
                date_str = auth_retention[:8]  # Extraer fecha desde los primeros 8 dígitos
                date_emision = datetime.strptime(date_str, "%d%m%Y")
                if date_emision < datetime.now() - timedelta(days=33):
                    out_range_retentions.append({
                        "clave": auth_retention,
                        "fecha_emision": date_emision.strftime("%d/%m/%Y"),
                        "dias_atraso": (datetime.now() - date_emision).days
                    })
                    _logger.warning("La retención con clave %s tiene más de 33 días de antigüedad y será ignorada.", auth_retention)
                    continue

                # Realizar la llamada al servicio de autorización del comprobante
                responseAuth = client_ws_auth.service.autorizacionComprobante(claveAccesoComprobante=auth_retention)
                if len(responseAuth['autorizaciones']) > 0:
                    if responseAuth['autorizaciones']['autorizacion'][0]['estado'] == 'AUTORIZADO':
                        # Procesar el XML
                        xml_string = responseAuth['autorizaciones']['autorizacion'][0]['comprobante']#.strip()
                        xml_data = etree.fromstring(bytes(xml_string, encoding='utf-8'))
                        _logger.debug("XML de retención procesado: %s", etree.tostring(xml_data, pretty_print=True).decode('utf-8'))
                        
                        electronic_authorization = xml_data.find("infoTributaria/claveAcceso").text
                        
                        # Procesar la retención
                        formatted_invoice_number = f"{xml_data.find('infoTributaria/estab').text}-{xml_data.find('infoTributaria/ptoEmi').text}-{xml_data.find('infoTributaria/secuencial').text}"
                        _logger.info(f"Procesando retención {auth_retention} asociada a {formatted_invoice_number}")

                        import_results_retentions, import_found_retentions, import_new_retentions, import_new_retentions_credit_card \
                            = self.import_retention(xml_data, self.type, 'txt')

                        results_retentions['no_invoice'] += import_results_retentions
                        found_retentions += import_found_retentions
                        new_retentions += import_new_retentions
                        new_retentions_credit_card += import_new_retentions_credit_card
                        if import_new_retentions or import_new_retentions_credit_card:
                            total_processed.append((auth_retention, formatted_invoice_number))

                        # if exists_invoice:
                        #     total_processed.append((auth_retention, formatted_invoice_number))
                        # elif (auth_retention, formatted_invoice_number) not in missing_invoice:
                        #     missing_invoice.append((auth_retention, formatted_invoice_number))

                        # else:
                        #     if 'Factura desconocida' not in missing_invoice_retentions:
                        #         missing_invoice_retentions['Factura desconocida'] = []

                        #     missing_invoice_retentions['Factura desconocida'].append(auth_retention)

                        #     _logger.error("Nodo 'numDocSustento' no encontrado o vacío en la retención: %s", auth_retention)
                        #     failed_keys.append(auth_retention)
                    else:
                        _logger.error("Clave NO autorizada en SRI: %s", auth_retention)
                        unauthorized_keys.append(auth_retention)
                        results_retentions['no_invoice'].append('Retención no autorizada en SRI: %s. Para cargarla, importe el XML autorizado.' % auth_retention)
                else:
                    _logger.error("Error clave no autorizada en SRI: %s", auth_retention)
                    unauthorized_keys.append(auth_retention)
                    results_retentions['no_invoice'].append('Retención no autorizada o no encontrada en SRI: %s. Para cargarla, importe el XML autorizado.' % auth_retention)
                    _logger.error("Clave no autorizada o no encontrada en SRI: %s", auth_retention)
            except ConnectionResetError as cre:
                failed_keys.append(auth_retention)
                _logger.error("Error de conexión al procesar retención %s: %s", auth_retention, str(cre))
            except Exception as e:
                failed_keys.append(auth_retention)
                _logger.error("Error general al procesar retención %s: %s", auth_retention, str(e))
        _logger.info("Resumen del procesamiento:")
        _logger.info("Total claves procesadas: %d", len(total_processed))
        _logger.info("Total duplicadas: %d", len(duplicated_keys))
        _logger.info("Total no autorizadas: %d", len(unauthorized_keys))
        _logger.info("Total fallidas: %d", len(failed_keys))
        
        for auth_credit_note in list_credit_notes:
            has_credit_note = True
            responseAuth = client_ws_auth.service.autorizacionComprobante(claveAccesoComprobante=auth_credit_note)
            if len(responseAuth['autorizaciones']) > 0:
                if responseAuth['autorizaciones']['autorizacion'][0]['estado'] == 'AUTORIZADO':
                    # DATOS INICIALES
                    xml_string = responseAuth['autorizaciones']['autorizacion'][0]['comprobante']
                    xml_data = etree.fromstring(bytes(xml_string, encoding='utf-8'))
                    infoTributaria = xml_data.findall("infoTributaria")[0]
                    infoNotaCredito = xml_data.findall("infoNotaCredito")[0]
                    detalles = xml_data.findall("detalles")[0]
                    electronic_authorization = infoTributaria.find('claveAcceso').text
                    l10n_latam_document_number = infoTributaria.find('estab').text + "-" + infoTributaria.find(
                        'ptoEmi').text + "-" + infoTributaria.find('secuencial').text
                    l10n_latam_document_number_invoice = infoNotaCredito.find('numDocModificado').text
                    # Buscar si la nota de crédito está ya ingresada utilizando el campo de autorización adecuado
                    exists_credit_notes = self._search_move_by_auth('in_refund', electronic_authorization)
                    if len(exists_credit_notes) > 0:
                        results_credit_note['exists_credit_note'].append(
                            'La Nota de Credito %s ya existe en el sistema' % (l10n_latam_document_number))
                        found_credit_notes = found_credit_notes + 1
                        continue

                    # Buscar si existe la factura
                    exists_invoice_credit_note = self.env['account.move'].search([('move_type', '=', 'in_invoice'), (
                        'l10n_latam_document_number', '=', l10n_latam_document_number_invoice)])
                    if len(exists_invoice_credit_note) == 0:
                        results_credit_note['no_exists_invoice_credit_note'].append(
                            'La Factura %s no esta creado en el sistema, para la nota de credito %s' % (
                                l10n_latam_document_number_invoice, l10n_latam_document_number))
                        no_invoice_credit_note = no_invoice_credit_note + 1
                        continue

                    if len(exists_invoice_credit_note) != 0:
                        invoice_date = (infoNotaCredito.find('fechaEmision').text).split("/")
                        invoice_date = invoice_date[2] + "-" + invoice_date[1] + "-" + invoice_date[0]

                        vals = {
                            'partner_id': exists_invoice_credit_note.partner_id.id,
                            'invoice_date': invoice_date,
                            'l10n_latam_document_number': (
                                infoTributaria.find('estab').text + '-' +
                                infoTributaria.find('ptoEmi').text + '-' +
                                infoTributaria.find('secuencial').text
                            ),
                            'move_type': 'in_refund',
                            'invoice_rectification_id': exists_invoice_credit_note.id,
                        }
                        # Asignar la clave de acceso al campo apropiado
                        auth_field = self._authorization_field()
                        if auth_field:
                            vals[auth_field] = infoTributaria.find('claveAcceso').text
                        credit_note = self.env['account.move'].create(vals)

                        lines = []
                        for detalle in detalles:
                            impuestos = detalle.find('impuestos')
                            tax_ids = []
                            for tax in impuestos.findall("impuesto"):
                                code_tax = tax.find('codigo').text
                                if code_tax == '0':
                                    tax_id = self.env['account.tax'].search([('l10n_ec_code_base', '=', '515'), ('type_tax_use', '=', 'purchase')])
                                if code_tax == '2':
                                    tax_id = self.env['account.tax'].search([('l10n_ec_code_base', '=', '510'), ('type_tax_use', '=', 'purchase')])
                                tax_ids.append(tax_id.id)

                            quantity = float(detalle.find('cantidad').text)
                            price_unit = float(detalle.find('precioUnitario').text)
                            descuento = 0
                            if detalle.find('descuento') != None:
                                descuento = float(detalle.find('descuento').text)
                            if descuento == 0:
                                discount = 0.00
                            else:
                                discount = round(((descuento * 100) / (quantity * price_unit)), 2)

                            product = []
                            if detalle.find('codigoPrincipal') != None:
                                product = self.env['product.product'].search([('default_code', '=', detalle.find('codigoPrincipal').text)])

                            lines.append((0, 0, {'name': detalle.find('descripcion').text if detalle.find('descripcion') != None else detalle.find('codigoPrincipal').text,
                                                 'product_id': product[0].id if len(product) > 0 else False,
                                                 'account_id': credit_note.journal_id.default_account_id.id,
                                                 'quantity': detalle.find('cantidad').text,
                                                 'price_unit': detalle.find('precioUnitario').text,
                                                 'tax_ids': [(6, 0, tax_ids)] if len(tax_ids) > 0 else False,
                                                 'discount': discount, }))

                        credit_note.write({'invoice_line_ids': lines})
                        # credit_note.button_reset_taxes()
                        new_credit_notes = new_credit_notes + 1
                    else:
                        continue

        # Imprimiendo resultados
        result_str = ""
        if has_invoice:
            if result_str == "":
                result_str = "FACTURAS IMPORTADAS" + "\n"
            else:
                result_str = result_str + "\n"
                result_str = result_str + "FACTURAS IMPORTADAS" + "\n"
            if new_invoices > 0:
                result_str = result_str + "Se importaron %s Facturas" % new_invoices
                result_str = result_str + "\n"
            if found_invoices > 0:
                result_str = result_str + "%s Factura(s) ya se encuentran importadas" % found_invoices
                result_str = result_str + "\n"
            for r2 in results_invoices['no_partner']:
                result_str = result_str + str(r2) + "\n"
        if has_retention:
            if result_str == "":
                result_str = "RETENCIONES IMPORTADAS" + "\n"
            else:
                result_str = result_str + "\n"
                result_str = result_str + "RETENCIONES IMPORTADAS" + "\n"
            total_facturas_intentadas = len(total_processed) + len(missing_invoice)
            total_retentions_evaluated = len(duplicated_keys) + len(unauthorized_keys) + len(failed_keys) + len(out_range_retentions)
            total_documentos = total_facturas_intentadas + total_retentions_evaluated
            summary_str = "========================================\n"
            summary_str += "           Resumen del procesamiento\n"
            summary_str += "========================================\n"
            summary_str += f"Total facturas procesadas exitosamente: {len(total_processed)} ({(len(total_processed)/total_documentos*100 if total_documentos > 0 else 0):.2f}%)\n"
            summary_str += f"Total facturas faltantes: {len(missing_invoice)} ({(len(missing_invoice)/total_documentos*100 if total_documentos > 0 else 0):.2f}%)\n"
            summary_str += f"Total retenciones duplicadas: {len(duplicated_keys)} ({(len(duplicated_keys)/total_documentos*100 if total_documentos > 0 else 0):.2f}%)\n"
            summary_str += f"Total retenciones no autorizadas: {len(unauthorized_keys)} ({(len(unauthorized_keys)/total_documentos*100 if total_documentos > 0 else 0):.2f}%)\n"
            summary_str += f"Total retenciones fallidas: {len(failed_keys)} ({(len(failed_keys)/total_documentos*100 if total_documentos > 0 else 0):.2f}%)\n"
            summary_str += f"Total retenciones fuera de rango: {len(out_range_retentions)} ({(len(out_range_retentions)/total_documentos*100 if total_documentos > 0 else 0):.2f}%)\n"
            summary_str += "\n"

            details_str = ""
            print(details_str)

            if total_processed:
                details_str += "----------------------------------------\n"
                details_str += "    Total claves procesadas exitosamente\n"
                details_str += "----------------------------------------\n"
                for item in total_processed:
                    if isinstance(item, tuple) and len(item) == 2:
                        retention, invoice = item
                        details_str += f"- Retención: {retention}, Factura asociada: {invoice}\n"
                    else:
                        _logger.warning(f"Error: Elemento inesperado en total_processed: {item}")  # Depuración
                details_str += "\n"

            if out_range_retentions:
                details_str += "----------------------------------------\n"
                details_str += "       Retenciones fuera de rango\n"
                details_str += "----------------------------------------\n"
                for retencion in out_range_retentions:
                    details_str += f"- Clave: {retencion['clave']}, Fecha emisión: {retencion['fecha_emision']}, Días de atraso: {retencion['dias_atraso']}\n"
                details_str += "\n"

            # Detalle de claves fallidas
            if failed_keys:
                details_str += "----------------------------------------\n"
                details_str += "         Claves fallidas\n"
                details_str += "----------------------------------------\n"
                for failed in failed_keys:
                    invoice = next((k for k, v in missing_invoice_retentions.items() if v == failed), "Factura desconocida")
                    details_str += f"- Retención: {failed}, Factura asociada: {invoice}\n"
                details_str += "\n"

            # Detalle de facturas faltantes
            if missing_invoice:
                details_str += "----------------------------------------\n"
                details_str += "       Facturas faltantes\n"
                details_str += "----------------------------------------\n"
                
                unique_missing_invoices = set()
                
                for auth, invoice in missing_invoice:
                    key = (auth, invoice)
                    if key not in unique_missing_invoices:
                        unique_missing_invoices.add(key)
                        details_str += f"- Clave de autorización: {auth}, Factura no encontrada: {invoice}\n"
                details_str += "\n"

            details_str += "========================================\n"
            details_str += "           Sugerencias\n"
            details_str += "========================================\n"
            details_str += "- Verifique las facturas asociadas.\n"
            details_str += "- Revise los documentos fuera de rango y procese manualmente.\n"   

            content = summary_str + "\n" + details_str
            file_name = "Resultados.txt"
            file_data = base64.b64encode(content.encode('utf-8'))

            result_str = summary_str + "\n" + details_str
            self.results = result_str
            self.process = True

            self.write({
                'file_data': file_data,
                'file_name': file_name,
            })

            if new_retentions > 0:
                result_str = result_str + "Se importaron %s Retencion(es) de Facturas" % new_retentions
                result_str = result_str + "\n"
            if new_retentions_credit_card > 0:
                result_str = result_str + "Se importaron %s Retencion(es) de Tarjetas de Credito" % new_retentions_credit_card
                result_str = result_str + "\n"
            if found_retentions > 0:
                result_str = result_str + "%s Retencion(es) ya se encuentran importadas" % found_retentions
                result_str = result_str + "\n"
            for r2 in results_retentions['no_invoice']:
                result_str = result_str + str(r2) + "\n"
            # self.export_results()
        if has_credit_note:
            if result_str == "":
                result_str = "NOTAS DE CREDITO IMPORTADAS" + "\n"
            else:
                result_str = result_str + "\n"
                result_str = result_str + "NOTAS DE CREDITO IMPORTADAS" + "\n"
            if new_credit_notes > 0:
                result_str = result_str + "Se importaron %s NOTAS DE CREDITO" % new_credit_notes
                result_str = result_str + "\n"
            if found_credit_notes > 0:
                for r3 in results_credit_note['exists_credit_note']:
                    result_str = result_str + str(r3) + "\n"
            if no_invoice_credit_note > 0:
                for r4 in results_credit_note['no_exists_invoice_credit_note']:
                    result_str = result_str + str(r4) + "\n"

        self.results = result_str
        self.process = True
        # return {
        #     'type': 'ir.actions.act_refresh_dialog',
        # }

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'ec.sri.load.edi',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': self.id,
            'views': [(False, 'form')],
            'target': 'new',
        }

    def import_files(self):
        def gt_txt(elem):
            return elem != None and elem.text or ''

        # result = []
        errores = []
        result_str = ""
        retenciones_cargadas = []
        for data_xml in self.xmls_ids:
            data = XML(base64.b64decode(data_xml.datas))
            # Depuración: registrar la etiqueta raíz del XML en proceso.  Se utiliza %s en lugar de %s
            _logger.debug("Procesando arhivo XML: %s", data.tag)
            if data.tag == 'autorizacion':
                try:
                    if gt_txt(data.find("ambiente")) == 'PRODUCCIÓN':
                        document = gt_txt(data.find('comprobante'))
                        # Depuración: mostrar los primeros 100 caracteres del documento
                        _logger.debug("Documento encontrado: %s", document[:100])
                        # Validación si el documento pertenece a la compañía
                        if self.company_id.vat not in document:
                            _logger.warning("El XML no pertenece a la compañia..!!: %s", self.company_id.vat)
                            raise UserError(_("El XML no pertenece a la compañia..!!"))

                        type_of_document = {
                            'infoFactura' in document: 'invoice',
                            'infoCompRetencion' in document: 'retention',
                            'infoNotaDebito' in document or 'infoNotaCredito' in document: 'nota_v'
                        }.get(True)
                        _logger.info("Tipo de documento identificado: %s", type_of_document)
                        # Si el tipo de documento es 'retencion', procesamos las retenciones
                        if type_of_document == 'retention':
                            invoice=False
                            xml_data = XML(document)

                            # Extraemos el número de retención antes de procesar
                            infoTributaria = xml_data.find("infoTributaria")
                            l10n_latam_document_number = (
                                f"{infoTributaria.find('estab').text}-"
                                f"{infoTributaria.find('ptoEmi').text}-"
                                f"{infoTributaria.find('secuencial').text}"
                            )
                            # Depuración: número formateado de la retención
                            _logger.debug("Numero de retencion: %s", l10n_latam_document_number)
                            try:
                                result_str = self.import_retention(xml_data, self.type, 'xml')
                                if result_str:
                                    retenciones_cargadas.append(result_str)
                            except UserError as e:
                                errores.append(f"Error con la retención {l10n_latam_document_number}: {str(e)}")
                                _logger.error(f"Error con la retención {l10n_latam_document_number}: {str(e)}")
                            except Exception as e:
                                error_str = str(e)
                                if "Invalid field 'multiple'" in error_str:
                                    mensaje_amigable = (
                                        "La retención no pudo ser procesada porque el sistema aún no habilita la opción "
                                        "de retenciones con múltiples facturas. Por favor contacte al administrador del sistema."
                                    )
                                    errores.append(f"Error con la retención {l10n_latam_document_number}: {mensaje_amigable}")
                                    _logger.error(f"Error con la retención {l10n_latam_document_number}: {mensaje_amigable}")
                                else:
                                    errores.append(f"Error desconocido con la retención {l10n_latam_document_number}: {error_str}")
                                    _logger.error(f"Error desconocido con la retención {l10n_latam_document_number}: {error_str}")

                            # if self.type_xml == 'ret_tc':
                            #     codigo_ret = False
                            #     porcentaje_ret = False
                            #     codigoRetencion = False
                            #     codigoRetencion = False
                            #     valorRetenido = False
                            #     if impuesto.find("codigo") != None:
                            #         codigo = impuesto.find('codigo').text
                            #         porcentajeRetener = impuesto.find('porcentajeRetener').text
                            #         codigoRetencion = impuesto.find('codigoRetencion').text
                            #         baseImponible = impuesto.find('baseImponible').text
                            #         valorRetenido = impuesto.find('valorRetenido').text
                            #
                            #     elif impuesto.find('retencion') != None:
                            #         codigo = impuesto.find('retencion').find('codigo').text
                            #         porcentajeRetener = impuesto.find('retencion').find('porcentajeRetener').text
                            #         codigoRetencion = impuesto.find('retencion').find('codigoRetencion').text
                            #         baseImponible = impuesto.find('retencion').find('baseImponible').text
                            #         valorRetenido = impuesto.find('retencion').find('valorRetenido').text
                            #     else:
                            #         codigo = impuesto.find('impuesto').find('codigo').text
                            #         porcentajeRetener = impuesto.find('impuesto').find('porcentajeRetener').text
                            #         codigoRetencion = impuesto.find('impuesto').find('codigoRetencion').text
                            #         baseImponible = impuesto.find('impuesto').find('baseImponible').text
                            #         valorRetenido = impuesto.find('impuesto').find('valorRetenido').text
                            #
                            #     if codigo == '1':
                            #         description = 'retencion_renta'
                            #         tax_id = self.env['account.tax'].search([('l10n_ec_code_base', '=', codigoRetencion),
                            #                                                  ('tax_group_id.l10n_ec_type', '=',
                            #                                                   'withhold_income_tax')])
                            #     else:
                            #         description = 'retencion_iva'
                            #         amount = 0.00
                            #         cod_ret = None
                            #         if float(porcentajeRetener) == 20.00:
                            #             # amount = -3.6000
                            #             cod_ret = '609'
                            #         if float(porcentajeRetener) == 30.00:
                            #             # amount = -3.6000
                            #             cod_ret = '609'
                            #         if float(porcentajeRetener) == 70.00:
                            #             # amount = -3.6000
                            #             cod_ret = '609'
                            #         if float(porcentajeRetener) == 100.00:
                            #             # amount = -3.6000
                            #             cod_ret = '609'
                            #         tax_id = self.env['account.tax'].search([('l10n_ec_code_base', '=', cod_ret), (
                            #             'tax_group_id.l10n_ec_type', '=', 'withhold_vat')])
                            #     impuestos_credit_card_lines.append((0, 0, {'description': description,
                            #                                                'tax_id': tax_id[0].id if len(tax_id) > 0 else False,
                            #                                                'tax_base': float(baseImponible),
                            #                                                'retention_percentage_manual': float(
                            #                                                    porcentajeRetener),
                            #                                                'retained_value_manual': float(valorRetenido)}))
                            # if self.type_xml == 'ret_tc':
                            #     ruc = infoTributaria.find('ruc').text
                            #     partner = self.env['res.partner'].search([('vat', '=', ruc)])
                            #     if len(partner) > 0:
                            #         date_retention = (infoCompRetencion.find('fechaEmision').text).split("/")
                            #         date_retention = date_retention[2] + "-" + date_retention[1] + "-" + date_retention[0]
                            #         new_retention_credit_card = self.env['account.withhold'].create(
                            #             {'transaction_type': 'sale',
                            #              'tarjeta_credito': True,
                            #              'multiple': True,
                            #              'document_type': 'electronic',
                            #              'partner_multi_id': partner[0].id,
                            #              'creation_date': date_retention,
                            #              'electronic_authorization': electronic_authorization,
                            #              'l10n_latam_document_number': l10n_latam_document_number,
                            #              'document_number': l10n_latam_document_number, })
                            #         new_retention_credit_card.write({'retention_line_ids': impuestos_credit_card_lines})
                            #         new_retention_credit_card._compute_amount()
                            #         result_str = "Se cargo la retención de tarjeta de credito: %s" % l10n_latam_document_number
                        if type_of_document == 'invoice':
                            # crear patner
                            invoice_data = XML(document)
                            infoTributaria = invoice_data.find("infoTributaria")
                            infoFactura = invoice_data.find("infoFactura")
                            detalles = invoice_data.find("detalles")
                            electronic_authorization = infoTributaria.find('claveAcceso').text
                            l10n_latam_document_number = infoTributaria.find('estab').text + "-" + infoTributaria.find('ptoEmi').text + "-" + infoTributaria.find('secuencial').text
                            _logger.debug("Procesando factura electronica: %s", l10n_latam_document_number)
                            # Buscar si hay facturas ingresadas con autorizaciones
                            # Buscar facturas ingresadas por clave de acceso utilizando el campo disponible
                            exists_invoices = self._search_move_by_auth('in_invoice', electronic_authorization)
                            if exists_invoices:
                                _logger.warning("Factura duplicada encontrada: %s", electronic_authorization)
                                raise UserError(_("La Factura ya se encuentra ingresada!!"))

                            # Buscar el proveedor por RUC
                            ruc = infoTributaria.find('ruc').text
                            razon_social = infoTributaria.find('razonSocial').text
                            direccion = infoTributaria.find('dirMatriz').text
                            partner_invoice = self.env['res.partner'].search([('vat', '=', ruc)])
                            
                            # Si el proveedor no existe, lo creamos
                            if not partner_invoice:
                                email = False
                                if self.env.user.company_id.documents_electronic_settings_id:
                                    if self.env.user.company_id.documents_electronic_settings_id.electronic_authorization:
                                        email = self.env.user.company_id.documents_electronic_settings_id.electronic_authorization.email_notification
                                else:
                                    email = self.env.user.company_id.partner_id.email if self.env.user.company_id.partner_id.email else 'sri@sri.com'

                                partner_invoice = self.env['res.partner'].create({'name': razon_social,
                                                                                'vat': ruc,
                                                                                'street': direccion,
                                                                                'is_company': True,
                                                                                'company_type': 'company',
                                                                                'email': email})
                                partner_invoice = self.env['res.partner'].search([('vat', '=', ruc)])

                            if partner_invoice:
                                # Verificamos si la factura ya existe para este proveedor y documento
                                exists_invoices = self.env['account.move'].search([('move_type', '=', 'in_invoice'),('partner_id','=',partner_invoice[0].id),('l10n_latam_document_number', '=', l10n_latam_document_number)])
                                if exists_invoices:
                                    raise UserError(_("La Factura ya se encuentra ingresada!!"))

                                # Procesamos la fecha de la factura
                                date_invoice = (infoFactura.find('fechaEmision').text).split("/")
                                date_invoice = f"{date_invoice[2]}-{date_invoice[1]}-{date_invoice[0]}"
                                
                                # Creamos la factura
                                vals = {
                                    'partner_id': partner_invoice[0].id,
                                    'invoice_date': date_invoice,
                                    'l10n_latam_document_number': l10n_latam_document_number,
                                    'move_type': 'in_invoice',
                                    'is_xml': True,
                                }
                                # Si el proveedor coincide con la compañía, se trata de una
                                # autofactura interna; activamos la casilla para evitar
                                # el error de validación del módulo account_internal_self_invoice.
                                try:
                                    company_partner = self.env.company.partner_id
                                    if partner_invoice and partner_invoice[0].id == company_partner.id:
                                        vals['is_internal_self_invoice'] = True
                                except Exception:
                                    pass
                                # Asignamos la clave de acceso al campo correcto
                                auth_field = self._authorization_field()
                                if auth_field:
                                    vals[auth_field] = electronic_authorization
                                invoice = self.env['account.move'].create(vals)
                                _logger.info(f"Factura cargada: {l10n_latam_document_number}")

                                lines = []
                                for detalle in detalles:
                                    impuestos = detalle.find('impuestos')
                                    tax_ids = []
                                    for tax in impuestos.findall("impuesto"):
                                        code_tax = tax.find('codigoPorcentaje').text
                                        if code_tax == '0':
                                            tax_id = self.env['account.tax'].search([('l10n_ec_code_base', '=', '517'), ('type_tax_use', '=', 'purchase')])
                                        elif code_tax == '2':
                                            tax_id = self.env['account.tax'].search([('l10n_ec_code_base', '=', '510'), ('type_tax_use', '=', 'purchase')])
                                        elif code_tax == '4':
                                            tax_id = self.env['account.tax'].search([('l10n_ec_code_base', '=', '510'), ('amount', '=', float(tax.find('tarifa').text)), ('type_tax_use', '=', 'purchase')])
                                        elif code_tax not in ('0', '2', '4'):
                                            tax_id = self.env['account.tax'].search([('l10n_ec_code_base', '=', code_tax), ('type_tax_use', '=', 'purchase')])
                                        if code_tax == '7':
                                            continue
                                        if code_tax == '3':
                                            tax_id = self.env['account.tax'].search([('l10n_ec_code_base', '=', code_tax), ('type_tax_use', '=', 'purchase')])

                                        if tax_id:
                                            tax_ids.append(tax_id.id)

                                    # Procesamos las líneas del detalle de la factura
                                    quantity = float(detalle.find('cantidad').text)
                                    price_unit = float(detalle.find('precioUnitario').text)
                                    descuento = float(detalle.find('descuento').text)
                                    discount = round(((descuento * 100) / (quantity * price_unit)), 2) if descuento != 0 else 0.00
                                    discount_fixed = descuento if descuento != 0 else 0.00

                                    product = self.env['product.product'].search([('default_code', '=', detalle.find('codigoPrincipal').text)])
                                    product_id = product[0].id if product else False
                                    account_id = invoice.journal_id.default_account_id.id

                                    lines.append((0, 0, {
                                        'name': detalle.find('descripcion').text if detalle.find('descripcion') is not None else detalle.find('codigoPrincipal').text,
                                        'product_id': product_id,
                                        'account_id': account_id,
                                        'debit': price_unit < 0.0 and -price_unit or 0.0,
                                        'credit': price_unit > 0.0 and price_unit or 0.0,
                                        'quantity': detalle.find('cantidad').text,
                                        'price_unit': price_unit,
                                        'tax_ids': [(6, 0, tax_ids)] if tax_ids else False,
                                        'discount': discount,
                                        'discount_fixed': discount_fixed,
                                        'is_upload_xml': True
                                    }))

                                # Escribimos las líneas de la factura
                                invoice.write({'invoice_line_ids': lines})
                                result_str = f"Se cargó la factura de proveedor: {l10n_latam_document_number}"

                except UserError as e:
                        # Extraemos el número de la factura que está causando el error
                        numero_factura = l10n_latam_document_number if 'l10n_latam_document_number' in locals() else "Desconocido"
                        errores.append(f"Error con la factura {numero_factura}: {str(e)}")
                        _logger.error(f"Error con la factura {numero_factura}: {str(e)}")
                except Exception as e:
                    errores.append(f"Error desconocido al procesar el XML: {str(e)}")
                    _logger.error(f"Error desconocido al procesar el XML: {str(e)}")
        if errores or retenciones_cargadas:
            retenciones_ingresadas = [error.replace("Error", "Aviso") for error in errores if "La Retención ya se encuentra ingresada" in error]
            facturas_no_ingresadas = [error for error in errores if "La Factura no se encuentra ingresada en el sistema" in error]
            errores_desconocidos = [
                error for error in errores
                if "La Retención ya se encuentra ingresada" not in error
                and "La Factura no se encuentra ingresada en el sistema" not in error
                and "No puede añadir / modificar asientos anteriores y hasta la fecha de bloqueo" not in error            
            ]
            retenciones_borrador = [
                error for error in errores
                if "No puede añadir / modificar asientos anteriores y hasta la fecha de bloqueo" in error
            ]    
            total = len(retenciones_cargadas) + len(errores)
            mensaje_error = (
                "===================================\n"
                "           Resumen del procesamiento\n"
                "===================================\n"
                f"Retenciones cargadas: {len(retenciones_cargadas)} ({(len(retenciones_cargadas)/total*100 if total else 0):.2f}%)\n"
                f"Retenciones ya ingresadas: {len(retenciones_ingresadas)} ({(len(retenciones_ingresadas)/total*100 if total else 0):.2f}%)\n"
                f"Facturas no ingresadas: {len(facturas_no_ingresadas)} ({(len(facturas_no_ingresadas)/total*100 if total else 0):.2f}%)\n"
                f"‼ Retenciones con error inesperado: {len(errores_desconocidos)} ({(len(errores_desconocidos)/total*100 if total else 0):.2f}%)\n"
                f"Retenciones en borrador (por bloqueo): {len(retenciones_borrador)} ({(len(retenciones_borrador)/total*100 if total else 0):.2f}%)\n"
                "\n"
            )
            detalle_error = (
                "----------------------\n"
                "Detalle de Resultados:\n"
                "----------------------\n"
                "Retenciones cargadas:\n" +
                "\n".join(retenciones_cargadas) + "\n\n" +
                "Retenciones ya ingresadas:\n" +
                "\n".join(retenciones_ingresadas) + "\n\n" +
                "Facturas no ingresadas:\n" +
                "\n".join(facturas_no_ingresadas) + "\n\n" +
                "‼ Retenciones con error inesperado:\n" +
                "\n".join(errores_desconocidos) + "\n\n" +
                "Retenciones ingresadas en borrador (por fecha bloqueada):\n" +
                "\n".join(retenciones_borrador)
            )

            content = mensaje_error + detalle_error
            file_name = "Resultados.txt"
            file_data = base64.b64encode(content.encode('utf-8'))

            self.results = mensaje_error
            self.process = True

            self.write({
                'file_data': file_data,
                'file_name': file_name,
            })

            return {
                'type': 'ir.actions.act_window',
                'res_model': 'ec.sri.load.edi',
                'view_mode': 'form',
                'view_type': 'form',
                'res_id': self.id,
                'views': [(False, 'form')],
                'target': 'new',
            }
        else:
            self.results = "Carga completada sin errores."
            self.process = True
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'ec.sri.load.edi',
                'view_mode': 'form',
                'view_type': 'form',
                'res_id': self.id,
                'views': [(False, 'form')],
                'target': 'new',
            }

    def import_retention(self, xml_data, type, type_import):
        """
        Procesa una retención priorizando el vínculo por partner (RUC) en
        lugar de exigir una factura específica.

        Reglas:
        - Si la retención ya existe por clave de acceso, no se vuelve a crear.
        - Si el emisor está marcado como banco/tarjeta, crea un asiento
          contable simple usando ``_create_credit_card_withhold``.
        - Para cualquier otro partner, crea la retención como saldo a favor
          del cliente usando ``_create_unlinked_sale_withhold``.

        Esto replica el comportamiento descrito en el video: la retención se
        registra aunque no exista la factura y luego puede aplicarse como
        crédito desde las facturas del cliente.
        """
        results_retentions = []
        new_retentions = 0
        new_retentions_credit_card = 0
        found_retentions = 0

        info_trib = xml_data.find('infoTributaria')
        if info_trib is None:
            if type_import == 'xml':
                raise UserError(_('El XML no contiene infoTributaria.'))
            return [_('XML inválido: no contiene infoTributaria')], 0, 0, 0

        access_key = info_trib.findtext('claveAcceso')
        document_number = '%s-%s-%s' % (
            info_trib.findtext('estab') or '',
            info_trib.findtext('ptoEmi') or '',
            info_trib.findtext('secuencial') or '',
        )

        if self._withhold_exists(access_key, withhold_type='out_withhold'):
            if type_import == 'xml':
                raise UserError(_('La Retención ya se encuentra ingresada!!'))
            found_retentions += 1
            return results_retentions, found_retentions, new_retentions, new_retentions_credit_card

        ruc = info_trib.findtext('ruc')
        razon_social = info_trib.findtext('razonSocial') or 'Contacto SRI'
        partner = self.env['res.partner'].search([('vat', '=', ruc)], limit=1)
        if not partner:
            id_type = self.env['l10n_latam.identification.type'].search([('name', '=', 'Ruc')], limit=1)
            partner = self.env['res.partner'].create({
                'name': razon_social,
                'vat': ruc,
                'l10n_latam_identification_type_id': id_type.id if id_type else False,
                'email': self.env.company.partner_id.email,
            })

        info_comp = xml_data.find('infoCompRetencion')
        fecha_emision = info_comp.findtext('fechaEmision') if info_comp is not None else False
        if fecha_emision and '/' in fecha_emision:
            dd, mm, yyyy = fecha_emision.split('/')
            date_retention = f'{yyyy}-{mm}-{dd}'
        else:
            date_retention = fields.Date.context_today(self)

        impuesto_nodes = []
        version = xml_data.attrib.get('version')
        if version == '1.0.0':
            impuestos_elem = xml_data.find('impuestos')
            if impuestos_elem is not None:
                impuesto_nodes.extend(impuestos_elem.findall('impuesto'))
        elif version == '2.0.0':
            docs_elem = xml_data.find('docsSustento')
            if docs_elem is not None:
                for doc in docs_elem.findall('docSustento'):
                    retenciones_elem = doc.find('retenciones')
                    if retenciones_elem is not None:
                        impuesto_nodes.extend(retenciones_elem.findall('retencion'))

        if not impuesto_nodes:
            if type_import == 'xml':
                raise UserError(_('No se encontraron impuestos en la retención.'))
            results_retentions.append(_('No se encontraron impuestos en la retención: %s') % document_number)
            return results_retentions, found_retentions, new_retentions, new_retentions_credit_card

        is_bank_partner = bool(getattr(partner, 'is_bank_partner', False))
        if not is_bank_partner:
            razon_upper = (razon_social or '').upper()
            partner_upper = (partner.name or '').upper()
            bank_markers = ['BANCO', 'DINERS', 'PACIFICO', 'TARJETA', 'VISA', 'MASTERCARD', 'AMEX']
            if any(marker in razon_upper for marker in bank_markers) or any(marker in partner_upper for marker in bank_markers):
                is_bank_partner = True
        if not is_bank_partner:
            # también tratar como banco si el soporte es 000-000-000000000
            try:
                for node in impuesto_nodes:
                    num_doc = (node.findtext('numDocSustento') or '').replace('-', '')
                    if num_doc == '000000000000000' or num_doc.startswith('000000'):
                        is_bank_partner = True
                        break
            except Exception:
                pass
        if not is_bank_partner:
            try:
                # Detección adicional para XML v2 de tarjetas/bancos
                docs_elem = xml_data.find('docsSustento')
                if docs_elem is not None:
                    for doc in docs_elem.findall('docSustento'):
                        if (doc.findtext('codDocSustento') or '').strip() == '12':
                            is_bank_partner = True
                            break
                        if (doc.findtext('formaPago') or '').strip() == '20':
                            is_bank_partner = True
                            break
            except Exception:
                pass

        if is_bank_partner:
            self._create_credit_card_withhold(
                partner=partner,
                document_number=document_number,
                access_key=access_key,
                date_retention=date_retention,
                impuesto_nodes=impuesto_nodes,
            )
            new_retentions_credit_card += 1
            msg = _('Se cargó la retención bancaria: %s') % document_number
            if type_import == 'xml':
                return msg
            results_retentions.append(msg)
            return results_retentions, found_retentions, new_retentions, new_retentions_credit_card

        # ── Buscar facturas sustento vinculadas por numDocSustento ────────────
        # Se busca cada número de documento sustento en las facturas posted del
        # partner.  Si se encuentran facturas pendientes de pago, se usa el
        # wizard de retenciones (que reconcilia automáticamente).  Si las facturas
        # ya están pagadas, o no se encuentran, se crea un saldo a favor.
        linked_invoices = self.env['account.move']
        for _node in impuesto_nodes:
            num_raw = (_node.findtext('numDocSustento') or '').replace('-', '')
            if len(num_raw) >= 7:
                num_invoice = num_raw[:3] + '-' + num_raw[3:6] + '-' + num_raw[6:]
            elif num_raw:
                num_invoice = num_raw
            else:
                continue
            inv_found = self.env['account.move'].search([
                ('move_type', '=', 'out_invoice'),
                ('partner_id', '=', partner.id),
                ('l10n_latam_document_number', '=', num_invoice),
                ('state', '=', 'posted'),
            ], limit=1)
            if inv_found and inv_found not in linked_invoices:
                linked_invoices |= inv_found

        invoice_amount_residual = sum(linked_invoices.mapped('amount_residual'))
        remove_reconcile = (invoice_amount_residual <= 0)

        if linked_invoices and not remove_reconcile:
            # Factura pendiente → wizard con conciliación automática
            impuestos_invoice_lines = []
            for _node in impuesto_nodes:
                line = self.create_line_retention(_node, False)
                if line:
                    impuestos_invoice_lines.append(line)
            if impuestos_invoice_lines:
                self._create_withhold_l10n_ec(
                    invoices=linked_invoices,
                    document_number=document_number,
                    access_key=access_key,
                    date_retention=date_retention,
                    impuestos_invoice_lines=impuestos_invoice_lines,
                    withhold_type='out_withhold',
                    remove_reconcile=False,
                )
                new_retentions += 1
                msg = _('Se cargó la retención: %s vinculada y conciliada con factura pendiente') % document_number
                if type_import == 'xml':
                    return msg
                results_retentions.append(msg)
                return results_retentions, found_retentions, new_retentions, new_retentions_credit_card

        # Sin factura encontrada o sin líneas válidas → saldo a favor
        self._create_unlinked_sale_withhold(
            partner=partner,
            document_number=document_number,
            access_key=access_key,
            date_retention=date_retention,
            impuesto_nodes=impuesto_nodes,
        )
        new_retentions += 1
        msg = _('Se cargó la retención de venta: %s como saldo a favor') % document_number
        if type_import == 'xml':
            return msg
        results_retentions.append(msg)
        return results_retentions, found_retentions, new_retentions, new_retentions_credit_card
