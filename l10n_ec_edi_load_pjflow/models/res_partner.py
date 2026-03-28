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
import time
import logging
import traceback
from lxml import etree
from xml.etree.ElementTree import Element, SubElement, tostring
from datetime import datetime
# --------------------------------------------------------------------------
# Suds SOAP client dependency
# --------------------------------------------------------------------------
try:
    from suds import WebFault  # type: ignore
    from suds.client import Client  # type: ignore
except Exception:
    WebFault = Exception  # type: ignore
    class Client:  # type: ignore
        def __init__(self, *args, **kwargs) -> None:
            from odoo.exceptions import UserError  # local import
            from odoo.tools.translate import _  # local import
            raise UserError(_(
                "La librería de cliente SOAP 'suds' no está instalada. "
                "Instale 'suds-py3' mediante pip para poder utilizar las "
                "consultas de comprobantes electrónicos del SRI."
            ))
from pprint import pformat
# --------------------------------------------------------------------------
# py4j gateway dependency
# --------------------------------------------------------------------------
try:
    from py4j.java_gateway import JavaGateway, GatewayClient  # type: ignore
except Exception:
    def _missing_py4j_partner(*args, **kwargs):
        from odoo.exceptions import UserError
        from odoo.tools.translate import _
        raise UserError(_(
            "La librería 'py4j' no está instalada. "
            "Instale 'py4j' (por ejemplo, con pip) para poder utilizar la "
            "pasarela Java necesaria para la firma de documentos."
        ))
    class JavaGateway:  # type: ignore
        def __init__(self, *args, **kwargs) -> None:
            _missing_py4j_partner()
    class GatewayClient:  # type: ignore
        def __init__(self, *args, **kwargs) -> None:
            _missing_py4j_partner()
from odoo import models, api, fields
from odoo import tools
from odoo.tools.translate import _
import odoo.addons
from odoo.tools.safe_eval import safe_eval as eval
# `except_orm` was deprecated and removed in recent Odoo versions.  Import
# only the exception classes that are still available.  The generic
# `UserError` is used to raise user‑facing errors and `ValidationError`
# validates model constraints.
from odoo.exceptions import UserError, ValidationError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DTF
from odoo.tools import float_compare
import base64
# ``modules_mapping`` was previously imported from the custom module
# ``ec_sri_authorizathions``.  The mapping is not used in this model and
# removing the import avoids a dependency on that module.
# --------------------------------------------------------------------------
# OpenSSL dependency
# --------------------------------------------------------------------------
try:
    from OpenSSL import crypto  # type: ignore
except Exception:
    class _MissingOpenSSLPartner:  # type: ignore
        def __getattr__(self, name: str):
            from odoo.exceptions import UserError
            from odoo.tools.translate import _
            raise UserError(_(
                "La librería 'pyopenssl' (paquete OpenSSL) no está instalada. "
                "Instale 'pyopenssl' para poder procesar certificados digitales."
            ))
    crypto = _MissingOpenSSLPartner()  # type: ignore
from random import randrange
# --------------------------------------------------------------------------
# xmlsig dependency
# --------------------------------------------------------------------------
try:
    import xmlsig  # type: ignore
except Exception:
    class _MissingXmlSigPartner:  # type: ignore
        def __getattr__(self, name: str):
            from odoo.exceptions import UserError
            from odoo.tools.translate import _
            raise UserError(_(
                "La librería 'xmlsig' no está instalada. "
                "Instale 'xmlsig' para poder firmar documentos XML."
            ))
    xmlsig = _MissingXmlSigPartner()  # type: ignore
# --------------------------------------------------------------------------
# xades dependency
# --------------------------------------------------------------------------
try:
    from xades import template, XAdESContext  # type: ignore
    from xades.policy import GenericPolicyId, ImpliedPolicy  # type: ignore
except Exception:
    def _missing_xades_partner(*args, **kwargs):
        from odoo.exceptions import UserError
        from odoo.tools.translate import _
        raise UserError(_(
            "La librería 'xades' no está instalada. "
            "Instale 'xades' (por ejemplo, con pip) para firmar documentos XML con XAdES."
        ))
    class _MissingXadesModulePartner:
        def __getattr__(self, name: str):
            return _missing_xades_partner
    template = _MissingXadesModulePartner()  # type: ignore
    XAdESContext = _MissingXadesModulePartner()  # type: ignore
    GenericPolicyId = _MissingXadesModulePartner()  # type: ignore
    ImpliedPolicy = _MissingXadesModulePartner()  # type: ignore
import json
# --------------------------------------------------------------------------
# xmltodict dependency
# --------------------------------------------------------------------------
try:
    import xmltodict  # type: ignore
except Exception:
    class _MissingXmlToDictPartner:  # type: ignore
        def __getattr__(self, name: str):
            from odoo.exceptions import UserError
            from odoo.tools.translate import _
            raise UserError(_(
                "La librería 'xmltodict' no está instalada. "
                "Instale 'xmltodict' para poder procesar documentos XML como diccionarios."
            ))
    xmltodict = _MissingXmlToDictPartner()  # type: ignore
from xml.etree.ElementTree import XML, Element

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_bank_partner = fields.Boolean(string='Es Banco', default=False)