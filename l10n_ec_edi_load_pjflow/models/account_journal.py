# -*- encoding: utf-8 -*-

from odoo import api, Command, fields, models, _
# The original code imported ``modules_mapping`` from a custom module
# ``ec_sri_authorizathions``.  The mapping is not used anywhere in this
# model, so the import has been removed to eliminate an unnecessary
# dependency on that module.
from odoo.exceptions import UserError, ValidationError
import logging
import xmltodict
from xml.etree.ElementTree import XML, Element
import base64
from lxml import etree
_logger = logging.getLogger(__name__)


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    def create_document_from_attachment(self, attachment_ids=None):
        def gt_txt(elem):
            return elem != None and elem.text or ''

        # if 'default_move_type' in self.env.context:
        #     if self.env.context['default_move_type']!='in_invoice':
        #         raise UserError(_("Por ahora solo puede subir facturas de proveedor.!!"))

        invoices = self.env['account.move']
        attachments = self.env['ir.attachment'].browse(attachment_ids)
        for attachment in attachments:
            data = XML(base64.b64decode(attachment.datas))
            xml_str = attachment.raw.decode("UTF-8")
            data_xml = xmltodict.parse(xml_str)
            if 'autorizacion' in data_xml:
                if gt_txt(data.find("ambiente")) == 'PRODUCCIÓN':
                    document = gt_txt(data.find('comprobante'))
                    type_of_document = {
                        'infoFactura' in document: 'invoice',
                        'infoCompRetencion' in document: 'retention',
                        'infoNotaDebito' in document or 'infoNotaCredito' in document: 'nota_v'}.get(True)
                    if type_of_document == 'invoice':
                        #crear partner
                        invoice_data = XML(document)
                        infoTributaria = invoice_data.find("infoTributaria")
                        infoFactura = invoice_data.find("infoFactura")
                        detalles = invoice_data.find("detalles")
                        electronic_authorization = infoTributaria.find('claveAcceso').text
                        document_number = infoTributaria.find('estab').text + "-" + infoTributaria.find('ptoEmi').text + "-" + infoTributaria.find('secuencial').text

                        # Buscar si hay facturas ingresadas con autorizaciones
                        exists_invoices = self.env['account.move'].search([('move_type', '=', 'in_invoice'), ('electronic_authorization', '=', electronic_authorization)])
                        if len(exists_invoices) > 0:
                            raise UserError(_("La Factura ya se encuentra ingresada!!"))

                        # Buscar si no existe el Proveedor
                        ruc = infoTributaria.find('ruc').text
                        razon_social = infoTributaria.find('razonSocial').text
                        direccion = infoTributaria.find('dirMatriz').text
                        partner_invoice = self.env['res.partner'].search([('vat', '=', ruc)])
                        if len(partner_invoice) == 0:
                            email = False
                            if self.env.user.company_id.documents_electronic_settings_id:
                                if self.env.user.company_id.documents_electronic_settings_id.electronic_authorization:
                                    email = self.env.user.company_id.documents_electronic_settings_id.electronic_authorization.email_notification
                            else:
                                if self.env.user.company_id.partner_id.email:
                                    email = self.env.user.company_id.partner_id.email

                            partner_invoice = self.env['res.partner'].create({'name': razon_social,
                                                                              'vat': ruc,
                                                                              'street': direccion,
                                                                              'is_company': True,
                                                                              'company_type': 'company',
                                                                              'email': email if email else 'sri@sri.com'})
                            partner_invoice = self.env['res.partner'].search([('vat', '=', ruc)])
                        if len(partner_invoice) != 0:
                            # Buscar si hay facturas ingresadas con numero de factura
                            exists_invoices = self.env['account.move'].search([('move_type', '=', 'in_invoice'),
                                                                               ('partner_id', '=', partner_invoice[0].id),
                                                                               ('l10n_latam_document_number', '=', document_number)])
                            if len(exists_invoices) > 0:
                                raise UserError(_("La Factura ya se encuentra ingresada!!"))

                            date_invoice = (infoFactura.find('fechaEmision').text).split("/")
                            date_invoice = date_invoice[2] + "-" + date_invoice[1] + "-" + date_invoice[0]
                            vals = {'partner_id': partner_invoice[0].id,
                                    'invoice_date': date_invoice,
                                    'electronic_authorization': infoTributaria.find('claveAcceso').text,
                                    'l10n_latam_document_number': infoTributaria.find('estab').text + "-" + infoTributaria.find('ptoEmi').text + "-" + infoTributaria.find('secuencial').text,
                                    'move_type': 'in_invoice',
                                    'document_type': 'electronic',
                                    'is_xml': True,
                                    }
                            invoice = self.env['account.move'].create(vals)
                            _logger.info(document_number)

                            lines = []
                            for detalle in detalles:
                                impuestos = detalle.find('impuestos')
                                tax_ids = []
                                for tax in impuestos.findall("impuesto"):
                                    code_tax = tax.find('codigoPorcentaje').text
                                    if code_tax == '0':
                                        tax_id = self.env['account.tax'].search([('l10n_ec_code_base', '=', '517'), ('type_tax_use', '=', 'purchase')])
                                    if code_tax == '2':
                                        tax_id = self.env['account.tax'].search([('l10n_ec_code_base', '=', '510'), ('type_tax_use', '=', 'purchase')])
                                    if code_tax not in ('0','2'):
                                        tax_id = self.env['account.tax'].search([('l10n_ec_code_base', '=', code_tax), ('type_tax_use', '=', 'purchase')])
                                    if code_tax == '7':
                                        continue
                                    if code_tax == '3':
                                        tax_id = self.env['account.tax'].search([('l10n_ec_code_base', '=', code_tax), ('type_tax_use', '=', 'purchase')])
                                    if len(tax_id)!=0:
                                        tax_ids.append(tax_id.id)
                                quantity = float(detalle.find('cantidad').text)
                                price_unit = float(detalle.find('precioUnitario').text)
                                descuento = float(detalle.find('descuento').text)
                                if descuento == 0:
                                    discount = 0.00
                                    discount_fixed = 0.00
                                else:
                                    discount = round(((descuento * 100) / (quantity * price_unit)), 2)
                                    discount_fixed = descuento
                                product = []
                                name_product = False
                                product_id = False
                                account_id = invoice.journal_id.default_account_id.id
                                if detalle.find('codigoPrincipal') != None:
                                    name_product = detalle.find('descripcion').text if detalle.find('descripcion') != None else detalle.find('codigoPrincipal').text
                                    product_id = product[0].id if len(product) > 0 else False
                                    product = self.env['product.product'].search([('default_code', '=', detalle.find('codigoPrincipal').text)])
                                    #buscar en línea de homologación
                                    # homologations = self.env['homologation.products.move'].search([('partner_id','=',partner_invoice[0].id)])
                                    # if len(homologations)!=0:
                                    #     for hg in homologations:
                                    #         for line in hg.line_ids:
                                    #             if line.line_txt == name_product and line.product_id:
                                    #                 product_id = line.product_id.id
                                    #                 account_id = line.product_id.property_account_expense_id.id if line.product_id.property_account_expense_id else invoice.journal_id.default_account_id.id

                                lines.append((0, 0, {'name': name_product,
                                                     'product_id': product_id,
                                                     'account_id': account_id,
                                                     'debit': price_unit < 0.0 and -price_unit or 0.0,
                                                     'credit': price_unit > 0.0 and price_unit or 0.0,
                                                     'quantity': detalle.find('cantidad').text,
                                                     'price_unit': price_unit,
                                                     'tax_ids': [(6, 0, tax_ids)] if len(tax_ids) > 0 else False,
                                                     'discount': discount,
                                                     'discount_fixed': discount_fixed,
                                                     'is_upload_xml':True}))
                            invoice.write({'invoice_line_ids': lines})
                            # Proceso para homologacion
                            # for line in invoice.invoice_line_ids:
                            #     line.with_context(taxes_xml=tax_ids)._onchange_product_id()
                            # invoice.with_context(check_move_validity=False)._recompute_dynamic_lines(recompute_all_taxes=True)
                            invoices += invoice
                    if type_of_document == 'retention':
                        retention_invoice = False
                        retention_credit_card = False
                        xml_data = XML(document)
                        infoTributaria = xml_data.find("infoTributaria")
                        infoCompRetencion = xml_data.find("infoCompRetencion")
                        electronic_authorization = infoTributaria.find('claveAcceso').text
                        l10n_latam_document_number = infoTributaria.find('estab').text + "-" + infoTributaria.find('ptoEmi').text + "-" + infoTributaria.find('secuencial').text

                        # Buscar si hay retenciones ingresadas
                        exists_retentions = self.env['account.withhold'].search([('transaction_type', '=', 'sale'), ('electronic_authorization', '=', electronic_authorization)])
                        if len(exists_retentions) > 0:
                            raise UserError(_("La Retención ya se encuentra ingresada!!"))

                        retention_wizard_object = self.env['account.withhold.wizard']
                        impuestos_invoice_lines = []
                        impuestos_credit_card_lines = []

                        impuestos = xml_data.findall("impuestos")[0] if xml_data.findall("impuestos") else []
                        if len(impuestos)!=0:
                            for impuesto in impuestos:
                                if impuesto.find('numDocSustento') != None:
                                    retention_invoice = True
                                    number_invoice = impuesto.find('numDocSustento').text
                                    number_invoice = str(number_invoice[:3]) + "-" + number_invoice[3:6] + "-" + number_invoice[6:]
                                    invoice = self.env['account.move'].search([('move_type', '=', 'out_invoice'), ('l10n_latam_document_number', '=', number_invoice)])
                                    if len(invoice) > 0:
                                        if impuesto.find('codigo').text == '1':
                                            description = 'retencion_renta'
                                            tax_id = self.env['account.tax'].search(
                                                [('description', '=', impuesto.find('codigoRetencion').text),
                                                 ('type_ec', '=', 'retencion_renta')])
                                        else:
                                            description = 'retencion_iva'
                                            amount = 0.00
                                            if float(impuesto.find('porcentajeRetener').text) == 30.00:
                                                amount = -3.6000
                                            if float(impuesto.find('porcentajeRetener').text) == 70.00:
                                                amount = -3.6000
                                            if float(impuesto.find('porcentajeRetener').text) == 100.00:
                                                amount = -3.6000
                                            tax_id = self.env['account.tax'].search(
                                                [('amount', '=', amount), ('type_ec', '=', 'retencion_iva')])

                                        impuestos_invoice_lines.append((0, 0, {'description': description,
                                                                               'tax_id': tax_id[0].id if len(tax_id) > 0 else False,
                                                                               'tax_base': float(impuesto.find('baseImponible').text),
                                                                               'retention_percentage': float(impuesto.find('porcentajeRetener').text)}))
                                    else:
                                        raise UserError(_("La Factura no se encuentra ingresada en el sistema!!"))
                                else:
                                    # REVISAR LOS CODIGOS DE IMPUESTOS
                                    retention_credit_card = True
                                    if impuesto.find('codigo').text == '1':
                                        description = 'retencion_renta'
                                        tax_id = self.env['account.tax'].search([('l10n_ec_code_ats', '=', impuesto.find('codigoRetencion').text),('tax_group_id.l10n_ec_type', '=', 'withhold_income_tax')])
                                    else:
                                        description = 'retencion_iva'
                                        amount = 0.00
                                        cod_ret = None
                                        if float(impuesto.find('porcentajeRetener').text) == 20.00:
                                            # amount = -3.6000
                                            cod_ret = '609'
                                        if float(impuesto.find('porcentajeRetener').text) == 30.00:
                                            # amount = -3.6000
                                            cod_ret = '609'
                                        if float(impuesto.find('porcentajeRetener').text) == 70.00:
                                            # amount = -3.6000
                                            cod_ret = '609'
                                        if float(impuesto.find('porcentajeRetener').text) == 100.00:
                                            # amount = -3.6000
                                            cod_ret = '609'
                                        tax_id = self.env['account.tax'].search([('l10n_ec_code_ats', '=', cod_ret), ('tax_group_id.l10n_ec_type', '=', 'withhold_vat')])
                                    impuestos_credit_card_lines.append((0, 0, {'description': description,
                                                                               'tax_id': tax_id[0].id if len(tax_id) > 0 else False,
                                                                               'tax_base': float(impuesto.find('baseImponible').text),
                                                                               'retention_percentage_manual': float(impuesto.find('porcentajeRetener').text),
                                                                               'retained_value_manual': float(impuesto.find('valorRetenido').text)}))
                        else:
                            docSustento = xml_data.find("docsSustento")
                            for doc_sustento in docSustento:
                                retenciones = doc_sustento.findall("retenciones")
                                if len(retenciones)!=0:
                                    for retencion in retenciones:
                                        retention_invoice = True
                                        number_invoice = doc_sustento.find('numDocSustento').text
                                        number_invoice = str(number_invoice[:3]) + "-" + number_invoice[3:6] + "-" + number_invoice[6:]
                                        invoice = self.env['account.move'].search([('move_type', '=', 'out_invoice'), ('l10n_latam_document_number', '=', number_invoice)])
                                        if len(invoice) > 0:
                                            if retencion.find('codigo').text == '1':
                                                description = 'retencion_renta'
                                                tax_id = self.env['account.tax'].search([('description', '=', retencion.find('codigoRetencion').text),('type_ec', '=', 'retencion_renta')])
                                            else:
                                                description = 'retencion_iva'
                                                amount = 0.00
                                                if float(retencion.find('porcentajeRetener').text) == 30.00:
                                                    amount = -3.6000
                                                if float(retencion.find('porcentajeRetener').text) == 70.00:
                                                    amount = -3.6000
                                                if float(retencion.find('porcentajeRetener').text) == 100.00:
                                                    amount = -3.6000
                                                tax_id = self.env['account.tax'].search([('amount', '=', amount), ('type_ec', '=', 'retencion_iva')])
                                            impuestos_invoice_lines.append((0, 0, {'description': description,
                                                                                   'tax_id': tax_id[0].id if len(tax_id) > 0 else False,
                                                                                   'tax_base': float(retencion.find('baseImponible').text),
                                                                                   'retention_percentage': float(retencion.find('porcentajeRetener').text)}))
                                        else:
                                            raise UserError(
                                                _("La Factura no se encuentra ingresada en el sistema!!"))
                                    # else:
                                    #     # REVISAR LOS CODIGOS DE IMPUESTOS
                                    #     retention_credit_card = True
                                    #     if impuesto.find('codigo').text == '1':
                                    #         description = 'retencion_renta'
                                    #         tax_id = self.env['account.tax'].search(
                                    #             [('l10n_ec_code_ats', '=', impuesto.find('codigoRetencion').text),
                                    #              ('tax_group_id.l10n_ec_type', '=', 'withhold_income_tax')])
                                    #     else:
                                    #         description = 'retencion_iva'
                                    #         amount = 0.00
                                    #         cod_ret = None
                                    #         if float(impuesto.find('porcentajeRetener').text) == 20.00:
                                    #             # amount = -3.6000
                                    #             cod_ret = '609'
                                    #         if float(impuesto.find('porcentajeRetener').text) == 30.00:
                                    #             # amount = -3.6000
                                    #             cod_ret = '609'
                                    #         if float(impuesto.find('porcentajeRetener').text) == 70.00:
                                    #             # amount = -3.6000
                                    #             cod_ret = '609'
                                    #         if float(impuesto.find('porcentajeRetener').text) == 100.00:
                                    #             # amount = -3.6000
                                    #             cod_ret = '609'
                                    #         tax_id = self.env['account.tax'].search(
                                    #             [('l10n_ec_code_ats', '=', cod_ret), (
                                    #                 'tax_group_id.l10n_ec_type', '=', 'withhold_vat')])
                                    #     impuestos_credit_card_lines.append((0, 0, {'description': description,
                                    #                                                'tax_id': tax_id[0].id if len(
                                    #                                                    tax_id) > 0 else False,
                                    #                                                'tax_base': float(
                                    #                                                    impuesto.find(
                                    #                                                        'baseImponible').text),
                                    #                                                'retention_percentage_manual': float(
                                    #                                                    impuesto.find(
                                    #                                                        'porcentajeRetener').text),
                                    #                                                'retained_value_manual': float(
                                    #                                                    impuesto.find(
                                    #                                                        'valorRetenido').text)}))


                        if retention_invoice:
                            ruc = infoTributaria.find('ruc').text
                            partner = self.env['res.partner'].search([('vat', '=', ruc)])
                            if len(partner) > 0:
                                date_retention = (infoCompRetencion.find('fechaEmision').text).split("/")
                                date_retention = date_retention[2] + "-" + date_retention[1] + "-" + date_retention[0]
                                retention = retention_wizard_object.create(
                                    {'document_number': l10n_latam_document_number,
                                     'partner_id': partner[0].id,
                                     'creation_date': date_retention,
                                     'invoice_id': invoice[0].id,
                                     'document_type': 'electronic',
                                     'transaction_type': 'sale',
                                     'electronic_authorization': electronic_authorization, })
                                retention.write({'lines_ids': impuestos_invoice_lines})
                                retention.approve_now()
                                invoices += invoice

                        if retention_credit_card:
                            ruc = infoTributaria.find('ruc').text
                            partner = self.env['res.partner'].search([('vat', '=', ruc)])
                            if len(partner) > 0:
                                date_retention = (infoCompRetencion.find('fechaEmision').text).split("/")
                                date_retention = date_retention[2] + "-" + date_retention[1] + "-" + date_retention[0]
                                # import pdb
                                # pdb.set_trace()
                                new_retention_credit_card = self.env['account.withhold'].create(
                                    {'transaction_type': 'sale',
                                     'tarjeta_credito': True,
                                     'multiple': True,
                                     'document_type': 'electronic',
                                     'partner_multi_id': partner[0].id,
                                     'creation_date': date_retention,
                                     'electronic_authorization': electronic_authorization,
                                     'l10n_latam_document_number': l10n_latam_document_number,
                                     'document_number': l10n_latam_document_number, })
                                # import pdb
                                # pdb.set_trace()
                                new_retention_credit_card.write({'retention_line_ids': impuestos_credit_card_lines})
                                # for line in new_retention_credit_card.retention_line_ids:
                                #     line.onchange_amount_data()
                                new_retention_credit_card._compute_amount()

        if len(invoices)!=0:
            action_vals = {
                'name': _('Generated Documents'),
                'res_model': 'account.move',
                'type': 'ir.actions.act_window',
                'context': self._context
            }
            if len(invoices) == 1:
                action_vals.update({
                    'views': [[False, "form"]],
                    'view_mode': 'form',
                    'res_id': invoices[0].id,
                })
            else:
                action_vals.update({
                    'views': [[False, "tree"], [False, "form"]],
                    'view_mode': 'tree, form',
                })
            return action_vals