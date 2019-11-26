# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details
from itertools import cycle

from odoo import api, fields, models
import ipdb
from stdnum import iso6346
import datetime
from collections import defaultdict
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning
from odoo.tools import float_round, float_repr, DEFAULT_SERVER_TIME_FORMAT

class marfrig_serivice_products(models.Model):
    _name = "marfrig.service.products"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _description = "Servicios Marfrig"
    _order = "id ASC"


    name = fields.Char()
    mrf_srv_id = fields.Many2one(comodel_name='marfrig.service.base', string='Servicios')
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

    planta_id = fields.Many2one(comodel_name='res.partner', string='Planta')
    action_type_id = fields.Many2one('tipo.accion', string="Tipo de Acción")
    origin_id = fields.Many2one(comodel_name='res.partner.address.ext', string='Origen')
    destiny_id = fields.Many2one(comodel_name='res.partner.address.ext', string='Destino')
    hora_llegada = fields.Datetime(string='Hora Llegada')
    hora_salida = fields.Datetime(string='Hora Salida')
    kg_planta = fields.Float(string='Kg Cargados')
    remito = fields.Char(string='Remito')
    currency_id_chofer = fields.Many2one(comodel_name='res.currency', string='Moneda Comisión Chofer')
    driver_commission = fields.Float('Comisión de chofer')
    matricula = fields.Char(string=u'Matricula')
    matricula_dos_id = fields.Many2one(comodel_name='fleet.vehicle', string=u'Matrícula dos')
    vehicle_id = fields.Many2one(comodel_name='fleet.vehicle', string=u'Matrícula', domain=[('is_ras_property', '=', True)])
    vehicle_type = fields.Selection(related='vehicle_id.vehicle_type', type='char', readonly=True)
    driver_id = fields.Many2one('hr.employee', 'Chofer', help=u'Chofer del Vehículo')
    chofer = fields.Char('Chofer')
    matricula_dos_fletero = fields.Char(string='Matricula Dos Fletero')
    matricula_fletero = fields.Many2one(comodel_name='fleet.vehicle', string='Matricula Fletero', domain=[('is_ras_property', '=', False)])
    product_type = fields.Selection([('propio', 'Propio'), ('terceros', 'Terceros')], string='Origen del Servicio')
    attachment_kg_planta = fields.Many2many('ir.attachment')
    attachment_remito = fields.Many2many('ir.attachment')
    hora_solicitada = fields.Datetime(string='Hora Solicitada', help='Hora de arribo solicitada por cliente')
    aduana_destino_id = fields.Many2one('fronteras', 'Aduana Destino')
    currency_id = fields.Many2one(comodel_name='res.currency', default=46, string=' ')
    importe_linea = fields.Float(string='Importe')
    hora_espera = fields.Boolean(string='Hora Espera')
    es_retiro_vacio = fields.Boolean(string='Es Retiro de Vacio')
    flete_viaje = fields.Boolean(string='Es Flete y Viaje')
    es_ingreso_puerto = fields.Boolean(string='Es Ingreso a Puerto')
    kg_symbol = fields.Many2one(comodel_name='res.currency', compute='_get_kg_symbol')
    is_invoiced = fields.Boolean('Facturable', help='Marque esta casilla si este servicio no se factura', default=True)
    invoice_id = fields.Many2one('account.invoice')
    invoiced_rejected = fields.Boolean()
    invoiced = fields.Boolean()
    cantidad_hora_espera = fields.Float(string='Cantidad de Horas de Espera')
    supplier_id = fields.Many2one(comodel_name='res.partner', string='Proveedor', domain=[('supplier', '=', True), ('freighter', '=', True)])
    valor_compra_currency_id = fields.Many2one(comodel_name='res.currency', string='Moneda Compra')
    valor_compra = fields.Monetary(string='Valor Compra', currency_field='valor_compra_currency_id')
    supplier_ids = fields.One2many('rt.service.product.supplier', 'rt_marfrig_product_id', 'Proveedores', copy=False)
    alquilado = fields.Boolean(string='Alquilado', help='Marque esta casilla si la matricula es alquilada pero el chofer es de la Empresa')
    start = fields.Datetime('Inicio', required=True)
    stop = fields.Datetime('Fin', required=True)
    purchase_number = fields.Char(string='Orden de Compra')

    @api.multi
    def reject_service(self):
        for rec in self:
            rec.invoiced_rejected = True
            rec.mrf_srv_id.state = 'invoice_rejected'

    @api.onchange('driver_commission')
    def carga_linea_comision(self):
        for rec in self:
            if rec.driver_commission:
                self.genera_comision_chofer(linea=rec, chofer=rec.driver_id)

    def genera_comision_chofer(self, linea, chofer):
        """
        Se generan comisiones si se cumple la siguiente casuistica:
        Chofer Pertenece a categoria 'Camion Grande' A3
        Producto = Flete
        Tipo de Accion = Viaje, Retiro de Vacío, Ingreso Cargado, Devolución de Vacío, Retiro de Cargado
        PARA CHOFERES DE CATEGORIA A2 (CAMION CHICO) LA COMISION ES EVENTUAL - NORMALMENTE NO CORRESPONDE
        :return:
        """
        print('-------------------------entro a la funcion genera_comision_chofer---------------------------------')
        flete = 'Flete'
        hr_job_obj = self.env['hr.job']
        action_type_obj = self.env['tipo.accion']
        categoria_corresponde_comision = hr_job_obj.search(
            [('x_studio_categora_mtss', '=', 'A3 - Chofer de semirremolque')])
        categoria_comision_opcional = hr_job_obj.search(
            [('x_studio_categora_mtss', '=', 'A2 - Chofer de Camión y Camioneta')])
        tipo_accion_corresponde_comision = action_type_obj.search([('corresponde_comision', '=', True)])
        if chofer.job_id.id in categoria_corresponde_comision.ids and linea.product_id.name == flete and linea.action_type_id.id in tipo_accion_corresponde_comision.ids:
            # Corresponde crear la comision
            linea.add_driver_commission()
        elif linea.alquilado:
                linea.add_driver_commission()

    def get_tack_id(self):
        if self.mrf_srv_id.container_number:
            return self.mrf_srv_id.container_number
        else:
            return ' '

    def get_dua(self):
        dua = ''
        carga = self.mrf_srv_id
        if carga.dua_aduana:
            dua = carga.dua_aduana + '-' if carga.dua_aduana else ''
            dua += carga.dua_anio + '-' if carga.dua_anio else ''
            dua += carga.dua_numero if carga.dua_numero else ''
        else:
            dua = ' '
        return dua


    def _get_kg_symbol(self):
        curr_obj = self.env['res.currency']
        kg_symbol = curr_obj.search([('name', 'ilike', 'Kg')])
        if not kg_symbol:
            kg_symbol = curr_obj.create({'name': 'Kg', 'symbol': 'Kg', 'position': 'after'})
        for rec in self:
            rec.kg_symbol = kg_symbol.id


    @api.onchange('product_type','action_type_id')
    def _cargar_dominio_vehiculo(self):
        domain = {}
        warning = {}
        res = {}
        fleet_obj = self.env['fleet.vehicle']
        fleet_vehicle_id = fleet_obj.search([('state_id', 'in', ('Tractores', 'Camiones', 'Camionetas'))])
        fleet_matricula_dos_id = fleet_obj.search([('state_id', 'in', 'Semi Remolques y Remolques')])
        employee_obj = self.env['hr.employee']
        driver = employee_obj.search([('category_ids.name', '=', 'Chofer')])
        if self.action_type_id:
            if self.action_type_id.name == 'Retiro de Vacío':
                self.is_invoiced = False
        domain = {
                  'matricula_dos_id': [('id', 'in', fleet_matricula_dos_id.ids)],
                  'driver_id': [('id', 'in', driver.ids)]
        }

        if warning:
            res['warning'] = warning
        if domain:
            res['domain'] = domain
        return res

    @api.onchange('matricula_fletero')
    def onchange_vehicle_id(self):
        domain = {}
        warning = {}
        res = {}

        for rec in self:
            rec.chofer = rec.matricula_fletero.chofer

        vehiculo = self.env['fleet.vehicle']
        matriculas_fleteros = vehiculo.search([('is_ras_property', '!=', True)]).ids
        domain = {'matricula_fletero': [('id', 'in', matriculas_fleteros)]}

        if warning:
            res['warning'] = warning
        if domain:
            res['domain'] = domain
        return res



    @api.onchange('action_type_id', 'product_id')
    def onchange_action_type_id(self):
        domain = {}
        warning = {}
        res = {}
        operation_search = self.action_type_id.search([('nacional', '=', True), ('contenedores', '=', True)]).ids
        domain = {'action_type_id': [('id', 'in', operation_search)]}
        if warning:
            res['warning'] = warning
        if domain:
            res['domain'] = domain
        action_obj = self.env['tipo.accion']
        retiro = action_obj.search([('name', '=', 'Retiro de Vacío')])
        viaje = action_obj.search([('name', '=', 'Viaje')])

        if self.action_type_id.name == retiro.name:
            self.es_retiro_vacio = True

        if self.product_id.name == 'Flete' and self.action_type_id.name == viaje.name:
            self.flete_viaje = True

        for srv in self.mrf_srv_id.mrf_srv_ids:
            if srv.action_type_id.name == 'Viaje':
                if srv.vehicle_id:
                    self.vehicle_id = srv.vehicle_id

                if srv.driver_id:
                    self.driver_id = srv.driver_id

                if srv.matricula_dos_id:
                    self.matricula_dos_id = srv.matricula_dos_id

                if srv.matricula_fletero:
                    self.matricula_fletero = srv.matricula_fletero

                if srv.matricula_dos_fletero:
                    self.matricula_dos_fletero = srv.matricula_dos_fletero

                if srv.chofer:
                    self.chofer = srv.chofer
        return res

    @api.multi
    @api.onchange('matricula_dos_id')
    def get_pricelist_item_products(self):
        pricelist_item_obj = self.env['product.pricelist.item']

        
    @api.onchange('vehicle_id')
    def onchange_matricula(self):
        if self.vehicle_id:
            self.driver_id = self.vehicle_id.driver_id.id


    @api.multi
    def add_supplier_to_product_line(self):
        if self._module:
            if self._module == 'operativa_marfrig':
                tax_obj = self.env['account.tax']
                taxes = tax_obj.search([('name', '=', 'IVA Directo Exp')])
                lineas = []
                for rec in self:
                    line_dict = {}
                    line_dict['ref'] = rec.mrf_srv_id.name
                    line_dict['supplier_id'] = rec.supplier_id.id
                    line_dict['currency_id'] = rec.valor_compra_currency_id.id
                    line_dict['amount'] = rec.valor_compra
                    line_dict['price_subtotal'] = rec.valor_compra
                    line_dict['margrig_id'] = rec.mrf_srv_id.id
                    line_dict['rt_service_id'] = False
                    line_dict['rt_consol_product_id'] = False
                    line_dict['rt_deposito_product_id'] = False
                    line_dict['rt_marfrig_product_id'] = self.id
                    line_dict['service_state'] = self.mrf_srv_id.state
                    line_dict['tax_ids'] = [(6, 0, taxes.ids)]
                    line_dict['service_date'] = rec.start
                    line_dict['tack_id'] = self.get_tack_id()
                    line_dict['dua'] = self.get_dua()
                    line_dict['mic'] = 'N/A'
                    line_dict['origin_id'] = rec.origin_id.id
                    line_dict['destiny_id'] = rec.destiny_id.id
                    line_dict['product_id'] = rec.product_id.id
                    line_dict['output_reference'] = rec.name
                    line_dict['partner_invoice_id'] = 10
                    lineas.append((0, 0, line_dict))

                self.supplier_ids = lineas