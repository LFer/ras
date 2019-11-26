# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details

from odoo import api, fields, models
import ipdb
from stdnum import iso6346
import datetime

class marfig_template(models.Model):
    _name = "marfrig.template"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _description = "Plantilla Operativa Marfrig"
    _order = "id DESC"

    name = fields.Char(default='Borrador')
    company_id = fields.Many2one('res.company', string='Compañia', default=lambda self: self.env.user.company_id)
    partner_invoice_id = fields.Many2one(comodel_name='res.partner', string='Cliente')#, compute='_compute_marfrig_name')
    pricelist_id = fields.Many2one('product.pricelist.item', string='Tarifa')
    currency_id = fields.Many2one(comodel_name="res.currency", string="Moneda", related="pricelist_id.currency_id", index=True, readonly=True, store=True)
    start_datetime = fields.Datetime(string='Fecha Inicio', required=True, index=True, copy=False, default=fields.datetime.now())
    stop_datetime = fields.Datetime('Fecha Fin', index=True, copy=False)
    output_reference = fields.Text('Referencia de Salida', size=16)
    mrf_srv_tmlp_ids = fields.One2many('marfrig.template.service.products', 'mrf_srv_tmpl_id', string='Servicios', copy=True)
    aduana_destino_id = fields.Many2one('fronteras', 'Aduana Destino')
    importe = fields.Float(string='Valor de Venta', store=True)
    terminal_ingreso_cargado = fields.Many2one(comodel_name='res.partner.address.ext', string=u'Terminal de Ingreso Cargado', ondelete='restrict')
    libre_devolucion = fields.Datetime(string='Libre de Devolución')
    booking = fields.Char('Booking', size=32)
    currency_id_vendedor = fields.Many2one(comodel_name='res.currency', string='Moneda')
    currency_id_chofer = fields.Many2one(comodel_name='res.currency', string='Moneda Comisión Chofer')
    driver_commission = fields.Float('Comisión de chofer')
    partner_seller_id = fields.Many2one(comodel_name='res.partner', string='Vendedor', domain=[('seller', '=', True)])
    seller_commission = fields.Float(string='Comisión Vendedor')
    product_type = fields.Selection([('propio', 'Propio'), ('terceros', 'Terceros')], string='Origen del Servicio')

    @api.depends('partner_invoice_id')
    def _compute_marfrig_name(self):
        cliente_obj = self.env['res.partner']
        cliente = cliente_obj.search([('name', 'ilike', 'Marfrig')])
        self.partner_invoice_id = cliente.id

    @api.onchange('partner_invoice_id', 'pricelist_id')
    def onchange_partner_invoice_id(self):
        domain = {}
        warning = {}
        res = {}
        tarifa_obj = self.env['product.pricelist.item']
        tarifa = tarifa_obj.search([('es_marfrig', '=', True)]).ids
        domain = {'pricelist_id': [('id', 'in', tarifa)]}

        if self.pricelist_id:
            self.importe = self.pricelist_id.sale_price
            self.driver_commission = self.pricelist_id.comision_chofer
            self.seller_commission = self.pricelist_id.comision_vendedor

        if warning:
            res['warning'] = warning
        if domain:
            res['domain'] = domain
        return res




class marfig_template_serivice_products(models.Model):
    _name = "marfrig.template.service.products"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _description = "Plantilla Servicios Marfrig"
    _order = "id ASC"


    name = fields.Char()
    mrf_srv_tmpl_id = fields.Many2one(comodel_name='marfrig.template', string='Servicios')
    sequence = fields.Integer()
    product_id = fields.Many2one(comodel_name='product.product', string='Servicio', domain=[('product_tmpl_id.type', '=', 'service'), ('sale_ok', '=', True)], required=False, change_default=True, ondelete='restrict')
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('confirm', 'Confirmado'),
        ('inprocess', 'En proceso'),
        ('cancel', 'Cancelado'),
        ('done', 'Realizado'),
    ], string='Status', index=True, readonly=True, default='draft',
        track_visibility='onchange', copy=False,
    )
    product_type = fields.Selection([('propio', 'Propio'), ('terceros', 'Terceros')],string='Origen del Servicio')
    planta_id = fields.Many2one(comodel_name='res.partner', string='Planta')
    action_type_id = fields.Many2one('tipo.accion', string="Tipo de Acción")
    supplier_id = fields.Many2one(comodel_name='res.partner', string='Proveedor', domain=[('supplier', '=', True), ('freighter', '=', True)])
    importe = fields.Float(string='Valor de Venta', store=True)
    valor_compra_currency_id = fields.Many2one(comodel_name='res.currency', string='Moneda Compra')
    valor_compra = fields.Monetary(string='Valor Compra', currency_field='valor_compra_currency_id')
    currency_id = fields.Many2one(comodel_name='res.currency', string='Moneda')
    currency_id_vendedor = fields.Many2one(comodel_name='res.currency', string='Moneda')
    currency_id_chofer = fields.Many2one(comodel_name='res.currency', string='Moneda Comisión Chofer')
    driver_commission = fields.Float('Comisión de chofer')
    partner_seller_id = fields.Many2one(comodel_name='res.partner', string='Vendedor', domain=[('seller', '=', True)],readonly=True)
    seller_commission = fields.Float(string='Comisión Vendedor')
    origin_id = fields.Many2one(comodel_name='res.partner.address.ext', string='Origen')
    destiny_id = fields.Many2one(comodel_name='res.partner.address.ext', string='Destino')
    hora_llegada = fields.Datetime(string='Hora Llegada')
    hora_salida = fields.Datetime(string='Hora Salida')
    kg_planta = fields.Float(string='Kg')
    start = fields.Datetime('Inicio', help="Start date of an event, without time for full days events",default=datetime.datetime.now())
    stop = fields.Datetime('Stop', help="Stop date of an event, without time for full days events", default=datetime.datetime.now())
    aduana_destino_id = fields.Many2one('fronteras', 'Aduana Destino')

    # @api.onchange('vehicle_id')
    # def onchange_vehicle_id(self):
    #     for rec in self:
    #         if not rec.vehicle_id:
    #             return
    #         rec.driver_id = rec.vehicle_id.driver_id.id
    #
    # @api.onchange('matricula_fletero')
    # def onchange_vehicle_id(self):
    #     for rec in self:
    #         if not rec.matricula_fletero:
    #             return
    #         rec.chofer = rec.matricula_fletero.chofer

    @api.onchange('product_type')
    def _onchange_product_type(self):
        self.product_type = self.mrf_srv_tmpl_id.product_type
