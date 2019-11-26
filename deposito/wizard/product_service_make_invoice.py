# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError, Warning
import ipdb
from odoo.addons import decimal_precision as dp

class DepositoMakeInvoice(models.TransientModel):
    _name = 'deposito.make.invoice'
    _description = 'Deposito Crear Factura'

    def cargar_campos_impresion(self, partner, invoice):
        invoice.print_output_reference = partner.print_output_reference
        invoice.print_origin_destiny_grouped = partner.print_origin_destiny_grouped
        invoice.print_cont_grouped = partner.print_cont_grouped
        invoice.print_product_grouped = partner.print_product_grouped
        invoice.print_invoice_load = partner.print_invoice_load
        invoice.print_invoice_product = partner.print_invoice_product
        invoice.print_date_start = partner.print_date_start
        invoice.print_ms_in_out = partner.print_ms_in_out
        invoice.print_mic = partner.print_mic
        invoice.print_crt = partner.print_crt
        invoice.print_consignee = partner.print_consignee
        invoice.print_purchase_order = partner.print_purchase_order
        invoice.print_origin_destiny = partner.print_origin_destiny
        invoice.print_container_number = partner.print_container_number
        invoice.print_container_size = partner.print_container_size
        invoice.print_booking = partner.print_booking
        invoice.print_gex = partner.print_gex
        invoice.print_sender = partner.print_sender
        invoice.print_dua = partner.print_dua
        invoice.print_packages = partner.print_packages
        invoice.print_kg = partner.print_kg
        invoice.print_volume = partner.print_volume
        invoice.print_extra_info = partner.print_extra_info
        invoice.show_extra_info = partner.show_extra_info

    def calcular_diario(self, partner_id):
        journal_obj = self.env['account.journal']
        if partner_id.vat_type == '2' and partner_id.country_id.code == 'UY':
            # e-Factura
            journal_id = journal_obj.search([('code', '=', 'EF')]).id
        if (partner_id.vat_type == '4' and partner_id.country_id.code != 'UY') or partner_id.vat_type == '3':
            # e-Ticket
            journal_id = journal_obj.search([('code', '=', 'ET')]).id

        return journal_id

    def generar_costos(self, products=None):
        cost_obj = self.env['rt.service.product.supplier']
        tax_obj = self.env['account.tax']

        if not products:
            return
        for prod in products:
            taxes = tax_obj.search([('name', '=', 'IVA Directo Op  Grav B')])
            if prod.product_id.name == 'Alquiler':
                taxes = tax_obj.search([('name', '=', 'Compras Exentos IVA')])
            if prod.product_type == 'terceros' and prod.is_outgoing:
                if prod.supplier_id:
                    if prod.valor_compra:
                        if prod.valor_compra_currency_id:
                            if prod.supplier_ids:
                                #vamos a borrar los costos
                                for prd in prod.supplier_ids:
                                    if not prd.invoice_id:
                                        prd.unlink()
                            line_dict = {}
                            line_dict['deposito_id'] = prod.deposito_srv_id.id
                            line_dict['supplier_id'] = prod.supplier_id.id
                            line_dict['currency_id'] = prod.valor_compra_currency_id.id
                            line_dict['amount'] = prod.valor_compra
                            if prod.product_id.name == 'Alquiler':
                                line_dict['price_subtotal'] = prod.valor_compra
                            else:
                                line_dict['price_subtotal'] = prod.valor_compra * 1.22
                            line_dict['ref'] = prod.deposito_srv_id.referencia
                            line_dict['rt_service_id'] = False
                            line_dict['rt_consol_product_id'] = False
                            line_dict['rt_marfrig_product_id'] = False
                            line_dict['rt_deposito_product_id'] = prod.id
                            line_dict['service_state'] = prod.state
                            line_dict['tax_ids'] = [(6, 0, taxes.ids)]
                            line_dict['service_date'] = prod.start
                            line_dict['origin_id'] = prod.origin_id.id
                            line_dict['destiny_id'] = prod.destiny_id.id
                            line_dict['product_id'] = prod.product_id.id
                            line_dict['output_reference'] = prod.name
                            line_dict['partner_invoice_id'] = prod.deposito_srv_id.partner_invoice_id.id
                            result = cost_obj.create(line_dict)

    @api.multi
    def make_invoices(self):
        inv_obj = self.env['account.invoice']
        if not self._context.get('active_ids'):
            return {'type': 'ir.actions.act_window_close'}
        product_service = self.env['deposito.service.products'].browse(self._context.get('active_ids'))
        self.generar_costos(products=product_service)
        tax_obj = self.env['account.tax']
        account_obj = self.env['account.account']
        operation_taxes = {
                           'exento': False,
                           'asimilado': tax_obj.search([('name', '=', 'IVA Venta asimilado a exportación')]),
                           'gravado': tax_obj.search([('name', '=', 'IVA Ventas (22%)')])
        }
        lineas = []
        for line in product_service:
            taxes = operation_taxes['gravado']
            account = account_obj.search([('code', '=', '41021001')])
            line_dict = {}
            line_dict['name'] = line.name
            line_dict['account_id'] = account.id
            line_dict['price_unit'] = line.importe
            line_dict['uom_id'] = line.product_id.uom_id.id
            line_dict['product_deposito_srv_id'] = line.id
            line_dict['product_id'] = line.product_id.id
            line_dict['invoice_line_tax_ids'] = [(6, 0, taxes.ids)]
            lineas.append((0, 0, line_dict))
            #Facturado
            line.invoiced = True
            line.deposito_srv_id.state = 'invoiced'

        journal_id = self.calcular_diario(line.partner_invoice_id)

        invoice = inv_obj.create({
            'name': line.partner_invoice_id.name or '',
            'origin': line.name,
            'type': 'out_invoice',
            'account_id': line.partner_invoice_id.property_account_receivable_id.id,
            'partner_id': line.partner_invoice_id.id,
            'journal_id': journal_id,
            'currency_id': line.currency_id.id,
            'fiscal_position_id': line.partner_invoice_id.property_account_position_id.id,
            'company_id': line.deposito_srv_id.company_id.id,
            'user_id': line.deposito_srv_id.user_id.id,
            'deposito_operation_id': line.deposito_srv_id.id,
            'invoice_line_ids': lineas
        })

        # line.invoices_ids += invoice
        # line.deposito_srv_id.invoices_ids

        partner = line.partner_invoice_id
        self.cargar_campos_impresion(partner, invoice)

        if self._context['open_invoices']:
            return {
                'domain': [('id', 'in', invoice.ids)],
                'name': 'Invoices',
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'account.invoice',
                'view_id': False,
                'views': [(self.env.ref('account.invoice_tree').id, 'tree'),
                          (self.env.ref('account.invoice_form').id, 'form')],
                'context': "{'type':'out_invoice'}",
                'type': 'ir.actions.act_window'
            }
        else:
            return {'type': 'ir.actions.act_window_close'}


