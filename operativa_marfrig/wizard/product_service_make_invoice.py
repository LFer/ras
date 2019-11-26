# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError, Warning
import ipdb
from odoo.addons import decimal_precision as dp

class MakeInvoice(models.TransientModel):
    _name = 'marfrig.service.product.make.invoice'
    _description = 'Create Mass Invoice (repair)'



    @api.multi
    def actualiza_estado_calendario(self, carpeta=None, estado=None):
        estados_obj = self.env['color.picker']
        calendario_obj = self.env['servicio.calendario']

        realizada_facturada = estados_obj.search([('name', '=', 'Carga Realizada y Facturada')])
        factura_rechazada = estados_obj.search([('name', '=', 'Factura Rechazada')])
        if carpeta:
            calendarios = calendario_obj.search([('marfrig_id', '=', carpeta.id)])
            for calendario in calendarios:
                if estado == 'Facturado':
                    calendario.color_pickier_id = realizada_facturada.id






    def cargar_campos_impresion(self, partner, invoice):
        invoice.print_output_reference = partner.print_output_reference
        invoice.print_origin_destiny_grouped = partner.print_origin_destiny_grouped
        invoice.print_cont_grouped = partner.print_cont_grouped
        invoice.print_product_grouped = partner.print_product_grouped
        invoice.print_invoice_load = partner.print_invoice_load
        invoice.print_invoice_product = partner.print_invoice_product
        invoice.print_date_start = partner.print_date_start
        invoice.print_ms_in_out = partner.print_ms_in_out
        invoice.print_delivery_order = partner.print_delivery_order
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

    def calcular_delivery_order(self, productos):
        delivery_order = ''
        carga_anterior = 0
        for prod in productos:
            if prod.rt_carga_id:
                carga = prod.rt_carga_id
                if carga.id != carga_anterior and carga.delivery_order:
                    delivery_order += carga.delivery_order + '\n'
                carga_anterior = carga.id
        return delivery_order


    @api.multi
    def make_invoices(self):
        invoices_created = self.env['account.invoice']
        product_service = self.env['marfrig.service.products'].browse(self._context.get('active_ids'))
        for srv in product_service:
            invoice = srv.mrf_srv_id.crea_factura(linea_planta=srv, importe=srv.importe_linea, producto_id=srv.product_id)
            srv.mrf_srv_id.invoices_ids += invoice
            invoices_created += invoice
            srv.mrf_srv_id.state = 'invoiced'
            partner = srv.planta_id
            self.cargar_campos_impresion(partner, invoice)
            self.actualiza_estado_calendario(carpeta=srv.mrf_srv_id, estado='Facturado')



        if self._context['open_invoices']:
            return {
                'domain': [('id', 'in', invoices_created.ids)],
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


