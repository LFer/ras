# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details

from odoo import api, fields, models
from odoo.addons import decimal_precision as dp
import ipdb
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning
# Proveedores por Product Line
class rt_service_product_supplier(models.Model):
    _name = 'rt.service.product.supplier'
    _description = "Proveedores del Servicio"
    _order = "id DESC"
    _rec_name = 'supplier_id'

    @api.multi
    def generar_oc(self):
        vals = {}
        vals['name'] = self.env['ir.sequence'].next_by_code('cost.sequence')
        vals['state'] = 'oc'
        return self.write(vals)

    @api.multi
    def do_sync(self):
        print('just a test!')
        return True

    @api.multi
    def button_delete_invoice_id(self):
        for rec in self:
            rec.write({'invoice_id': False})
        return True

    @api.one
    @api.depends('rt_service_product_id.rt_service_id')
    def _get_service(self):
        if self.rt_service_product_id:
            self.rt_service_id = self.rt_service_product_id.rt_service_id.id
        return

    # @api.one
    # @api.depends('rt_service_product_id.rt_service_id','supplier_id')
    # def _get_service_state(self):
    #     if self.rt_service_product_id and self.rt_service_product_id.rt_service_id:
    #         self.service_state = self.rt_service_product_id.rt_service_id.state
    #     return

    # @api.one
    # @api.depends('rt_service_product_id.rt_service_id', 'supplier_id')
    # def get_service_date(self):
    #     if self.rt_service_id and self.rt_service_id.start_datetime:
    #         self.service_date = self.rt_service_id.start_datetime
    #     return

    @api.one
    @api.depends('rt_service_product_id.rt_service_id', 'invoice_id')
    def _get_invoice_number(self):
        # if self.invoice_id:
        #     self.supplier_invoice_number = self.invoice_id.supplier_invoice_number
        return

    @api.one
    @api.depends('rt_service_product_id.rt_service_id', 'supplier_id')
    def _get_origin(self):
        # if self.rt_service_product_id and self.rt_service_product_id.travel_section_ids:
        #     for s in self.rt_service_product_id.travel_section_ids:
        #         if s.action_type == 'retreat':
        #             self.origin = s.place_id.id
        return

    @api.one
    @api.depends('rt_service_product_id.rt_service_id','supplier_id')
    def _get_destination(self):
        # if self.rt_service_product_id and self.rt_service_product_id.travel_section_ids:
        #     for s in self.rt_service_product_id.travel_section_ids:
        #         if s.action_type == 'delivery':
        #             self.destination = s.place_id.id
        return

    @api.one
    @api.depends('rt_service_product_id.rt_service_id','supplier_id')
    def _get_output_reference(self):
        # if self.rt_service_product_id and self.rt_service_product_id.rt_service_id and self.rt_service_product_id.rt_service_id.output_reference:
        #     self.output_reference = self.rt_service_product_id.rt_service_id.output_reference
        return

    @api.one
    @api.depends('price_subtotal')
    def _compute_amount(self):
        tax = self.tax_ids if self.tax_ids else 0
        if not tax:
            self.price_subtotal = self.amount
        else:
            self.price_subtotal = self.amount * (1 + tax.amount / 100)

    state = fields.Selection([('draft', 'Borrador'),('oc', 'Confirmado')], string='Estado', index=True, readonly=True, default='draft', track_visibility='onchange', copy=False)
    ref = fields.Char(string='Carpeta Relacionada')
    name = fields.Char(string='Orden de Pago')
    #Producto
    product_id = fields.Many2one('product.product', 'Producto', ondelete="cascade")
    #Cliente a Facturar
    partner_invoice_id = fields.Many2one(comodel_name='res.partner', string='Cliente a facturar',domain=[('customer', '=', True)])
    #Product Line ID
    rt_service_product_id = fields.Many2one(comodel_name='rt.service.productos', string='Producto Asociado', ondelete='cascade')
    #Service
    rt_service_id = fields.Many2one(comodel_name='rt.service', string='Carpeta Asociada', store=True, readonly=True, compute='_get_service')
    #Estado Servicio
    service_state = fields.Selection([
        ('draft', 'Borrador'),
        ('confirm', 'Confirmado'),
        ('inprocess', 'En proceso'),
        ('progress', 'Servicio Facturado'),
        ('cancel', 'Cancelado'),
        ('done', 'Realizado'),
        ('invoiced', 'Factura Borrador'),
        ('invoice_rejected', 'Fac. Rechazada'),
        ('rejected', 'Factura Rechazada'),
        ('partially_invoiced', 'Parc. Facturado'),
        ('totally_invoiced', 'Comp. Facturado'),
    ], string='Estado de la Carpeta')
    #Proveedor
    supplier_id = fields.Many2one('res.partner', 'Supplier', domain=[('is_company', '=', True), ('supplier', '=', True)], required=True)
    #Factura Proveedor
    invoice_id = fields.Many2one('account.invoice', 'Supplier invoice', domain=[('type', '=', 'in_invoice'), ('state', 'in', ['draft', 'open', 'paid'])])
    #Moneda
    currency_id = fields.Many2one('res.currency', 'Currency')
    #Impuestos
    tax_ids = fields.Many2many('account.tax', 'rt_service_product_supplier_tax_rel', 'supplier_line_id', 'tax_id', 'Taxes', domain=[('type_tax_use', '=', 'purchase')], copy=True)
    #Remito
    sender = fields.Char('Sender', size=32)
    #Importe
    amount = fields.Float('Amount')
    #Precio con impuestos (dice subtotal pero en realidad es el total)
    price_subtotal = fields.Float(string='Total', digits=dp.get_precision('Account'), readonly=True, compute='_compute_amount')
    #Fecha de servicio
    service_date = fields.Datetime('Service Date', store=True, readonly=True)#, compute='get_service_date')
    #Contenedor
    tack_id = fields.Char('Tack', size=32, store=True, readonly=True)
    #Origen
    origin = fields.Many2one('stock.warehouse', 'Origin', store=True, readonly=True)#, compute='_get_origin')
    #Destino
    destination = fields.Many2one('stock.warehouse', 'Destination', store=True, readonly=True)#, compute='_get_destination')
    #Numero Factura
    supplier_invoice_number = fields.Char('Supplier Invoice Number', store=True, readonly=True, compute='_get_invoice_number')
    #DUA
    dua = fields.Char('DUA', store=True, readonly=True)
    #MIC
    mic = fields.Char('MIC', store=True, readonly=True)#, compute='_get_mic')
    #CRT
    crt = fields.Char('CRT', store=True, readonly=True)#, compute='_get_crt')
    #Referencia de salida
    output_reference = fields.Char('Referencia de Salida', store=True, readonly=True)#, compute='_get_output_reference')
    origin_id = fields.Many2one(comodel_name='res.partner.address.ext', string='Origen')
    destiny_id = fields.Many2one(comodel_name='res.partner.address.ext', string='Destino')


    @api.onchange('amount')
    def onchange_amount(self):
        for rec in self:
            iva = (100 + rec.tax_ids.amount if rec.tax_ids else 0) / 100
            if rec.amount:
                rec.price_subtotal = rec.amount * iva

    @api.multi
    def update_amount(self):
        nueva_linea = self.copy()
        return True
