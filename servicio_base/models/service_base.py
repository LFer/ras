# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import ipdb
from collections import defaultdict
import odoo.addons.decimal_precision as dp
from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning
_logger = logging.getLogger(__name__)

class rt_service(models.Model):
    _name = "rt.service"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _description = "Servicio Nacional-Internacional"
    _order = "name DESC"

    @api.model
    def create(self, vals):
        context = self._context
        if context is None:
            context = {}
        if context.get('default_es_plantilla', False):
            if 'operation_type' in vals and vals['operation_type'] == 'national':
                vals['name'] = self.env['ir.sequence'].next_by_code('rt.service.template.nacional') or '/'

            if 'operation_type' in vals and vals['operation_type'] == 'international':
                vals['name'] = self.env['ir.sequence'].next_by_code('rt.service.template.internacional') or '/'

        if not vals.get('name', False) and not context.get('default_es_plantilla', False):
            if 'operation_type' in vals and vals['operation_type'] == 'national':
                vals['name'] = self.env['ir.sequence'].next_by_code('rt.service.nacional') or '/'

            if 'operation_type' in vals and vals['operation_type'] == 'international':
                vals['name'] = self.env['ir.sequence'].next_by_code('rt.service.internacional') or '/'
        return super(rt_service, self).create(vals)

    @api.multi
    def _get_operation_type(self):
        res = []
        operation_national = [('transit_nat', '80 - Transito Nacional'),
                              ('impo_nat', '10 - IMPO Nacional'),
                              ('expo_nat', '40 - EXPO Nacional'),
                              ('interno_plaza_nat', 'Interno Plaza Nacional'),
                              ('interno_fiscal_nat', 'Interno Fiscal Nacional')
                              ]
        # operation_international = [('transit_inter', '80 - Transito Internacional'),
        #                            ('impo_inter', '10 - IMPO Internacional'),
        #                            ('expo_inter', '40 - EXPO Internacional'),
        #                            ('interno_plaza_inter', 'Interno Plaza Internacional'),
        #                            ('interno_fiscal_inter', 'Interno Fiscal Internacional')]

        operation_international = [('transit_inter_in', '80 - Transito Internacional Ingreso'),
                                   ('transit_inter_out', '80 - Transito Internacional Salida'),
                                   ('impo_inter', '10 - IMPO Internacional'),
                                   ('expo_inter', '40 - EXPO Internacional')]
        both = operation_national + operation_international
        context = self._context
        if 'default_operation_type' in context:
            if context['default_operation_type'] == 'national':
                res = operation_national
            if context['default_operation_type'] == 'international':
                res = operation_international
        else:
            return both
        return res

    @api.depends('operation_type')
    def compute_operation_type(self):
        return

    @api.multi
    def get_vehicles(self):
        for carga in self.carga_ids:
            for line in carga.producto_servicio_ids:
                if line.vehicle_id:
                    carga.rt_service_id.vehicles_ids += line.vehicle_id
        return

    @api.one
    @api.depends('carga_ids.importe_total_carga')
    def _compute_importe_carpeta(self):
        self.importe_total_carpeta = sum(line.importe_total_carga for line in self.carga_ids)
        self.carpeta_currecy_id = self.pricelist_id.currency_id.id



    def _compute_attached_docs_count(self):
        attach_ids = []
        for carpeta in self:
            for carga in carpeta.carga_ids:
                if carga.attach_tipo_contenedor:
                    attach_ids.append(carga.attach_tipo_contenedor.id)

                if carga.attach_remito:
                    attach_ids.append(carga.attach_remito.id)

                if carga.attach_precinto:
                    attach_ids.append(carga.attach_precinto.id)


                for inv in carga.factura_carga_ids:
                    if inv.attachment:
                        attach_ids.append(inv.attachment.id)

                for pl in carga.packing_list_carga_ids:
                    if pl.attachment:
                        attach_ids.append(pl.attachment.id)

                for bl in carga.bill_of_landing_ids:
                    if bl.attachment:
                        attach_ids.append(bl.attachment.id)

                for prod in carga.producto_servicio_ids:
                    if prod.attach_remito:
                        attach_ids.append(id_rm for id_rm in prod.attach_remito.ids)
        self.doc_count = len(attach_ids)


    @api.depends('invoices_ids', 'invoice_count')
    def _compute_invoice(self):
        for order in self:
            invoices = self.env['account.invoice']
            inves = invoices.search([('rt_service_id', '=', order.id)])
            order.invoice_count = len(inves)

    @api.depends('carga_ids.producto_servicio_ids', 'totally_invoiced_computed')
    def _compute_totally_invoiced(self):
        facturado = []
        for carpeta in self:
            for carga in carpeta.carga_ids:
                for producto in carga.producto_servicio_ids:
                    if producto.is_invoiced:
                        if producto.invoiced:
                            facturado.append(True)
                        else:
                            facturado.append(False)
        if facturado:
            if not all(facturado):
                #Si hay alguno en falso es porque no esta facturado
                carpeta.totally_invoiced_computed = False
                carpeta.totally_invoiced = False
                print('deberia poner todo en falso')

            if all(facturado):
                #Tiene todas en true
                carpeta.totally_invoiced_computed = True
                carpeta.totally_invoiced = True


    origin_id = fields.Many2one(comodel_name='res.partner.address.ext', string='Origen')
    destiny_id = fields.Many2one(comodel_name='res.partner.address.ext', string='Destino')
    service_template_id = fields.Many2one(comodel_name='service.template', string='Plantilla')
    company_id = fields.Many2one('res.company', string='Compañia', default=lambda self: self.env.user.company_id)
    user_id = fields.Many2one('res.users', string='Usuario', default=lambda self: self.env.user, track_visibility="onchange")
    invoices_ids = fields.One2many(comodel_name='account.invoice', inverse_name='rt_service_id', string='Facturas de Cliente', domain=[('type', '=', 'out_invoice')])
    operation_type = fields.Selection([('national', 'Nacional'), ('international', 'Internacional')], string='Tipo de Servicio', store=True)
    calendario_id = fields.Many2one(comodel_name='servicio.calendario', string='Calendario Relacionado')
    active = fields.Boolean(default=True)
    aduana_origen_id = fields.Many2one('fronteras', 'Aduana Origen')
    aduana_destino_id = fields.Many2one('fronteras', 'Aduana Destino')
    name = fields.Char('Referencia', required=False, copy=False, select=True, default='/')
    reference = fields.Text(string='Referencia Carpeta')
    dua_type = fields.Selection([('cabezal', 'En Cabezal'), ('linea', u'Por Línea')], string='Modalidad DUA')
    invoice_type_id = fields.Many2one(comodel_name='rt.invoice.type', string=u'Modalidad de Facturación') #TODO REMOVE
    dua_cabezal = fields.Char(string='DUA')
    dua_aduana = fields.Char(string='Mes', size=3)
    dua_anio = fields.Char(string='Año', size=4)
    dua_numero = fields.Char(string='Dua_Numero')
    dua_anionumero = fields.Char()
    gex_number = fields.Char(string='Nº de Gex')
    mensaje_simplificado = fields.Char(string='MS')
    rt_servicios_ids = fields.One2many('rt.service.line', 'rt_service_id', string='Cargas Asociadas')
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('confirm', 'Confirmado'),
        ('inprocess', 'En proceso'),
        ('progress', 'Servicio Facturado'),
        ('invoice_rejected', 'Fac. Rechazada'),
        ('cancel', 'Cancelado'),
        ('done', 'Realizado'),
    ], string='Status', index=True, readonly=True, default='draft',
        track_visibility='onchange', copy=False,
        help=" * The 'Draft' status is used when a user is encoding a new and unconfirmed Invoice.\n"
             " * The 'Open' status is used when user creates invoice, an invoice number is generated. It stays in the open status till the user pays the invoice.\n"
             " * The 'Paid' status is set automatically when the invoice is paid. Its related journal entries may or may not be reconciled.\n"
             " * The 'Cancelled' status is used when user cancel invoice.")
    partner_id = fields.Many2one(comodel_name='res.partner', string='Dueño de la Mercadería', domain=[('customer', '=', True), ('dispatcher', '=', False)])
    partner_invoice_id = fields.Many2one(comodel_name='res.partner', string='Cliente a facturar', domain=[('customer', '=', True)])
    partner_dispatcher_id = fields.Many2one(comodel_name='res.partner', string='Despachante', domain=[('dispatcher', '=', True)])
    partner_where_paper_id = fields.Many2one('res.partner', 'Donde quedan los papeles', domain=[('where_paper', '=', True)])
    partner_carrier_id = fields.Many2one(comodel_name='res.partner', string='Carrier', domain=[('carrier', '=', True)])
    pricelist_id = fields.Many2one(comodel_name='product.pricelist', string='Tarifa')
    currency_id = fields.Many2one(comodel_name="res.currency", string="Moneda", related="pricelist_id.currency_id", index=True, readonly=True, store=True)
    carpeta_currecy_id = fields.Many2one(comodel_name="res.currency", string="Moneda")
    partner_consignee_id = fields.Many2one(comodel_name='res.partner', string='Consignatario', domain=[('consignee', '=', True)])
    partner_remittent_id = fields.Many2one(comodel_name='res.partner', string=u'Remitente de Tránsito', domain=[('remittent', '=', True)])
    start_datetime = fields.Datetime(string='Fecha Inicio', index=True, copy=False, default=fields.datetime.now())
    stop_datetime = fields.Datetime('Fecha Fin', index=True, copy=False)
    regimen = fields.Selection(_get_operation_type, string="Regimen", store=True)
    cut_off_operative = fields.Datetime('Cut off operative', required=False)
    partner_user_zf_id = fields.Many2one('res.partner', 'User of ZF', domain=[('user_zf', '=', True)])
    partner_receiver_id = fields.Many2one('res.partner', 'Receiver', domain=[('receiver', '=', True)])
    partner_dispatcher_from_id = fields.Many2one('res.partner', 'Despachante de Origen',domain=[('dispatcher', '=', True)])
    partner_dispatcher_to_id = fields.Many2one('res.partner', 'Despachante de Destino',domain=[('dispatcher', '=', True)])
    grouping_stock = fields.Char('Stock de agrupamiento', size=16)
    output_reference = fields.Char('Referencia de Salida', size=16)
    detail = fields.Text('Detalle')
    lic_type = fields.Char('Tipo de Permiso')
    ministries = fields.Boolean('Ministerio')
    seller_commission = fields.Float('Comisión del vendedor', digits=dp.get_precision('Account'))
    customs_transit = fields.Boolean('Tránsito Aduanero')
    permissive = fields.Boolean('Permisado')
    peons = fields.Boolean('Peons')
    ministries_date = fields.Datetime('Fecha de Ministerio')
    hoist = fields.Boolean('Montacargas')
    dispatcher_contact = fields.Char('Contacto despachante', size=254)
    load_agent_contact = fields.Char('Contacto Cliente Descarga', size=254)
    dangers_loads = fields.Boolean('Carga Peligrosa')
    #Comision
    travel_commission = fields.Float(string=u'Comisión')
    # Campos Auxiliares
    dua_visible = fields.Boolean('Page DUA')
    mic_visible = fields.Boolean('Page MIC')
    retreat_data_visible = fields.Boolean('Page Travel Flow')
    tack_visible = fields.Boolean('Page Tack')
    other_concept_visible = fields.Boolean('Page Other Concepts')
    simplified_message_visible = fields.Boolean('Page Simplified Message')
    summary_visible = fields.Boolean('Page Summary')
    packing_visible = fields.Boolean('Page Packing')
    extra_invoice_partner_visible = fields.Boolean('Partner Invoices')
    srv_partner_seller_id_visible = fields.Boolean('Seller')
    srv_partner_dispatcher_id_visible = fields.Boolean('Dispatcher')
    srv_partner_where_paper_id_visible = fields.Boolean('Where they are the papers')
    srv_partner_remittent_id_visible = fields.Boolean('Remittent of transit')
    importe_total_carpeta = fields.Float(string='Valor Total Carpeta', compute="_compute_importe_carpeta", store=False)
    #Carga
    carga_ids = fields.One2many('rt.service.carga', 'rt_service_id', string='Cargas', copy=True)
    #load_type = fields.Selection([('bulk', 'Bulk'), ('contenedor', 'Contenedor'), ('liquido_granel', u'Granel Líquido'),('solido_granel', u'Granel Solido')], string='Tipo de Carga')
    load_type = fields.Selection([('bulk', 'Bulk-Carga Suelta'), ('contenedor', 'Contenedor'), ('liquido_granel', u'Granel Líquido'),('solido_granel', u'Granel Solido')], string='Tipo de Carga')
    #invoice_lines = fields.Many2many('account.invoice.line', 'invoice_id', 'Invoice Lines', copy=False)
    xls_name = fields.Char(string='File Name', size=128)
    xls_file = fields.Binary(string='XLS File')
    imo = fields.Boolean('IMO')
    crt = fields.Boolean('CRT')
    mic = fields.Boolean('MIC')
    container_qty = fields.Integer('Cantidad de contenedores')
    make_page_invisible = fields.Boolean(help='Este booleano es para hacer invisible la pagina si\n no se cargo regimen, cliente a facturar')
    make_dua_invisible_or_required = fields.Boolean(help='Este campo me va ayudar hacer el dua de las cargas invisible o visible y requerido')
    make_gex_invisible_or_required = fields.Boolean(help='Este campo me va ayudar hacer el gex de las cargas invisible o visible y requerido')
    make_presentacion_invisible = fields.Boolean(help='Esto va hacer el campo presentacion invisible', default=True)
    make_terminal_devolucion_invisible = fields.Boolean(help='Esto hace el campo terminal de devolucion invisible')
    profit_carpeta_ids = fields.One2many('rt.service.profit.carpeta', 'rt_service_id', string='Profit Carpeta')
    profit_carpeta = fields.Float(string='Profit')
    suppliers_invoices_ids = fields.Many2many('account.invoice')
    supplier_invoices_ids = fields.One2many('account.invoice', 'rt_service_id', string='Facturas de Cliente',domain=[('type', '=', 'in_invoice')])
    vehicles_ids = fields.One2many('fleet.vehicle', 'rt_service_id', string='Vehículo', compute='get_vehicles')
    invisible_in_transit = fields.Boolean()
    dua_muestra = fields.Boolean()
    doc_count = fields.Integer(compute='_compute_attached_docs_count', string="Number of documents attached")
    action_type_id = fields.Many2one('tipo.accion', string="Tipo de Acción")
    attachment = fields.Many2many('ir.attachment', 'attatch_rel', 'res_id')
    has_dua_cabezal = fields.Boolean()
    invoice_count = fields.Integer(compute="_compute_invoice", string='Conteo de Facturas', copy=False, default=0, store=True)
    totally_invoiced = fields.Boolean()
    totally_invoiced_computed = fields.Boolean(compute="_compute_totally_invoiced", store=False)
    es_plantilla = fields.Boolean(string='Es plantilla')
    plantilla_id = fields.Many2one(comodel_name='rt.service', string='Carpeta Generada')
    profit_carpeta_uyu = fields.Float(string='Profit Carpeta UYU')
    profit_carpeta_usd = fields.Float(string='Profit Carpeta USD')
    @api.multi
    def generar_costos(self, carpetas=None):
        """
        Recorre las cargas, recorre los servicios.
        Si es de terceros, gastos y tiene proveedor y moneda y valor de compra
        Crea el objeto de costo
        :return:
        """
        regimen_map = {
            'transit_nat': 'Transito Nacional',
            'impo_nat': 'IMPO Nacional',
            'expo_nat': 'EXPO Nacional',
            'interno_plaza_nat': 'Interno Plaza Nacional',
            'interno_fiscal_nat': 'Interno Fiscal Nacional',
            'transit_inter_in': 'Transito Internacional Ingreso',
            'transit_inter_out': 'Transito Internacional Salida',
            'impo_inter': 'IMPO Internacional',
            'expo_inter': 'EXPO Internacional',
        }
        regimen = regimen_map[self.regimen]
        regimen_obj = self.env['regimenes']
        regimen_id = regimen_obj.search([('name', '=', regimen)])
        tax_obj = self.env['account.tax']
        taxes = tax_obj.search([('regimen_ids', 'in', regimen_id.ids)])
        lineas = []
        cost_obj = self.env['rt.service.product.supplier']
        for carpeta in carpetas:
            for carga in carpeta.carga_ids:
                for producto in carga.producto_servicio_ids:
                    if producto.product_type == 'terceros' and producto.is_outgoing:
                        if producto.supplier_id:
                            if producto.valor_compra:
                                if producto.valor_compra_currency_id:
                                    if producto.supplier_ids:
                                        for prd in producto.supplier_ids:
                                            if not prd.invoice_id:
                                                prd.unlink()
                                    """
                                    aca va ir todo el codigo supongo
                                    """
                                    line_dict = {}
                                    line_dict['ref'] = carpeta.name
                                    line_dict['supplier_id'] = producto.supplier_id.id
                                    line_dict['currency_id'] = producto.valor_compra_currency_id.id
                                    line_dict['amount'] = producto.valor_compra
                                    line_dict['price_subtotal'] = float(producto.valor_compra * (1 + (taxes.amount / 100)))
                                    line_dict['rt_service_id'] = carpeta.id
                                    line_dict['rt_service_product_id'] = producto.id
                                    line_dict['service_state'] = carpeta.state
                                    line_dict['tax_ids'] = [(6, 0, taxes.ids)]
                                    line_dict['service_date'] = producto.start
                                    line_dict['tack_id'] = producto.get_tack_id()
                                    line_dict['dua'] = producto.get_dua()
                                    line_dict['mic'] = producto.get_mic()
                                    line_dict['crt'] = producto.get_crt()
                                    line_dict['origin_id'] = producto.origin_id.id
                                    line_dict['destiny_id'] = producto.destiny_id.id
                                    line_dict['product_id'] = producto.product_id.id
                                    line_dict['output_reference'] = producto.name
                                    line_dict['partner_invoice_id'] = producto.partner_invoice_id.id
                                    # lineas.append((0, 0, line_dict))
                                    result = cost_obj.create(line_dict)
                                    print('aca va el codigo')
                                else:
                                    raise Warning('No tiene importe')
                            else:
                                raise Warning('No tiene moneda')


                        else:
                            raise Warning('No tiene Proveedor')

    @api.multi
    def copy(self, default=None):
        if self.calendario_id:
            context = self._context.copy()
            calendario = self.calendario_id
            default = dict(default or {})
            default['operation_type'] = self.operation_type
            default['regimen'] = self.regimen
            default['es_plantilla'] = False
            default['make_page_invisible'] = True
            default['start_datetime'] = calendario.start
            default['stop_datetime'] = calendario.stop
            default['calendario_id'] = False
            # super(rt_service, self).copy(default)
            new = super(rt_service, self).copy(default)
            for carga in new.carga_ids:
                if self.dua_type == 'cabezal':
                    carga.has_dua_cabezal = True
                if self.dua_type == 'linea':
                    carga.has_dua_cabezal = False
                carga.es_plantilla = False
                carga.start_datetime = calendario.start
                for producto in carga.producto_servicio_ids:
                    producto.es_plantilla = False
                    producto.start = calendario.start
                    producto.stop = calendario.stop
            calendario.partner_id = self.partner_id
            calendario.rt_service_id = new.id
            self.plantilla_id = new.id
            self.calendario_id = False

            return new
        else:
            raise UserError(
                "No se encontró un Calendario Relacionado, llene dicho campo y vuelva a crear la plantilla")
        # return {
        #     'type': 'ir.actions.client',
        #     'tag': 'action_warn',
        #     'name': 'Notificación',
        #     'params': {
        #         'title': 'CFE',
        #         'text': '¡La facturación Electrónica está activa!',
        #         'sticky': True
        #     }
        # }
        # return {
        #     'domain': [('id', 'in', new.ids), ('operation_type', '=', 'national')],
        #     'name': 'Carpeta',
        #     'view_type': 'form',
        #     'view_mode': 'tree,form',
        #     'res_model': 'rt.service',
        #     'view_id': False,
        #     'views': [(self.env.ref('servicio_base.rt_service_base_tree_view').id, 'tree'), (self.env.ref('servicio_base.view_rt_service_form').id, 'form')],
        #     'context': "{'default_operation_type':'national'}",
        #     'type': 'ir.actions.act_window'
        # }


    @api.multi
    def actualiza_estado_calendario(self, carpeta=None, estado=None):
        estados_obj = self.env['color.picker']
        calendario_obj = self.env['servicio.calendario']
        realizada_facturada = estados_obj.search([('name', '=', 'Carga Realizada y Facturada')])
        factura_rechazada = estados_obj.search([('name', '=', 'Factura Rechazada')])
        if carpeta:
            calendarios = calendario_obj.search([('rt_service_id', '=', carpeta.id)])
            if calendarios:
                for calendario in calendarios:
                    if estado == 'Facturado':
                        calendario.color_pickier_id = realizada_facturada.id
                    if estados_obj == 'Rechazado':
                        calendario.color_pickier_id = factura_rechazada.id


    # @api.constrains('dua_anionumero')
    # def _check_dua_muestra(self):
    #     for record in self:
    #         if not record.dua_muestra:
    #             raise ValidationError("NO puede haber dos numeros de DUA iguales en el mismo año!")

    @api.multi
    def show_rejected_service_lines(self):
        context = self._context.copy()
        srv_ids = self.ids
        act_window = self.env['ir.actions.act_window']
        wizard = self
        # open the list view of service product to invoice
        res = act_window.for_xml_id('servicio_base', 'action_servicio_rechazado')
        res['context'] = {
            'search_default_invoiced_rejected': 1,
        }
        products_obj = self.env['rt.service.productos']
        products_rejected = products_obj.search([('rt_service_id', '=', self.id), ('is_invoiced', '=', True)])

        # domain
        if srv_ids:
            res['domain'] = []
            res['domain'].append(('id', 'in', products_rejected.ids))
            res['domain'].append(('invoiced', '=', False))
            res['domain'].append(('is_invoiced', '=', True))
        return res

    @api.multi
    def action_view_invoice(self):
        '''
        This function returns an action that display existing vendor bills of given purchase order ids.
        When only one found, show the vendor bill immediately.
        '''
        action = self.env.ref('account.action_invoice_tree1')
        result = action.read()[0]
        create_bill = self.env.context.get('create_bill', False)
        # override the context to get rid of the default filtering
        result['context'] = {
            'type': 'out_invoice',
            'default_purchase_id': self.id,
            'default_currency_id': self.currency_id.id,
            'default_company_id': self.company_id.id,
            'company_id': self.company_id.id
        }
        # choose the view_mode accordingly
        if len(self.invoices_ids) > 1 and not create_bill:
            result['domain'] = "[('id', 'in', " + str(self.invoices_ids.ids) + ")]"
        else:
            res = self.env.ref('account.invoice_form', False)
            result['views'] = [(res and res.id or False, 'form')]
            # Do not set an invoice_id if we want to create a new bill.
            if not create_bill:
                result['res_id'] = self.invoices_ids.id or False
        result['context']['default_origin'] = self.name
        # result['context']['default_reference'] = self.partner_ref
        return result

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
        invoice.print_delivery_order = partner.print_delivery_order
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

    def calcular_delivery_order(self):
        delivery_order = ''
        carga_anterior = 0
        for carga in self.carga_ids:
                if carga.id != carga_anterior and carga.delivery_order:
                    delivery_order += carga.delivery_order + '\n'
                carga_anterior = carga.id
        return delivery_order

    def get_regimen(self, lineas_producto):
        regimen = []
        regimen_to_return = ''
        if lineas_producto:
            for line in lineas_producto:
                if line.rt_service_id:
                    regimen.append(line.rt_service_id.regimen)
                    regimen_to_return = line.rt_service_id.regimen
                if line.regimen_excepcion:
                    regimen.append(line.regimen_excepcion)

        if len(set(regimen)) > 1:
            raise Warning('El conjunto de regimenes no puede ser mayor a 1, revise')

        return regimen_to_return

    def _group_by_product(self, product_service=None):
        lista_prod = []
        for producto in product_service:
            existe = False
            if lista_prod:
                for product_name in lista_prod:

                    if producto.product_id.name == product_name[0]:
                        existe = True
                        product_name[1][1] += producto.importe
                        product_name[1][2].append(producto.id)
            if not lista_prod or not existe:
                lista_prod.append([producto.product_id.name, [producto, producto.importe, [producto.id]]])

        return lista_prod


    @api.multi
    def facturar_regimen_transito_in(self, product_lines, amount, advance_payment_method):
        if advance_payment_method == 'all':
            raise Warning('No se puede facturar entera una IMPO')
        account_obj = self.env['account.account']
        tax_obj = self.env['account.tax']
        carpeta_obj = self.env['rt.service']
        operation_taxes = {
            'exento': False,
            'asimilado': tax_obj.search([('name', '=', 'IVA Venta asimilado a exportación')]),
            'gravado': tax_obj.search([('name', '=', 'IVA Ventas (22%)')])
        }

        lineas = []
        if product_lines:
            for line in product_lines:
                id_carpeta = line.rt_service_id.id
                carpeta = carpeta_obj.browse(id_carpeta)
                account = account_obj.search([('code', '=', '41031007')])
                taxes = operation_taxes['asimilado']
                line_dict = {}
                if advance_payment_method == 'percentage':
                    # TRAMO INTERNACIONAL
                    if self.tramo_a_facturar == 'internacional':
                        if line.tramo_inter:
                            raise Warning('Ya se facturo el tramo internacional')
                        else:
                            taxes = operation_taxes['asimilado']
                            account = account_obj.search([('code', '=', '41031007')])
                            if line.product_id.name == 'Flete':
                                line_dict['name'] = line.name or ''  # 'TRAMO INTERNACIONAL'
                                line_dict['account_id'] = account.id
                                line_dict['price_unit'] = line.importe * amount / 100
                                line_dict['uom_id'] = line.product_id.uom_id.id
                                line_dict['tramo_facturado'] = 'international'
                                line_dict['product_id'] = line.product_id.id
                                line_dict['rt_service_product_id'] = line.id
                                line_dict['invoice_line_tax_ids'] = [(6, 0, taxes.ids)]
                                lineas.append((0, 0, line_dict))
                                line.tramo_inter = True
                                if line.tramo_inter and line.tramo_nat:
                                    # Facturado
                                    line.invoiced = True
                            else:
                                line_dict['name'] = line.name or ''
                                line_dict['account_id'] = account.id
                                line_dict['price_unit'] = line.importe
                                line_dict['uom_id'] = line.product_id.uom_id.id
                                line_dict['product_id'] = line.product_id.id
                                line_dict['rt_service_product_id'] = line.id
                                line_dict['invoice_line_tax_ids'] = [(6, 0, taxes.ids)]
                                lineas.append((0, 0, line_dict))
                                # Facturado
                                line.invoiced = True

                    # TRAMO NACIONAL
                    if self.tramo_a_facturar == 'national':
                        if line.tramo_nat:
                            raise Warning('Ya se facturo el tramo nacional')
                        else:
                            taxes = operation_taxes['gravado']
                            account = account_obj.search([('code', '=', '41031008')])
                            if line.product_id.name == 'Flete':
                                line_dict['name'] = line.name or ''  # 'TRAMO NACIONAL'
                                line_dict['account_id'] = account.id
                                line_dict['price_unit'] = line.importe * amount / 100
                                line_dict['uom_id'] = line.product_id.uom_id.id
                                line_dict['tramo_facturado'] = 'national'
                                line_dict['product_id'] = line.product_id.id
                                line_dict['rt_service_product_id'] = line.id
                                line_dict['invoice_line_tax_ids'] = [(6, 0, taxes.ids)]
                                lineas.append((0, 0, line_dict))
                                line.tramo_nat = True
                                if line.tramo_nat and line.tramo_inter:
                                    # Facturado
                                    line.invoiced = True
                            else:
                                line_dict['name'] = line.name or ''
                                line_dict['account_id'] = account.id
                                line_dict['price_unit'] = line.importe
                                line_dict['uom_id'] = line.product_id.uom_id.id
                                line_dict['product_id'] = line.product_id.id
                                line_dict['rt_service_product_id'] = line.id
                                line_dict['invoice_line_tax_ids'] = [(6, 0, taxes.ids)]
                                lineas.append((0, 0, line_dict))
                                # Facturado
                                line.invoiced = True

                else:
                    line_dict['name'] = line.name or ''
                    line_dict['account_id'] = account.id
                    line_dict['price_unit'] = line.importe
                    line_dict['uom_id'] = line.product_id.uom_id.id
                    line_dict['product_id'] = line.product_id.id
                    line_dict['rt_service_product_id'] = line.id
                    line_dict['invoice_line_tax_ids'] = [(6, 0, taxes.ids)]
                    lineas.append((0, 0, line_dict))
                    # Facturado
                    line.invoiced = True

        return lineas, carpeta

    @api.multi
    def facturar_regimen_transito_out(self, product_lines, amount_nat, amount_inter):
        account_obj = self.env['account.account']
        tax_obj = self.env['account.tax']
        carpeta_obj = self.env['rt.service']
        operation_taxes = {
            'exento': False,
            'asimilado': tax_obj.search([('name', '=', 'IVA Venta asimilado a exportación')]),
            'gravado': tax_obj.search([('name', '=', 'IVA Ventas (22%)')])
        }
        lineas = []
        if product_lines:
            for line in product_lines:
                id_carpeta = line.rt_service_id.id
                carpeta = carpeta_obj.browse(id_carpeta)
                account_nat = account_obj.search([('code', '=', '41031006')])
                account_inter = account_obj.search([('code', '=', '41031005')])
                taxes = operation_taxes['asimilado']
                line_dict_inter = {}
                line_dict_nat = {}
                line_dict = {}
                if line.product_id.name == 'Flete':
                    # TRAMO INTERNACIONAL
                    line_dict_inter['name'] = line.name or ''#'TRAMO INTERNACIONAL'
                    line_dict_inter['account_id'] = account_inter.id
                    line_dict_inter['price_unit'] = line.importe * amount_inter / 100
                    line_dict_inter['uom_id'] = line.product_id.uom_id.id
                    line_dict_inter['product_id'] = line.product_id.id
                    line_dict_inter['rt_service_product_id'] = line.id
                    line_dict_inter['invoice_line_tax_ids'] = [(6, 0, taxes.ids)]
                    lineas.append((0, 0, line_dict_inter))

                    # TRAMO NACIONAL
                    line_dict_nat['name'] = line.name or '' #'TRAMO NACIONAL'
                    line_dict_nat['account_id'] = account_nat.id
                    line_dict_nat['price_unit'] = line.importe * amount_nat / 100
                    line_dict_nat['uom_id'] = line.product_id.uom_id.id
                    line_dict_nat['product_id'] = line.product_id.id
                    line_dict_nat['rt_service_product_id'] = line.id
                    line_dict_nat['invoice_line_tax_ids'] = [(6, 0, taxes.ids)]
                    lineas.append((0, 0, line_dict_nat))
                else:
                    line_dict['name'] = line.name or ''
                    line_dict['account_id'] = account_inter.id
                    line_dict['price_unit'] = line.importe
                    line_dict['uom_id'] = line.product_id.uom_id.id
                    line_dict['product_id'] = line.product_id.id
                    line_dict['rt_service_product_id'] = line.id
                    line_dict['invoice_line_tax_ids'] = [(6, 0, taxes.ids)]
                    lineas.append((0, 0, line_dict))
                # Facturado
                line.invoiced = True

        return lineas, carpeta

    @api.multi
    def facturar_regimen_expo(self, product_lines, amount_nat, amount_inter):
        account_obj = self.env['account.account']
        tax_obj = self.env['account.tax']
        carpeta_obj = self.env['rt.service']
        operation_taxes = {
            'exento': False,
            'asimilado': tax_obj.search([('name', '=', 'IVA Venta asimilado a exportación')]),
            'gravado': tax_obj.search([('name', '=', 'IVA Ventas (22%)')])
        }
        lineas = []
        if product_lines:
            for line in product_lines:
                id_carpeta = line.rt_service_id.id
                carpeta = carpeta_obj.browse(id_carpeta)
                account_inter = account_obj.search([('code', '=', '41031001')])
                account_nat = account_obj.search([('code', '=', '41031002')])
                taxes = operation_taxes['asimilado']
                line_dict_inter = {}
                line_dict_nat = {}
                line_dict = {}
                if line.product_id.name == 'Flete':
                    # TRAMO INTERNACIONAL
                    line_dict_inter['name'] = line.name or ''#'TRAMO INTERNACIONAL'
                    line_dict_inter['account_id'] = account_inter.id
                    line_dict_inter['price_unit'] = line.importe * amount_inter / 100
                    line_dict_inter['uom_id'] = line.product_id.uom_id.id
                    line_dict_inter['product_id'] = line.product_id.id
                    line_dict_inter['rt_service_product_id'] = line.id
                    line_dict_inter['invoice_line_tax_ids'] = [(6, 0, taxes.ids)]
                    lineas.append((0, 0, line_dict_inter))

                    # TRAMO NACIONAL
                    line_dict_nat['name'] = line.name or '' #'TRAMO NACIONAL'
                    line_dict_nat['account_id'] = account_nat.id
                    line_dict_nat['price_unit'] = line.importe * amount_nat / 100
                    line_dict_nat['uom_id'] = line.product_id.uom_id.id
                    line_dict_nat['product_id'] = line.product_id.id
                    line_dict_nat['rt_service_product_id'] = line.id
                    line_dict_nat['invoice_line_tax_ids'] = [(6, 0, taxes.ids)]
                    lineas.append((0, 0, line_dict_nat))
                else:
                    line_dict['name'] = line.name or ''
                    line_dict['account_id'] = account_inter.id
                    line_dict['price_unit'] = line.importe
                    line_dict['uom_id'] = line.product_id.uom_id.id
                    line_dict['product_id'] = line.product_id.id
                    line_dict['rt_service_product_id'] = line.id
                    line_dict['invoice_line_tax_ids'] = [(6, 0, taxes.ids)]
                    lineas.append((0, 0, line_dict))
                # Facturado
                line.invoiced = True

        return lineas, carpeta

    @api.multi
    def facturar_regimen_impo(self, product_lines, amount, advance_payment_method):
        if advance_payment_method == 'all':
            raise Warning('No se puede facturar entera una IMPO')
        account_obj = self.env['account.account']
        tax_obj = self.env['account.tax']
        carpeta_obj = self.env['rt.service']
        operation_taxes = {
            'exento': False,
            'asimilado': tax_obj.search([('name', '=', 'IVA Venta asimilado a exportación')]),
            'gravado': tax_obj.search([('name', '=', 'IVA Ventas (22%)')])
        }

        lineas = []
        if product_lines:
            for line in product_lines:
                id_carpeta = line.rt_service_id.id
                carpeta = carpeta_obj.browse(id_carpeta)
                account = account_obj.search([('code', '=', '41031003')])
                taxes = operation_taxes['asimilado']
                line_dict = {}
                if advance_payment_method == 'percentage':
                    # TRAMO INTERNACIONAL
                    if self.tramo_a_facturar == 'internacional':
                        if line.tramo_inter:
                            raise Warning('Ya se facturo el tramo internacional')
                        else:
                            taxes = operation_taxes['asimilado']
                            account = account_obj.search([('code', '=', '41031003')])
                            if line.product_id.name == 'Flete':
                                line_dict['name'] = line.name or ''#'TRAMO INTERNACIONAL'
                                line_dict['account_id'] = account.id
                                line_dict['price_unit'] = line.importe * amount / 100
                                line_dict['uom_id'] = line.product_id.uom_id.id
                                line_dict['tramo_facturado'] = 'international'
                                line_dict['product_id'] = line.product_id.id
                                line_dict['rt_service_product_id'] = line.id
                                line_dict['invoice_line_tax_ids'] = [(6, 0, taxes.ids)]
                                lineas.append((0, 0, line_dict))
                                line.tramo_inter = True
                                if line.tramo_inter and line.tramo_nat:
                                    # Facturado
                                    line.invoiced = True
                            else:
                                line_dict['name'] = line.name or ''
                                line_dict['account_id'] = account.id
                                line_dict['price_unit'] = line.importe
                                line_dict['uom_id'] = line.product_id.uom_id.id
                                line_dict['product_id'] = line.product_id.id
                                line_dict['rt_service_product_id'] = line.id
                                line_dict['invoice_line_tax_ids'] = [(6, 0, taxes.ids)]
                                lineas.append((0, 0, line_dict))
                                # Facturado
                                line.invoiced = True

                    # TRAMO NACIONAL
                    if self.tramo_a_facturar == 'national':
                        if line.tramo_nat:
                            raise Warning('Ya se facturo el tramo nacional')
                        else:
                            taxes = operation_taxes['gravado']
                            account = account_obj.search([('code', '=', '41031004')])
                            if line.product_id.name == 'Flete':
                                line_dict['name'] = line.name or '' #'TRAMO NACIONAL'
                                line_dict['account_id'] = account.id
                                line_dict['price_unit'] = line.importe * amount / 100
                                line_dict['uom_id'] = line.product_id.uom_id.id
                                line_dict['product_id'] = line.product_id.id
                                line_dict['rt_service_product_id'] = line.id
                                line_dict['invoice_line_tax_ids'] = [(6, 0, taxes.ids)]
                                lineas.append((0, 0, line_dict))
                                line.tramo_nat = True
                                if line.tramo_nat and line.tramo_inter:
                                    # Facturado
                                    line.invoiced = True
                            else:
                                line_dict['name'] = line.name or ''
                                line_dict['account_id'] = account.id
                                line_dict['price_unit'] = line.importe
                                line_dict['uom_id'] = line.product_id.uom_id.id
                                line_dict['product_id'] = line.product_id.id
                                line_dict['rt_service_product_id'] = line.id
                                line_dict['invoice_line_tax_ids'] = [(6, 0, taxes.ids)]
                                lineas.append((0, 0, line_dict))
                                # Facturado
                                line.invoiced = True

                else:
                    line_dict['name'] = line.name or ''
                    line_dict['account_id'] = account.id
                    line_dict['price_unit'] = line.importe
                    line_dict['uom_id'] = line.product_id.uom_id.id
                    line_dict['product_id'] = line.product_id.id
                    line_dict['rt_service_product_id'] = line.id
                    line_dict['invoice_line_tax_ids'] = [(6, 0, taxes.ids)]
                    lineas.append((0, 0, line_dict))
                    # Facturado
                    line.invoiced = True

        return lineas, carpeta

    @api.multi
    def facturar_carpeta(self, amount_nat, amount_inter, amount, advance_payment_method, group_by_product):
        """
        Facturamos directamente todos los servicios de esta carpeta
        :return:
        """
        inv_obj = self.env['account.invoice']
        # journal_id = self.env['account.invoice'].default_get(['journal_id'])['journal_id']
        tax_obj = self.env['account.tax']
        account_obj = self.env['account.account']
        product_service = self.env['rt.service.productos'].search([('rt_service_id', '=', self.id), ('is_invoiced', '=',True), ('invoiced', '=', False)])
        operation_taxes = {
            'exento': False,
            'asimilado': tax_obj.search([('name', '=', 'IVA Venta asimilado a exportación')]),
            'gravado': tax_obj.search([('name', '=', 'IVA Ventas (22%)')])
        }
        lineas = []
        if self.state == 'progress' and self.totally_invoiced:
            raise Warning('La carpeta ya esta facturada')
        if not product_service:
            raise Warning('No se encontraron servicios facturables. Revise si la carga tiene servicios asociados')
        regimen = self.get_regimen(product_service)
        if group_by_product:
            original_product_service = product_service
            product_service = self._group_by_product(product_service=product_service)
        for line in product_service:
            if group_by_product:
                precio = line[1][1]
                ids = line[1][2]
                line = line[1][0]
            if line.is_invoiced:
                if line.operation_type == 'national':
                    if regimen == 'impo_nat':
                        taxes = operation_taxes['gravado']
                        account = account_obj.search([('code', '=', '41012001')])
                        line_dict = {}
                        line_dict['name'] = line.name
                        line_dict['account_id'] = account.id
                        line_dict['uom_id'] = line.product_id.uom_id.id
                        line_dict['product_id'] = line.product_id.id
                        if group_by_product:
                            line_dict['price_unit'] = precio
                            line_dict['rt_service_product_ids'] = [(4, id) for id in ids]
                        else:
                            line_dict['price_unit'] = line.importe
                            line_dict['rt_service_product_id'] = line.id
                        line_dict['invoice_line_tax_ids'] = [(6, 0, taxes.ids)]
                        lineas.append((0, 0, line_dict))
                        # Facturado
                        line.invoiced = True

                    if regimen == 'expo_nat':
                        taxes = operation_taxes['asimilado']
                        account = account_obj.search([('code', '=', '41013001')])
                        line_dict = {}
                        line_dict['name'] = line.name
                        line_dict['account_id'] = account.id
                        line_dict['uom_id'] = line.product_id.uom_id.id
                        line_dict['product_id'] = line.product_id.id
                        if group_by_product:
                            line_dict['price_unit'] = precio
                            line_dict['rt_service_product_ids'] = [(4, id) for id in ids]
                        else:
                            line_dict['price_unit'] = line.importe
                            line_dict['rt_service_product_id'] = line.id
                        line_dict['invoice_line_tax_ids'] = [(6, 0, taxes.ids)]
                        lineas.append((0, 0, line_dict))
                        # Facturado
                        line.invoiced = True

                    if regimen == 'interno_plaza_nat':
                        taxes = operation_taxes['gravado']
                        account = account_obj.search([('code', '=', '41012001')])
                        line_dict = {}
                        line_dict['name'] = line.name
                        line_dict['account_id'] = account.id
                        line_dict['uom_id'] = line.product_id.uom_id.id
                        line_dict['product_id'] = line.product_id.id
                        if group_by_product:
                            line_dict['price_unit'] = precio
                            line_dict['rt_service_product_ids'] = [(4, id) for id in ids]
                        else:
                            line_dict['price_unit'] = line.importe
                            line_dict['rt_service_product_id'] = line.id
                        line_dict['invoice_line_tax_ids'] = [(6, 0, taxes.ids)]
                        lineas.append((0, 0, line_dict))
                        # Facturado
                        line.invoiced = True

                    if regimen == 'transit_nat':
                        taxes = operation_taxes['asimilado']
                        account = account_obj.search([('code', '=', '41013002')])
                        line_dict = {}
                        line_dict['name'] = line.name
                        line_dict['account_id'] = account.id
                        line_dict['uom_id'] = line.product_id.uom_id.id
                        line_dict['product_id'] = line.product_id.id
                        if group_by_product:
                            line_dict['price_unit'] = precio
                            line_dict['rt_service_product_ids'] = [(4, id) for id in ids]
                        else:
                            line_dict['price_unit'] = line.importe
                            line_dict['rt_service_product_id'] = line.id
                        line_dict['invoice_line_tax_ids'] = [(6, 0, taxes.ids)]
                        lineas.append((0, 0, line_dict))
                        # Facturado
                        line.invoiced = True

                    if regimen == 'interno_fiscal_nat':
                        taxes = operation_taxes['asimilado']
                        account = account_obj.search([('code', '=', '41013002')])
                        line_dict = {}
                        line_dict['name'] = line.name
                        line_dict['account_id'] = account.id
                        line_dict['uom_id'] = line.product_id.uom_id.id
                        line_dict['product_id'] = line.product_id.id
                        if group_by_product:
                            line_dict['price_unit'] = precio
                            line_dict['rt_service_product_ids'] = [(4, id) for id in ids]
                        else:
                            line_dict['price_unit'] = line.importe
                            line_dict['rt_service_product_id'] = line.id
                        line_dict['invoice_line_tax_ids'] = [(6, 0, taxes.ids)]
                        lineas.append((0, 0, line_dict))
                        # Facturado
                        line.invoiced = True

                    self.actualiza_estado_calendario(carpeta=self, estado='Facturado')

        if self.operation_type == 'international':
            if regimen == 'transit_inter_out':
                lineas, carpeta = self.facturar_regimen_transito_out(product_service, amount_nat, amount_inter )
                self.actualiza_estado_calendario(carpeta=carpeta, estado='Facturado')
            if regimen == 'transit_inter_in':
                lineas, carpeta = self.facturar_regimen_transito_in(product_service, amount, advance_payment_method)
                self.actualiza_estado_calendario(carpeta=carpeta, estado='Facturado')
            if regimen == 'expo_inter':
                lineas, carpeta = self.facturar_regimen_expo(product_service, amount_nat, amount_inter)
                self.actualiza_estado_calendario(carpeta=carpeta, estado='Facturado')
            if regimen == 'impo_inter':
                lineas, carpeta = self.facturar_regimen_impo(product_service, amount, advance_payment_method)
                self.actualiza_estado_calendario(carpeta=carpeta, estado='Facturado')

        if group_by_product:
            journal_id = self.calcular_diario(original_product_service[0].rt_service_id.partner_invoice_id)
            inv_account_id = original_product_service[0].rt_service_id.partner_invoice_id.property_account_receivable_id.id
            inv_partner_id = original_product_service[0].rt_service_id.partner_invoice_id.id
            inv_user_id = line.rt_service_id.user_id and original_product_service[0].rt_service_id.user_id.id
        else:
            journal_id = self.calcular_diario(product_service[0].rt_service_id.partner_invoice_id)
            inv_account_id = product_service[0].rt_service_id.partner_invoice_id.property_account_receivable_id.id
            inv_partner_id = product_service[0].rt_service_id.partner_invoice_id.id
            inv_user_id = line.rt_service_id.user_id and product_service[0].rt_service_id.user_id.id

        delivery_order = self.calcular_delivery_order()

        invoice = inv_obj.create({
            'name': self.name,
            'origin': line.name,
            'type': 'out_invoice',
            'account_id': inv_account_id,
            'partner_id': inv_partner_id,
            'journal_id': journal_id,
            'comment': delivery_order,
            'currency_id': line.currency_id.id,
            'fiscal_position_id': line.partner_invoice_id.property_account_position_id.id,
            'company_id': line.rt_service_id.company_id.id,
            'user_id': inv_user_id,
            'rt_service_product_id': line.id,
            'rt_service_id': line.rt_service_id.id,
            'invoice_line_ids': lineas
        })
        line.invoices_ids += invoice
        line.rt_service_id.invoices_ids += invoice

        partner = line.rt_service_id.partner_invoice_id
        self.cargar_campos_impresion(partner, invoice)
        self.generar_costos(carpetas=self)
        self.state = 'progress'
        self.totally_invoiced = True
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

    def get_attachment_ids(self):
        attach_ids = []
        for carpeta in self:
            for carga in carpeta.carga_ids:
                if carga.attach_tipo_contenedor:
                    attach_ids.append(carga.attach_tipo_contenedor.id)

                if carga.attach_remito:
                    attach_ids.append(carga.attach_remito.id)

                if carga.attach_precinto:
                    attach_ids.append(carga.attach_precinto.id)


                for inv in carga.factura_carga_ids:
                    if inv.attachment:
                        attach_ids.append(inv.attachment.id)

                for pl in carga.packing_list_carga_ids:
                    if pl.attachment:
                        attach_ids.append(pl.attachment.id)

                for bl in carga.bill_of_landing_ids:
                    if bl.attachment:
                        attach_ids.append(bl.attachment.id)

                for prod in carga.producto_servicio_ids:
                    if prod.attach_remito:
                        attach_ids.append(prod.attach_remito.id)
        return attach_ids

    @api.multi
    def attachment_tree_view(self):
        self.ensure_one()
        attach_ids = self.get_attachment_ids()
        self.env.cr.execute("select id from ir_attachment where res_model = 'rt.service' and res_id = %s" % self.id)
        res = self.env.cr.fetchall()
        if res:
            result = [r[0] for r in res] + attach_ids
        else:
            result = attach_ids
        domain = [('id', 'in', result)]
        print(domain)
        return {
            'name': _('Attachments'),
            'domain': domain,
            'res_model': 'ir.attachment',
            'type': 'ir.actions.act_window',
            'view_id': False,
            'view_mode': 'kanban,tree,form',
            'view_type': 'form',
            'help': _('''<p class="o_view_nocontent_smiling_face">
                        Documents are attached to the tasks and issues of your project.</p><p>
                        Send messages or log internal notes with attachments to link
                        documents to your project.
                    </p>'''),
            'limit': 80,
            # 'context': "{'default_res_model': '%s','default_res_id': %d}" % (self._name, self.id)
        }

    @api.onchange('partner_invoice_id')
    def _onchange_partner_invoice_id(self):
        if self.partner_invoice_id:
            self.partner_id = self.partner_invoice_id.id

    @api.multi
    def borrador_confirmado(self):
        return self.write({'state': 'confirm'})

    @api.multi
    def a_cancelado(self):
        return self.write({'state': 'cancel'})

    @api.multi
    def a_borrador(self):
        return self.write({'state': 'draft'})

    @api.multi
    def confirmado_en_procesos(self):
        return self.write({'state': 'inprocess'})

    @api.multi
    def facturado_a_realiado(self):
        return self.write({'state': 'done'})

    @api.multi
    @api.depends('name', 'reference')
    def name_get(self):
        return [(rec.id, '%s - %s' % (rec.name, rec.reference)) for rec in self]

    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        recs = self.search(['|', ('name', operator, name), ('reference', operator, name)] + args, limit=limit)
        return recs.name_get()

    @api.onchange('partner_invoice_id', 'company_id', 'start_datetime')
    def _onchange_partner_id(self):
        domain = {}
        warning = {}
        res = {}
        pricelist_obj = self.env['product.pricelist']
        if self.partner_invoice_id:
            partner_id = self.partner_invoice_id.id
            pricelist = pricelist_obj.search([('partner_id', '=', partner_id)])

            if not pricelist:
                if self.partner_invoice_id.property_product_pricelist:
                    self.pricelist_id = self.partner_invoice_id.property_product_pricelist.id
                    return res
                else:
                    pricelist = pricelist_obj.search([('es_generica', '=', True)])
            if len(pricelist) == 1:
                self.pricelist_id = pricelist.id
            else:
                domain = {'pricelist_id': [('id', 'in', pricelist.ids)]}
        if warning:
            res['warning'] = warning
        if domain:
            res['domain'] = domain
        return res


    @api.onchange('gex_number')
    def onchange_gex(self):
        if self.gex_number:
            self.make_dua_invisible_or_required = False
        else:
            self.make_dua_invisible_or_required = True

    @api.onchange('dua_type')
    def _onchange_dua_type(self):
        if self.dua_type == 'cabezal':
            self.make_dua_invisible_or_required = True
            self.make_gex_invisible_or_required = True
            self.has_dua_cabezal = True
        if self.dua_type == 'linea':
            self.has_dua_cabezal = False
            self.make_dua_invisible_or_required = False
            self.make_gex_invisible_or_required = False
            if self.dua_anio:
                self.dua_anio = False
            if self.dua_aduana:
                self.dua_aduana = False
            if self.dua_numero:
                self.dua_numero = False

    @api.onchange('dua_aduana')
    def check_mes(self):
        for rec in self:
            if rec.dua_aduana:
                # probar si se ingreso un int
                try:
                    type(int(rec.dua_aduana)) == int
                except ValueError:
                    rec.dua_aduana = False
                    return {'warning': {'title': "Error", 'message': "Se espera un número de 3 cifras ej: 001"}}
                # 3 es el largo esperado
                if rec.dua_aduana != False:
                    if len(rec.dua_aduana) != 3:
                        rec.dua_aduana = False
                        return {'warning': {'title': "Error", 'message': "Se espera un número de 3 cifras ej: 001"}}
                self.make_gex_invisible_or_required = False
            else:
                self.make_gex_invisible_or_required = True


    @api.onchange('dua_anio','dua_numero')
    def check_anio(self):
        for rec in self:
            # probar si se ingreso un int
            try:
                type(int(rec.dua_anio)) == int
            except ValueError:
                rec.dua_anio = False
                return {'warning': {'title': "Error", 'message': "Se espera un número de 4 cifras ej: 2019"}}
            # 4 es el largo esperado
            if rec.dua_anio != False:
                if len(rec.dua_anio) != 4:
                    rec.dua_anio = False
                    return {'warning': {'title': "Error", 'message': "Se espera un número de 4 cifras ej: 2019"}}
        if rec.dua_numero:
            rec.dua_anionumero = rec.dua_anio + rec.dua_numero


    @api.multi
    @api.onchange('dua_numero', 'dua_type')
    def check_numero(self):
        dua_importaciones = range(0, 500000);
        dua_exportaciones = range(500000, 700000)
        dua_transitos = range(700000, 1000000)
        dua_type = ''
        for rec in self:
            # probar si se ingreso un int
            try:
                type(int(rec.dua_numero)) == int
            except ValueError:
                rec.dua_numero = False
                return {'warning': {'title': "Error", 'message': "Se espera un número de 6 cifras ej: 457882"}}
            if not rec.dua_muestra:
                #6 es el largo esperado
                if rec.dua_numero != False:
                    if len(rec.dua_numero) != 6:
                        rec.dua_numero = False
                        return {'warning': {'title': "Error", 'message': "Se espera un número de 6 cifras ej: 457882"}}
                #Validar regimen
                int_dua = int(rec.dua_numero)
                if (rec.regimen == 'impo_inter' or rec.regimen == 'impo_nat') and int_dua not in dua_importaciones:
                    if int_dua in dua_exportaciones:
                        dua_type = 'Exportaciones (500000 - 699999)'
                    if int_dua in dua_transitos:
                        dua_type = 'Transitos (700000 - 999999)'
                    if rec.dua_numero != False:
                        rec.dua_numero = False
                        return {'warning': {'title': "Error", 'message': 'DUA inválido para el Regimen IMPO \n El DUA ingresado corresponde al regimen  %s' % dua_type}}
                if (rec.regimen == 'expo_inter' or rec.regimen == 'expo_nat') and int_dua not in dua_exportaciones:
                    if int_dua in dua_transitos:
                        dua_type = '700000 - 999999 - Transitos'
                    if int_dua in dua_importaciones:
                        dua_type = '000001 - 499999 - Importaciones'
                    if rec.dua_numero != False:
                        rec.dua_numero = False
                        return {'warning': {'title': "Error", 'message': 'DUA inválido para el Regimen EXPO \n El DUA ingresado corresponde al regimen  %s' % dua_type}}
                if (rec.regimen == 'transit_inter_in' or rec.regimen == 'transit_inter_out' or rec.regimen == 'transit_nat') and int_dua not in dua_transitos:
                    if int_dua in dua_importaciones:
                        dua_type = '000001 - 499999 - Importaciones'
                    if int_dua in dua_exportaciones:
                        dua_type = '500000 - 699999 - Exportaciones'
                    if rec.dua_numero != False:
                        rec.dua_numero = False
                        return {'warning': {'title': "Error", 'message': 'DUA inválido para el Regimen TRANSITO \n El DUA ingresado corresponde al regimen  %s' % dua_type}}
        if rec.dua_anio:
            rec.dua_anionumero = rec.dua_anio + rec.dua_numero

    @api.multi
    def check_numero_fn(self, regimen=False):
        if not regimen:
            regimen = self.regimen
        dua_importaciones = range(0, 500000)
        dua_exportaciones = range(500000, 700000)
        dua_transitos = range(700000, 1000000)
        dua_type = ''
        if self.dua_numero:
            # probar si se ingreso un int
            try:
                type(int(self.dua_numero)) == int
            except ValueError:
                self.dua_numero = False
                return {'warning': {'title': "Error", 'message': "Se espera un número de 6 cifras ej: 457882"}}
            #6 es el largo esperado
            if self.dua_numero != False:
                if len(self.dua_numero) != 6:
                    self.dua_numero = False
                    return {'warning': {'title': "Error", 'message': "Se espera un número de 6 cifras ej: 457882"}}
            #Validar regimen
            int_dua = int(self.dua_numero)
            if (regimen == 'impo_inter' or regimen == 'impo_nat') and int_dua not in dua_importaciones:
                    if int_dua in dua_exportaciones:
                        dua_type = 'Exportaciones (500000 - 699999)'
                    if int_dua in dua_transitos:
                        dua_type = 'Transitos (700000 - 999999)'
                        self.dua_numero = False
                        return {'warning': {'title': "Error", 'message': 'DUA inválido para el Regimen IMPO \n El DUA ingresado corresponde al regimen  %s' % dua_type}}
            if (regimen == 'expo_inter' or regimen == 'expo_nat') and int_dua not in dua_exportaciones:
                    if int_dua in dua_transitos:
                        dua_type = '700000 - 999999 - Transitos'
                    if int_dua in dua_importaciones:
                        dua_type = '000001 - 499999 - Importaciones'
                        self.dua_numero = False
                        return {'warning': {'title': "Error", 'message': 'DUA inválido para el Regimen EXPO \n El DUA ingresado corresponde al regimen  %s' % dua_type}}
            if (regimen == 'transit_inter_out' or regimen == 'transit_nat' or regimen == 'transit_inter_in') and int_dua not in dua_transitos:
                    if int_dua in dua_importaciones:
                        dua_type = '000001 - 499999 - Importaciones'
                    if int_dua in dua_exportaciones:
                        dua_type = '500000 - 699999 - Exportaciones'
                        self.dua_numero = False
                        return {'warning': {'title': "Error", 'message': 'DUA inválido para el Regimen TRANSITO \n El DUA ingresado corresponde al regimen  %s' % dua_type}}
        if self.dua_anio:
            if not self.dua_anionumero:
                self.dua_anionumero = self.dua_anio + self.dua_numero

    @api.multi
    def action_open_invoice_wzd(self):
        row = self
        # pdb.set_trace()
        if not row.ready_to_invoice:
            raise Warning(_('Error'), _("This service not have any invoiceable product pendant to invoice.\n Please check the 'Invoiceable' field on each service product that you want to invoice."))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Invoice Order'),
            'res_model': 'rt.service.advance.payment.inv',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_invoice_nat_per_tax_ids': [
                    (6, 0, [ac_tax.id for ac_tax in row.invoice_nat_per_tax_ids if row.invoice_nat_per_tax_ids])],
                'invoice_nat_per_amount': row.invoice_nat_per_amount,
                'default_invoice_nat_per_account_id': row.invoice_nat_per_account_id and row.invoice_nat_per_account_id.id or False,
                'default_invoice_int_per_tax_ids': [
                    (6, 0, [ac_tax.id for ac_tax in row.invoice_int_per_tax_ids if row.invoice_int_per_tax_ids])],
                'invoice_int_per_amount': row.invoice_int_per_amount,
                'default_invoice_int_per_account_id': row.invoice_int_per_account_id and row.invoice_int_per_account_id.id or False,
            }
        }


    @api.onchange('regimen', 'partner_invoice_id', 'dua_type')
    def onchange_fields(self):
        for rec in self:
            if rec.dua_numero:
                rec.make_dua_invisible_or_required = True
            if not rec.regimen or not rec.partner_invoice_id or not rec.dua_type:
                rec.make_page_invisible = True
            elif rec.regimen or rec.partner_invoice_id or rec.dua_type:
                rec.make_page_invisible = False
            else:
                rec.make_page_invisible = True
            if rec.regimen:
                if rec.regimen == 'expo':
                    rec.make_terminal_devolucion_invisible = False
            if rec.regimen == 'interno_plaza_nat' or rec.regimen == 'interno_fiscal_nat':
                rec.make_page_invisible = False
            if rec.es_plantilla:
                rec.make_page_invisible = False
        return

    @api.multi
    @api.onchange('regimen')
    def change_regimen_dua(self):
        for rec in self:
            if rec.regimen:
                rec.dua_type = False
                rec.gex_number = False
                rec.dua_aduana = False
                rec.dua_anio = False
                rec.dua_numero = False


    def crea_carga_fcl(self, modelo, cantidad):
        line_vals = {}
        lineas = []
        pricelist = self.pricelist_id
        for line in range(int(cantidad)):
            vals = {
                'rt_service_id':self.id,
                'name' : '/',
                'load_type': 'contenedor',
                'container_type': modelo.id,
                'container_size': modelo.size,
                'make_dua_invisible_or_required': True if self.dua_numero else False,
                #'importe': pricelist.sale_price,
                #'importe': pricelist.item_ids[0].sale_price,
                'partner_seller_id': self.partner_invoice_id.user_id.id,
                'importe_currency_id': pricelist.currency_id.id,
                'partner_invoice_id': self.partner_invoice_id.id,
                'partner_id': self.partner_invoice_id.id,
                'start_datetime': self.start_datetime,
                # 'producto_servicio_ids': self.nodo_productos_dos()//

            }
            lineas.append((0, 0, vals))

        line_vals['carga_ids'] = lineas

        return line_vals


    def crea_carga_bulk(self, cantidad):
        line_vals = {}
        lineas = []
        pricelist = self.pricelist_id
        for line in range(int(cantidad)):
            vals = {
                'rt_service_id':self.id,
                'name' : '/',
                'load_type': 'bulk',
                'make_dua_invisible_or_required': True if self.dua_numero else False,
                #'importe': pricelist.sale_price,
                #'importe': pricelist.item_ids[0].sale_price,
                'partner_seller_id': self.partner_invoice_id.user_id.id,
                'importe_currency_id': pricelist.currency_id.id,
                'partner_invoice_id': self.partner_invoice_id.id,
                'partner_id': self.partner_invoice_id.id,
                # 'producto_servicio_ids': self.nodo_productos_dos()

            }
            lineas.append((0, 0, vals))

        line_vals['carga_ids'] = lineas

        return line_vals

    @api.multi
    def generar_cargas(self):
        if not self.rt_servicios_ids:
            raise Warning('Debe ingresar lineas')
        for line in self.rt_servicios_ids:
            if not line.load_type:
                raise Warning('Debe selecionar el tipo de carga')

            if not line.qty:
                raise Warning('La cantidad no puede ser 0')

            #Por ahora vamos por nombre, tenemos que encontrar una forma mas elegante de hacerlo
            if line.load_type == 'contenedor':
                vals = self.crea_carga_fcl(modelo=line.vehicle_id, cantidad=line.qty)
                self.write(vals)
            if line.load_type == 'bulk':
                vals = self.crea_carga_bulk(cantidad=line.qty)
                self.write(vals)

    def convert_to_pesos(self, amount):
        curr_obj = self.env['res.currency']
        cot = curr_obj.search([('name', '=', 'USD')])
        return amount * cot.rate

    def convert_to_dolares(self, amount):
        curr_obj = self.env['res.currency']
        cot = curr_obj.search([('name', '=', 'USD')])
        return amount / cot.rate


    @api.multi
    def compute_profit(self):
        profit_obj = self.env['rt.service.profit.carpeta']
        lineas = []
        line_dict = {}
        self.profit_carpeta_ids = False
        for carga in self.carga_ids:
            for srv in carga.producto_servicio_ids:
                #Cuando es propio el costo hay que cargarglo de otra forma
                if srv.product_type == 'propio':
                    line_dict['rt_service_id'] = self.id
                    line_dict['name'] = 'Venta'
                    line_dict['costo'] = 0
                    line_dict['venta'] = srv.importe
                    line_dict['currency_operation'] = srv.currency_id.id
                    line_dict['usd_currency_id'] = 2
                    line_dict['uyu_currency_id'] = 46
                    line_dict['venta_usd'] = self.convert_to_dolares(srv.importe) if self.currency_id.name != 'USD' else srv.importe
                    line_dict['venta_uyu'] = self.convert_to_pesos(srv.importe) if self.currency_id.name == 'USD' else srv.importe
                    line_dict['costo_usd'] = 0
                    line_dict['costo_uyu'] = 0
                    lineas.append((0, 0, line_dict))
                    line_dict = {}
                    if srv.costo_estimado:
                        line_dict['rt_service_id'] = self.id
                        line_dict['name'] = 'Costo Chofer'
                        line_dict['costo'] = 0
                        line_dict['venta'] = srv.costo_estimado
                        line_dict['currency_operation'] = srv.currency_id.id
                        line_dict['usd_currency_id'] = 2
                        line_dict['uyu_currency_id'] = 46
                        line_dict['venta_usd'] = 0
                        line_dict['venta_uyu'] = 0
                        line_dict['costo_usd'] = self.convert_to_dolares(srv.costo_estimado) if self.currency_id.name != 'USD' else srv.costo_estimado
                        line_dict['costo_uyu'] = self.convert_to_pesos(srv.costo_estimado) if self.currency_id.name == 'USD' else srv.costo_estimado
                        lineas.append((0, 0, line_dict))



        self.profit_carpeta_ids = lineas
        self.profit_carpeta_usd = sum(pro.venta_usd for pro in self.profit_carpeta_ids.filtered(lambda x: x.venta_usd)) - sum(pro.costo_usd for pro in self.profit_carpeta_ids.filtered(lambda x: x.costo_usd))
        self.profit_carpeta_uyu = sum(pro.venta_uyu for pro in self.profit_carpeta_ids.filtered(lambda x: x.venta_uyu)) - sum(pro.costo_uyu for pro in self.profit_carpeta_ids.filtered(lambda x: x.costo_uyu))


class rt_service_profit_carpeta(models.Model):
    _name = "rt.service.profit.carpeta"
    _description = "Profit de la Carpeta"

    rt_service_id = fields.Many2one(comodel_name='rt.service', string='Carpeta Relacionada')
    currency_operation = fields.Many2one('res.currency')
    name = fields.Char(string='Concepto')
    venta = fields.Monetary(string='Venta', default=0.0, currency_field='currency_operation')
    costo = fields.Monetary(string='Costo', default=0.0, currency_field='currency_operation')
    usd_currency_id = fields.Many2one('res.currency')
    uyu_currency_id = fields.Many2one('res.currency')

    venta_usd = fields.Monetary(string='Venta USD', default=0.0, currency_field='usd_currency_id')
    costo_usd = fields.Monetary(string='Costo USD', default=0.0, currency_field='usd_currency_id')

    venta_uyu = fields.Monetary(string='Venta UYU', default=0.0, currency_field='uyu_currency_id')
    costo_uyu = fields.Monetary(string='Costo UYU', default=0.0, currency_field='uyu_currency_id')
