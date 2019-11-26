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

class marfrig_service_base(models.Model):
    _name = "marfrig.service.base"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _description = "Operativa Marfrig"
    _order = "id DESC"

    @api.one
    @api.depends('mrf_srv_ids.kg_planta')
    def _compute_amount(self):
        self.container_kg = sum(line.kg_planta for line in self.mrf_srv_ids)

    # @api.depends('order_line.invoice_lines.invoice_id')
    @api.depends('invoices_ids', 'invoice_count')
    def _compute_invoice(self):
        for order in self:
            invoices = self.env['account.invoice']
            inves = invoices.search([('marfrig_operation_id', '=', order.id)])
            order.invoice_count = len(inves)

    @api.multi
    def update_state(self):
        data = {d['id']: d['state'] for d in self.sudo().read(['state'])}
        for order in self:
            # Segun la cantidad de facuras y sus estados, cambiamos el estado de la operativa
            # Existen facturas?
            if order.invoices_ids:
                # Si todas estan el borrador, no hacemos nada, ya que debe de estar en el estado 'Factura Borrador'
                # Si alguna esta validada, el estado tiene que ser Parcialmente Facturada
                states = [x.state for x in order.invoices_ids]
                if all(n in 'open' for n in states):
                    return self.write({'state': 'totally_invoiced'})
                if any(n in 'open' for n in states):
                    return self.write({'state': 'partially_invoiced'})
                # Si estan todas factuiradas tenemos que pasar el estado a Totalmente Facturado
            if not order.invoices_ids:
                return self.write({'state': 'confirm'})




    name = fields.Char(default='Borrador')
    service_template_id = fields.Many2one(comodel_name='marfrig.template', string='Plantilla')
    company_id = fields.Many2one('res.company', string='Compañia', default=lambda self: self.env.user.company_id)
    partner_invoice_id = fields.Many2one(comodel_name='res.partner', string='Cliente', compute='_compute_marfrig_name')
    pricelist_id = fields.Many2one('product.pricelist.item', string='Tarifa',domain=[('es_marfrig', '=', True)])
    currency_id = fields.Many2one(comodel_name="res.currency", string="Moneda", related="pricelist_id.currency_id", index=True, readonly=True, store=True)
    start_datetime = fields.Datetime(string='Fecha Inicio', required=True, index=True, copy=False, default=fields.datetime.now())
    stop_datetime = fields.Datetime('Fecha Fin', index=True, copy=False)
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('confirm', 'Confirmado'),
        ('inprocess', 'En proceso'),
        ('invoiced', 'Factura Borrador'),
        ('invoice_rejected', 'Fac. Rechazada'),
        ('partially_invoiced', 'Parc. Facturado'),
        ('totally_invoiced', 'Comp. Facturado'),
        ('cancel', 'Cancelado'),
        ('done', 'Realizado'),
    ], string='Status', index=True, readonly=True, default='draft',track_visibility='onchange', copy=False, store=True)
    output_reference = fields.Text('Referencia de Salida', size=16)
    dua_aduana = fields.Char(string= 'Mes', size=3)
    dua_anio = fields.Char(string='Año', size=4)
    dua_numero = fields.Char(string='Dua_Numero', size=6)
    mrf_srv_ids = fields.One2many('marfrig.service.products', 'mrf_srv_id', string='Servicios', copy=True)
    load_presentation = fields.Many2one(comodel_name='catalogo.tipo.bulto', string=u'Tipo de bultos')
    aduana_destino_id = fields.Many2one('fronteras', 'Aduana Destino')
    container_type = fields.Many2one(comodel_name='fleet.vehicle', string='Tipo de Contenedor')
    booking = fields.Char('Booking', size=32)
    preasignado = fields.Boolean(string='Preasignado')
    cut_off_operative = fields.Datetime('Cut off Operativo')
    cut_off_documentario = fields.Datetime('Cut off Documentario')
    terminal_retreat = fields.Many2one(comodel_name='res.partner.address.ext', string='Terminal de Retiro', ondelete='restrict')
    origin_id = fields.Many2one(comodel_name='res.partner.address.ext', string='Origen')
    destiny_id = fields.Many2one(comodel_name='res.partner.address.ext', string='Destino')
    importe = fields.Float(string='Valor de Venta', store=True)
    container_number = fields.Char(string=u'Número de contenedor', size=13)
    container_number_exception = fields.Char(string=u'Nº de contenedor Excepción', size=13)
    seal_number = fields.Char(string='Número de precinto', size=32)
    payload = fields.Float(string='Payload')
    tare = fields.Float('Tara')
    terminal_ingreso_cargado = fields.Many2one(comodel_name='res.partner.address.ext', string=u'Terminal de Ingreso Cargado', ondelete='restrict')
    libre_devolucion = fields.Datetime(string='Libre de Devolución')
    make_container_number_invisible = fields.Boolean(string='Exception', default=False)
    valid_cointaner_number_text = fields.Boolean(help= 'Este booleano es para que se muestre un texto si el número de container es válido')
    invalid_cointaner_number_text = fields.Boolean(help='Este booleano es para que se muestre un texto si el número de container no es válido')
    currency_id_vendedor = fields.Many2one(comodel_name='res.currency', string='Moneda')
    currency_id_chofer = fields.Many2one(comodel_name='res.currency', string='Moneda Comisión Chofer')
    partner_seller_id = fields.Many2one(comodel_name='res.partner', string='Vendedor', domain=[('seller', '=', True)])
    seller_commission = fields.Float(string='Comisión Vendedor')
    product_type = fields.Selection([('propio', 'Propio'), ('terceros', 'Terceros')], string='Origen del Servicio')
    sale_number = fields.Char(string='Nº de Venta')
    attachment_virada = fields.Many2many('ir.attachment')
    attachment_precinto = fields.Many2many('ir.attachment')
    kg_symbol = fields.Many2one(comodel_name='res.currency', compute='_get_kg_symbol', string=' ')
    container_kg = fields.Monetary(string='Peso de la carga', store=True, readonly=True, compute='_compute_amount')
    user_id = fields.Many2one('res.users', string='Usuario', default=lambda self: self.env.user, track_visibility="onchange")
    invoices_ids = fields.One2many('account.invoice', 'marfrig_operation_id', string='Facturas de Clientes',domain=[('type', '=', 'out_invoice')])
    invoice_count = fields.Integer(compute="_compute_invoice", string='Conteo de Facturas', copy=False, default=0, store=True)
    suppliers_invoices_ids = fields.Many2many('account.invoice', string='Facturas de Proveedor', copy=False)
    invoice_id = fields.Many2one('account.invoice')
    load_type = fields.Selection(
        [('bulk', 'Bulk-Carga Suelta'), ('contenedor', 'Contenedor'), ('liquido_granel', u'Granel Líquido'),
         ('solido_granel', u'Granel Solido')], string='Tipo de Carga', default='contenedor')

    @api.multi
    def show_rejected_service_lines(self):
        srv_ids = self.ids
        act_window = self.env['ir.actions.act_window']
        res = act_window.for_xml_id('operativa_marfrig', 'action_servicio_marfig_rechazado')
        res['context'] = {
            'search_default_invoiced_rejected': 1,
        }
        products_obj = self.env['marfrig.service.products']
        products_rejected = products_obj.search([('mrf_srv_id', '=', self.id), ('is_invoiced', '=', True), ('invoiced_rejected', '=', True)])
        # domain
        if srv_ids:
            res['domain'] = []
            res['domain'].append(('id', 'in', products_rejected.ids))
            res['domain'].append(('invoiced', '=', True))
            res['domain'].append(('is_invoiced', '=', True))
        return res



    @api.multi
    def unlink(self):
        for rec in self:
            if rec.state not in ('draft'):
                raise UserError('No Puede eliminar una operativa que no este en estado Borrador')
        return super(marfrig_service_base, self).unlink()

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

    @api.onchange('partner_invoice_id')
    def onchange_partner_invoice_id(self):
        domain = {}
        warning = {}
        res = {}
        tarifa_obj = self.env['product.pricelist.item']
        tarifa = tarifa_obj.search([('es_marfrig', '=', True)]).ids
        domain = {'pricelist_id': [('id', 'in', tarifa)]}
        if warning:
            res['warning'] = warning
        if domain:
            res['domain'] = domain
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

    def crea_horas_espera(self, planta, importe, linea, cantidad_hora_espera):
        self.ensure_one()
        product_obj = self.env['product.product']
        prod_hora_espera = product_obj.search([('name', '=', 'Horas de Espera')])
        matricula_propio = False
        chofer_propio = False
        matricula_dos_id_propio = False
        matricula_fletero_tercero = False
        matricula_dos_fletero_tercero = False
        chofer_tercero = False
        cantidad_hora_espera = cantidad_hora_espera
        # order_lines = []
        data = {}
        action_type_id = self.env['tipo.accion'].search([('name', '=', 'Viaje')])

        data.update({
            'name': 'Horas de Espera',
            'planta_id': planta.id,
            'product_id': prod_hora_espera.id,
            'mrf_srv_id': self.id,
            'importe_linea': importe,
            'product_type': 'propio',
            'action_type_id': action_type_id.id,
            'hora_espera': True,
            'vehicle_id': matricula_propio,
            'driver_id': chofer_propio,
            'matricula_dos_id': matricula_dos_id_propio,
            'matricula_fletero': matricula_fletero_tercero,
            'matricula_dos_fletero': matricula_dos_fletero_tercero,
            'chofer': chofer_tercero,
            'cantidad_hora_espera': cantidad_hora_espera,

        })

        # order_lines.append((0, 0, data))
        self.mrf_srv_ids.create(data)
        # self.mrf_srv_ids = order_lines

    @api.multi
    def a_borrador(self):
        return self.write({'state': 'draft'})

    @api.multi
    def borrador_confirmado(self):
        """
            Genero horas de espera a facturar segun cantidad de plantas.
            Se facturan las horas que se excedan de la cantidad estandard
            definida en el diccionario esperas_segun_plantas.
        """
        vals = {}
        self.ensure_one()
        if not self.mrf_srv_ids:
            vals['name'] = self.env['ir.sequence'].next_by_code('operativa.marfrig.sequence') or '/'
            vals['state'] = 'confirm'
            return self.write(vals)

        pricelist_item_obj = self.env['product.pricelist.item']
        # Defino las horas de espera estandard segun la cantidad de plantas
        esperas_segun_plantas = {1: [5],
                                 2: [2.5, 2.5],
                                 3: [1.5, 1.5, 2],
                                 4: [2, 1, 1, 1]}

        # Contamos las plantas que hay en los servicios
        servicios_con_planta = self.mrf_srv_ids.filtered(lambda x: set(x.planta_id))
        servicios_con_planta_para_crear_horas_espera = self.mrf_srv_ids.filtered(lambda x: set(x.planta_id.ids) and x.is_invoiced)
        cantidad_plantas = len(servicios_con_planta_para_crear_horas_espera)
        if cantidad_plantas > 4:
            raise UserError("El programa no está preparado para soportar más de 4 plantas, contacte al departamento"
                            " de desarrollo")
        horas_espera = esperas_segun_plantas[cantidad_plantas]



        # Recorro los servicios y creo las horas a facturar
        for srv in servicios_con_planta:
            if srv.hora_solicitada and srv.hora_llegada and srv.hora_salida:
                from datetime import datetime
                from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
                import pytz

                user_tz = self.env.user.tz or pytz.utc

                local = pytz.timezone(user_tz)

                display_date_result = datetime.strftime(pytz.utc.localize(srv.hora_solicitada).astimezone(local), '%Y-%m-%d %H:%M:%S')
                print(srv.planta_id.name)
                print('hora solicitada - ' + srv.hora_solicitada.strftime("%d/%m/%Y, %H:%M:%S"))
                print('hora llegada - ' + srv.hora_llegada.strftime("%d/%m/%Y, %H:%M:%S"))
                print('hora salida - ' + srv.hora_salida.strftime("%d/%m/%Y, %H:%M:%S"))
                if horas_espera:
                    # Utilizo la lista como una pila, obtengo y remuevo el primer elemento
                    espera_estandard = horas_espera.pop(0)
                    # Marco Inicio y Fin de la espera real y calculo su duración en horas
                    inicio = srv.hora_llegada if srv.hora_solicitada < srv.hora_llegada else srv.hora_solicitada
                    fin = srv.hora_salida
                    diferencia = fin - inicio
                    diff_horas = diferencia.seconds / 60 / 60
                    if diferencia.days == -1:
                        continue

                    # Si la espera real excede la estandard se factura la diferencia
                    if diff_horas > espera_estandard:
                        hora_a_cobrar = abs(diff_horas - espera_estandard)
                        #Se cobra la hora de espera segun las tarifas por viaje unico (secuencias 1,2,4)
                        sequencia_planta_unica = [1, 2, 3, 4, 5]
                        tarifa_planta = pricelist_item_obj.search([('planta_id', '=', srv.planta_id.id), ('sequence', 'in', sequencia_planta_unica)], limit=1)
                        importe_linea = hora_a_cobrar * tarifa_planta.wait_value
                        srv.importe_linea = importe_linea
                        self.crea_horas_espera(planta=srv.planta_id,
                                               importe=importe_linea, linea=srv, cantidad_hora_espera=hora_a_cobrar)

        vals['name'] = self.env['ir.sequence'].next_by_code('operativa.marfrig.sequence') or '/'
        vals['state'] = 'confirm'
        return self.write(vals)

    def _get_kg_symbol(self):
        curr_obj = self.env['res.currency']
        kg_symbol = curr_obj.search([('name', 'ilike', 'Kg')])
        if not kg_symbol:
            kg_symbol = curr_obj.create({'name': 'Kg', 'symbol': 'Kg', 'position': 'after'})
        self.kg_symbol = kg_symbol.id

    @api.depends('partner_invoice_id')
    def _compute_marfrig_name(self):
        cliente_obj = self.env['res.partner']
        cliente = cliente_obj.search([('name', 'ilike', 'Marfrig')], limit=1)
        self.partner_invoice_id = cliente.id

    def calculo_importe_planta(self, servicio, monto_a_repartir, kg_total, kg_planta, iteracion, servicios_topeados,
                               importes_por_servicio, monto_inicial):
        """
            Calculo y devuelvo el importe correpondiente a la planta recibida en la iteración
            actual.
        """
        def safe_division(dividendo, divisor):
            return dividendo / divisor if dividendo != 0 else 0

        # Calculo el tope que se le puede cobrar a la planta
        planta = servicio.planta_id
        pricelist_item_obj = self.env['product.pricelist.item']
        tarifa_planta = pricelist_item_obj.search([('planta_id', '=', planta.id)], limit=1)
        if not tarifa_planta:
            raise Warning('No se encontro tarifa para esa planta, revise %s' % planta.name)
        tope = tarifa_planta.sale_price
        # Si es la primer iteración caclulo el importe correspondiente segun la proporcion del peso y el monto inicial
        if iteracion == 1:
            importe = safe_division((monto_inicial * kg_planta), kg_total)
            if not importe and not servicio.product_id.name == 'Horas de Espera':

                raise Warning('Importe cero, Revise o Contante Departamento de desarollo')
            # Si supera el tope, el importe es el tope y el servicio queda topeado
            if importe > tope:
                importe = tope
                servicios_topeados.add(servicio.id)

        # Si es la segunda o tercera iteracion
        else:
            # Si el servicio está topeado devuelvo importe 0
            if servicio.id in servicios_topeados:
                importe = 0.0

            else:
                # Si no está topeado calculo la disponibilidad y la trato como el nuevo tope
                disponibilidad = tope - importes_por_servicio[servicio.id]
                importe = monto_a_repartir
                if importe > disponibilidad:
                    importe = disponibilidad
                    servicios_topeados.add(servicio.id)

        return importe

    @api.multi
    def generar_costos(self):
        for productos in self.mrf_srv_ids:
            if productos.product_type == 'terceros' and not productos.alquilado:
                if productos.supplier_id and productos.valor_compra_currency_id and productos.valor_compra:
                    if productos.supplier_ids:
                        productos.supplier_ids = False
                    productos.add_supplier_to_product_line()

    @api.multi
    def crea_factura(self, linea_planta, importe, producto_id, tarifa_planta):
        account = False
        delivery_order = ''
        inv_obj = self.env['account.invoice']
        lineas = []
        user = self.user_id.id
        journal_id = self.env['account.invoice'].default_get(['journal_id'])['journal_id']

        account_obj = self.env['account.account']
        planta_obj = self.env['marfrig.service.products']
        tax_obj = self.env['account.tax']
        tax = tax_obj.search([('name', '=', 'IVA Venta asimilado a exportación')])
        tax_hora_espera = tax_obj.search([('name', '=', 'IVA Ventas (22%)')])
        if linea_planta.product_id.name == 'Flete':
            account = account_obj.search([('code', '=', '41013001')])
        if linea_planta.product_id.name != 'Flete':
            account = account_obj.search([('code', '=', '41013003')])
        prods = []
        for line in linea_planta:
            delivery_order = line.purchase_number
            line_dict = {}
            line_dict['name'] = line.name + ' - Estadia en plaza' if line.product_id.name == 'Horas de Espera' else line.name
            line_dict['account_id'] = account.id
            if line.product_id.name == 'Horas de Espera':
                line_dict['price_unit'] = tarifa_planta.wait_value
            else:
                line_dict['price_unit'] = importe
            line_dict['uom_id'] = producto_id.uom_id.id
            line_dict['product_id'] = producto_id.id
            if line.product_id.name == 'Horas de Espera':
                line_dict['quantity'] = line.cantidad_hora_espera
            if line.product_id.name == 'Horas de Espera':
                line_dict['invoice_line_tax_ids'] = [(6, 0, tax_hora_espera.ids)]
            else:
                line_dict['invoice_line_tax_ids'] = [(6, 0, tax.ids)]
            lineas.append((0, 0, line_dict))
            prods.append(line.id)
            line.invoiced = True
            if line.invoiced_rejected:
                line.invoiced_rejected = False
        # Facturado
        invoice = inv_obj.create({
            'name': linea_planta.name or '',
            'origin': linea_planta.name,
            'type': 'out_invoice',
            'account_id': linea_planta.planta_id.property_account_receivable_id.id,
            'partner_id': linea_planta.planta_id.id,
            'journal_id': journal_id,
            'comment': delivery_order,
            'currency_id': linea_planta.mrf_srv_id.currency_id.id,
            'fiscal_position_id': linea_planta.planta_id.property_account_position_id.id,
            'company_id': linea_planta.mrf_srv_id.company_id.id,
            'user_id': user,
            'borrador_confirmado': linea_planta.mrf_srv_id.id,
            'invoice_line_ids': lineas
        })
        if prods:
            prods_obj = self.env['marfrig.service.products'].browse(prods)
            invoice.service_marfrig_ids += prods_obj

        partner = linea_planta.planta_id
        self.cargar_campos_impresion(partner, invoice)

        return invoice

    @api.multi
    def generar_facturas_marfrig(self):
        self.ensure_one()
        self.generar_costos()
        # servicios_con_planta_facturable = self.mrf_srv_ids.filtered(lambda x: bool(x.planta_id) and x.action_type_id.name == 'Viaje' and not x.hora_espera and x.is_invoiced)
        servicios_con_planta_facturable = self.mrf_srv_ids.filtered(lambda x: bool(x.planta_id) and x.action_type_id.name == 'Viaje' and x.is_invoiced)
        kg_total = self.container_kg
        if not kg_total:
            kg_total = self.container_kg = sum(self.mrf_srv_ids.mapped('kg_planta'))

        # Cuando es solo una planta, el valor de venta sale directo de la tarifa, no hay regla de tres
        sequencia_planta_unica = [1, 2, 3, 4, 5]
        pricelist_item_obj = self.env['product.pricelist.item']
        if self.pricelist_id.sequence in sequencia_planta_unica:
            for srv in servicios_con_planta_facturable:
                if not srv.invoiced or srv.invoiced_rejected:
                    if srv.hora_espera:
                        tarifa_planta = pricelist_item_obj.search(
                            [('planta_id', '=', srv.planta_id.id), ('sequence', 'in', sequencia_planta_unica)], limit=1)
                        invoice = self.crea_factura(linea_planta=srv, importe=srv.importe_linea, producto_id=srv.product_id, tarifa_planta=tarifa_planta)
                    else:
                        invoice = self.crea_factura(linea_planta=srv, importe=self.importe, producto_id=srv.product_id, tarifa_planta=False)
                    self.invoices_ids += invoice
                    self.state = 'invoiced'

        # Si hay más de una planta aplico el algoritmo de distribución
        else:
            importes_por_servicio = defaultdict(float)
            monto_a_repartir = self.importe
            monto_inicial = self.importe
            iterador_servicios = cycle(servicios_con_planta_facturable)
            servicios_visitados = set()
            servicios_topeados = set()

            # Mientras quede monto a repartir
            while monto_a_repartir > 0:
                # Obtengo el servicio del iterador ciclico
                srv = next(iterador_servicios)

                # Caclulo nro de iteracion
                iteracion = 1 if srv.id not in servicios_visitados else 2

                # Marco el servicio como visitado
                servicios_visitados.add(srv.id)

                # Calculo monto correspondiente al servicio en esta iteración y lo voy acumulando
                importe = self.calculo_importe_planta(servicio=srv, monto_a_repartir=monto_a_repartir, kg_total=kg_total,
                                                      kg_planta=srv.kg_planta, iteracion=iteracion,
                                                      servicios_topeados=servicios_topeados,
                                                      importes_por_servicio=importes_por_servicio,
                                                      monto_inicial=monto_inicial)

                # El importe caclulado en cada iteración se resta del monto a repartir y se le suma al servicio
                monto_a_repartir -= importe
                importes_por_servicio[srv.id] += importe

            # Creo las facturas para los montos calculados
            for srv in servicios_con_planta_facturable:
                if not srv.invoiced or srv.invoiced_rejected:
                    if srv.hora_espera:
                        if srv.id in importes_por_servicio:
                            importes_por_servicio.pop(srv.id)
                        tarifa_planta = pricelist_item_obj.search([('planta_id', '=', srv.planta_id.id), ('sequence', 'in', sequencia_planta_unica)], limit=1)
                        invoice = self.crea_factura(linea_planta=srv, importe=srv.importe_linea, producto_id=srv.product_id, tarifa_planta=tarifa_planta)
                        self.invoices_ids |= invoice

                    else:
                        invoice = self.crea_factura(linea_planta=srv, importe=importes_por_servicio[srv.id], producto_id=srv.product_id, tarifa_planta=False)
                        self.invoices_ids |= invoice
                        srv.importe_linea = importes_por_servicio[srv.id]

            # Marco el servicio base como facturado
            self.state = 'invoiced'

    @api.onchange('partner_invoice_id')
    def _onchange_partner_id(self):
        domain = {}
        warning = {}
        res = {}
        pricelist_obj = self.env['product.pricelist.item']
        if self.partner_invoice_id:
            partner_id = self.partner_invoice_id.id
            pricelist = pricelist_obj.search([('partner_id', '=', partner_id)])

            if not pricelist:
                self.pricelist_id = False
                warning = {
                    'title': ("Alerta para %s") % self.partner_invoice_id.name,
                    'message': "No se encontró Tarifa para el cliente"
                }
            if len(pricelist) == 1:
                self.pricelist_id = pricelist.id


            domain = {'pricelist_id': [('id', 'in', pricelist.ids)]}
        if warning:
            res['warning'] = warning
        if domain:
            res['domain'] = domain
        return res

    @api.onchange('pricelist_id')
    @api.multi
    def onchange_pricelist_id(self):
        for rec in self:
            if rec.pricelist_id:
                rec.importe = rec.pricelist_id.sale_price
                rec.currency_id = rec.pricelist_id.currency_id.id
                rec.currency_id_chofer = rec.pricelist_id.comision_chofer_currency_id.id
                rec.partner_seller_id = rec.pricelist_id.partner_seller_id.id
                rec.seller_commission = rec.pricelist_id.comision_vendedor
                rec.currency_id_vendedor = rec.pricelist_id.comision_vendedor_currency_id.id

    @api.onchange('container_number')
    def check_container_number(self):
        for rec in self:
            #Valida existencia
            if rec.container_number != False:
                #Valida largo correcto
                if len(rec.container_number) != 13:
                    rec.container_number = False
                    return {'warning': {'title': "Error", 'message': "Se espera un número de 13 cifras ej: BMOU-123456-7"}}
                #Valida existencia de - para poder realizar split
                if rec.container_number.count('-') != 2:
                    rec.container_number = False
                    return {'warning': {'title': "Error", 'message': "Formato inválido, se espera BMOU-123456-7"}}
                #letras_c,numeros_c,digitov_c = rec.container_number.split("-") Si es necesario utlizar para verificar otras cosas
                string_container,numeros_container,digitov_container = rec.container_number.split("-")
                if not string_container.isalpha():
                    rec.container_number = False
                    return {'warning': {'title': "Error", 'message': "Se espera un número de 13 cifras ej: BMOU-123456-7"}}
                try:
                    type(int(numeros_container)) == int
                except ValueError:
                    rec.container_number = False
                    return {'warning': {'title': "Error", 'message': "Se espera un número de 13 cifras ej: BMOU-123456-7"}}
                try:
                    type(int(numeros_container)) == int
                except ValueError:
                    rec.container_number = False
                    return {
                        'warning': {'title': "Error", 'message': "Se espera un número de 13 cifras ej: BMOU-123456-7"}}
                try:
                    type(int(digitov_container)) == int
                except ValueError:
                    rec.container_number = False
                    return {
                        'warning': {'title': "Error", 'message': "Se espera un número de 13 cifras ej: BMOU-123456-7"}}
                #validar el numero con el algoritmo iso6346
                container_number = rec.container_number.replace('-', '')
                if not iso6346.is_valid(container_number):
                    rec.container_number = False
                    rec.valid_cointaner_number_text = False
                    rec.invalid_cointaner_number_text = True
                else:
                    rec.valid_cointaner_number_text = True
                    rec.invalid_cointaner_number_text = False

    @api.onchange('container_number_exception')
    def check_container_number_exception(self):
        for rec in self:
            # Valida existencia
            if rec.container_number_exception != False:
                # Valida largo correcto
                if len(rec.container_number_exception) != 13:
                    rec.container_number_exception = False
                    return {
                        'warning': {'title': "Error", 'message': "Se espera un número de 13 cifras ej: BMOU-123456-7"}}
                # Valida existencia de - para poder realizar split
                if rec.container_number_exception.count('-') != 2:
                    rec.container_number_exception = False
                    return {'warning': {'title': "Error", 'message': "Formato inválido, se espera BMOU-123456-7"}}
                # letras_c,numeros_c,digitov_c = rec.container_number_exception.split("-") Si es necesario utlizar para verificar otras cosas
                string_container, numeros_container, digitov_container = rec.container_number_exception.split("-")
                if not string_container.isalpha():
                    rec.container_number_exception = False
                    return {
                        'warning': {'title': "Error", 'message': "Se espera un número de 13 cifras ej: BMOU-123456-7"}}
                try:
                    type(int(numeros_container)) == int
                except ValueError:
                    rec.container_number_exception = False
                    return {
                        'warning': {'title': "Error", 'message': "Se espera un número de 13 cifras ej: BMOU-123456-7"}}
                try:
                    type(int(numeros_container)) == int
                except ValueError:
                    rec.container_number_exception = False
                    return {
                        'warning': {'title': "Error", 'message': "Se espera un número de 13 cifras ej: BMOU-123456-7"}}
                try:
                    type(int(digitov_container)) == int
                except ValueError:
                    rec.container_number_exception = False
                    return {
                        'warning': {'title': "Error", 'message': "Se espera un número de 13 cifras ej: BMOU-123456-7"}}

    @api.multi
    def get_container_number(self):
        for rec in self:
            rec.make_container_number_invisible = True
        return

    @api.multi
    def cancel_get_container_number(self):
        for rec in self:
            rec.make_container_number_invisible = False
        return

    @api.onchange('dua_aduana')
    def check_mes(self):
        for rec in self:
            # 3 es el largo esperado
            if rec.dua_aduana:
                if len(rec.dua_aduana) != 3:
                    rec.dua_aduana = False
                    return {'warning': {'title': "Error", 'message': "Se espera un número de 3 cifras ej: 001"}}

    @api.onchange('dua_anio','dua_numero')
    def check_anio(self):
        for rec in self:
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
            # 6 es el largo esperado
            if rec.dua_numero != False:
                if len(rec.dua_numero) != 6:
                    rec.dua_numero = False
                    return {'warning': {'title': "Error", 'message': "Se espera un número de 6 cifras ej: 457882"}}
            # Validar regimen
            int_dua = int(rec.dua_numero)
            if int_dua not in dua_exportaciones:
                if int_dua in dua_transitos:
                    dua_type = '700000 - 999999 - Transitos'
                if int_dua in dua_importaciones:
                    dua_type = '000001 - 499999 - Importaciones'
                if rec.dua_numero != False:
                    rec.dua_numero = False
                    return {'warning': {'title': "Error",
                                        'message': 'DUA inválido para el Regimen EXPO \n El DUA ingresado corresponde al regimen  %s' % dua_type}}

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
            if int_dua not in dua_exportaciones:
                if int_dua in dua_transitos:
                    dua_type = '700000 - 999999 - Transitos'
                if int_dua in dua_importaciones:
                    dua_type = '000001 - 499999 - Importaciones'
                    self.dua_numero = False
                    return {'warning': {'title': "Error", 'message': 'DUA inválido para el Regimen EXPO \n El DUA ingresado corresponde al regimen  %s' % dua_type}}
        if self.dua_anio:
            if not self.dua_anionumero:
                self.dua_anionumero = self.dua_anio + self.dua_numero

    @api.multi
    @api.onchange('container_kg', 'container_type', 'dangers_loads')
    def get_pricelist_item(self):
        pricelist_item_obj = self.env['product.pricelist.item']
        condiciones_busqueda = [('active', '=', True)]
        if self.container_type.size == 20:
            if self.container_kg:
                condiciones_busqueda.append(('kg_from', '<=', self.container_kg))
                condiciones_busqueda.append(('kg_to', '>=', self.container_kg))

        else:
            condiciones_busqueda.append(('size_from', '<=', self.container_type.size))
            condiciones_busqueda.append(('size_to', '>=', self.container_type.size))

    @api.onchange('container_type')
    def onchange_container_type(self):
        for rec in self:
            if rec.container_type.license_plate == '20FR':
                rec.payload = 32500
            if rec.container_type.license_plate == '20OT':
                rec.payload = 28120
            if rec.container_type.license_plate == '20RF':
                rec.payload = 30480
            if rec.container_type.license_plate == '20STD':
                rec.payload = 30480
            # if rec.container_type.license_plate == '40FR-HC':
            #     rec.payload = 4030
            if rec.container_type.license_plate == '40HC':
                rec.payload = 28560
            if rec.container_type.license_plate == '40OT':
                rec.payload = 32500
            # if rec.container_type.license_plate == '40OT-HC':
            #     rec.payload = 0
            if rec.container_type.license_plate == '40RF':
                rec.payload = 32500
            if rec.container_type.license_plate == '40RF-HC':
                rec.payload = 29150
            if rec.container_type.license_plate == '40STD':
                rec.payload = 28750
        return

    def _compute_line_data_for_template_change(self, line):

        data = {
            'planta_id': line.planta_id.id,
            'product_id': line.product_id.id,
            'action_type_id': line.action_type_id.id,
            'origin_id': line.origin_id.id,
            'destiny_id': line.destiny_id.id,
            'name': line.name,
            'es_retiro_vacio': True if line.action_type_id.name == 'Retiro de Vacío' else False,
            'flete_viaje': True if line.product_id.name == 'Flete' and line.action_type_id.name == 'Viaje' else False
        }

        return data

    @api.onchange('service_template_id')
    def onchange_service_template_id(self):
        if not self.service_template_id:
            return
        #Primero Vaciamos
        if self.mrf_srv_ids:
            self.mrf_srv_ids = False

        template = self.service_template_id
        self.partner_invoice_id = template.partner_invoice_id.id
        self.output_reference = template.output_reference
        self.pricelist_id = template.pricelist_id.id
        self.currency_id = template.currency_id.id
        self.importe = template.importe
        self.partner_seller_id = template.partner_seller_id.id
        self.seller_commission = template.seller_commission
        self.aduana_destino_id = template.aduana_destino_id.id

        order_lines = [(5, 0, 0)]
        for line in template.mrf_srv_tmlp_ids:
            data = self._compute_line_data_for_template_change(line)
            order_lines.append((0, 0, data))
        self.mrf_srv_ids = order_lines