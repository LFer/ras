from odoo import api, fields, models
import ipdb
from stdnum import iso6346
import datetime
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning

class marfrig_service_base(models.Model):
    _name = "deposito.service.base"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _description = "Deposito"
    _order = "id DESC"

    @api.depends('invoices_ids', 'invoice_count')
    def _compute_invoice(self):
        return

    name = fields.Char(default='Borrador')
    referencia = fields.Char(defualt='Referencia de Carpeta')
    stock_operation = fields.Many2one(comodel_name='stock.picking', string='Movimiento Deposito')
    user_id = fields.Many2one('res.users', string='Usuario', default=lambda self: self.env.user, track_visibility="onchange")
    company_id = fields.Many2one('res.company', string='Compañia', default=lambda self: self.env.user.company_id)
    partner_invoice_id = fields.Many2one(comodel_name='res.partner', string='Cliente', domain=[('customer', '=', True)])
    pricelist_id = fields.Many2one('product.pricelist', string='Tarifa')
    currency_id = fields.Many2one(comodel_name="res.currency", string="Moneda", related="pricelist_id.currency_id",
                                  index=True, readonly=True, store=True)
    start_datetime = fields.Datetime(string='Fecha Inicio', required=True, index=True, copy=False,
                                     default=fields.datetime.now())
    stop_datetime = fields.Datetime('Fecha Fin', index=True, copy=False)
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('confirm', 'Confirmado'),
        ('inprocess', 'En proceso'),
        ('invoiced', 'Facturado'),
        ('invoice_rejected', 'Fac. Rechazada'),
        ('cancel', 'Cancelado'),
        ('done', 'Realizado'),
    ], string='Status', index=True, readonly=True, default='draft', track_visibility='onchange', copy=False, store=True)
    dua_aduana = fields.Char(string='Mes', size=3)
    dua_anio = fields.Char(string='Año', size=4)
    dua_numero = fields.Char(string='Dua_Numero', size=6)
    deposito_srv_ids = fields.One2many('deposito.service.products', 'deposito_srv_id', string='Servicios', copy=True)
    aduana_destino_id = fields.Many2one('fronteras', 'Aduana Destino')
    origin_id = fields.Many2one(comodel_name='res.partner.address.ext', string='Origen')
    destiny_id = fields.Many2one(comodel_name='res.partner.address.ext', string='Destino')
    invoices_ids = fields.One2many('account.invoice', 'deposito_operation_id', string='Facturas de Clientes',
                                   domain=[('type', '=', 'out_invoice')])
    invoice_count = fields.Integer(compute="_compute_invoice", string='Conteo de Facturas', copy=False, default=0,
                                   store=True)
    suppliers_invoices_ids = fields.Many2many('account.invoice', string='Facturas de Proveedor', copy=False)
    invoice_id = fields.Many2one('account.invoice')

    @api.multi
    def draft_confirm(self):
        return self.write({'state': 'confirm', 'name': self.env['ir.sequence'].next_by_code('service.deposito') or '/'})

    @api.multi
    def confirm_inprocess(self):
        return self.write({'state': 'inprocess'})

    @api.multi
    def confirm_cancel(self):
        return self.write({'state': 'cancel'})

    @api.multi
    def cancel_draft(self):
        return self.write({'state': 'draft'})

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
        if not self.invoices_ids:
            raise Warning('No tiene Facturas creadas aún')
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

    def show_service_lines(self):
        context = self._context.copy()
        srv_ids = self.ids
        act_window = self.env['ir.actions.act_window']
        wizard = self
        # open the list view of service product to invoice
        res = act_window.for_xml_id('deposito', 'action_consolidado_servicio_tree')
        # context
        res['context'] = {
            'search_default_uninvoiced': 1,
        }
        products_obj = self.env['producto.servicio.camion']
        ids_guardadas = []
        if self.productos_servicios_camion_ids:
            for prod in self.productos_servicios_camion_ids:
                if prod.is_invoiced and not prod.invoiced:
                    ids_guardadas.append(prod.id)

        if self.cargas_ids:
            for prod in self.cargas_ids:
                for cg in prod.producto_servicio_carga_ids:
                    if cg.is_invoiced and not cg.invoiced:
                        ids_guardadas.append(cg.id)
        # domain
        if srv_ids:
            if not res.get('domain', False) or not isinstance(res.get('domain', False), (list,)):
                res['domain'] = []
            # res['domain'].append(('camion_id', 'in', srv_ids))
            res['domain'].append(('id', 'in', ids_guardadas))
            res['domain'].append(('invoiced', '=', False))
            res['domain'].append(('is_invoiced', '=', True))
        return res

class deposito_serivice_products(models.Model):
        _name = "deposito.service.products"
        _description = "Servicios Deposito"
        _order = "id ASC"

        name = fields.Char()
        deposito_srv_id = fields.Many2one(comodel_name='deposito.service.base', string='Carpeta Relacionada')
        state = fields.Selection([
            ('draft', 'Borrador'),
            ('confirm', 'Confirmado'),
            ('inprocess', 'En proceso'),
            ('cancel', 'Cancelado'),
            ('done', 'Realizado'),
        ], string='Status', index=True, readonly=True, default='draft',
            track_visibility='onchange', copy=False,
        )
        product_type = fields.Selection([('propio', 'Propio'), ('terceros', 'Terceros')], string='Origen del Servicio')
        partner_invoice_id = fields.Many2one(comodel_name='res.partner', string='Cliente')
        pricelist_id = fields.Many2one('product.pricelist.item', string='Tarifa')
        product_id = fields.Many2one(comodel_name='product.product', string='Servicio',
                                     domain=[('product_tmpl_id.type', '=', 'service'), ('sale_ok', '=', True)],
                                     required=False, change_default=True, ondelete='restrict')
        supplier_id = fields.Many2one(comodel_name='res.partner', string='Proveedor',
                                      domain=[('supplier', '=', True)])
        origin_id = fields.Many2one(comodel_name='res.partner.address.ext', string='Origen')
        destiny_id = fields.Many2one(comodel_name='res.partner.address.ext', string='Destino')
        matricula = fields.Char(string=u'Matricula')
        matricula_dos_id = fields.Many2one(comodel_name='fleet.vehicle', string=u'Matrícula dos')
        vehicle_id = fields.Many2one(comodel_name='fleet.vehicle', string=u'Matrícula',
                                     domain=[('is_ras_property', '=', True)])
        vehicle_type = fields.Selection(related='vehicle_id.vehicle_type', type='char', readonly=True)
        driver_id = fields.Many2one('hr.employee', 'Chofer', help=u'Chofer del Vehículo')
        chofer = fields.Char('Chofer')
        matricula_dos_fletero = fields.Char(string='Matricula Dos Fletero')
        matricula_fletero = fields.Many2one(comodel_name='fleet.vehicle', string='Matricula Fletero',
                                            domain=[('is_ras_property', '=', False)])
        currency_id = fields.Many2one(comodel_name='res.currency', string='Moneda')
        importe = fields.Float(string='Importe')
        valor_compra_currency_id = fields.Many2one(comodel_name='res.currency', string='Moneda Compra')
        valor_compra = fields.Monetary(string='Valor Compra', currency_field='valor_compra_currency_id')
        currency_id_chofer = fields.Many2one(comodel_name='res.currency', string='Moneda Comisión Chofer')
        driver_commission = fields.Float('Comisión de chofer')

        is_invoiced = fields.Boolean('Facturable', help='Marque esta casilla si este servicio no se factura',
                                     default=True)
        is_outgoing = fields.Boolean('¿Es Gasto?', help='Marque esta casilla si este servicio es un Gasto',
                                     default=True)
        invoiced = fields.Boolean(string='¿Facturado?', copy=False)
        oc = fields.Char(string='Orden de Compra')
        invoiced_rejected = fields.Boolean(string='Factura Rechazada')
        supplier_ids = fields.One2many('rt.service.product.supplier', 'rt_deposito_product_id', 'Proveedores', copy=True)
        start = fields.Datetime('Inicio', required=True)
        stop = fields.Datetime('Fin', required=True)
        action_type_id = fields.Many2one('tipo.accion', string="Tipo de Acción")
        alquilado = fields.Boolean(string='Alquilado', track_visibility='always')
        partner_seller_id = fields.Many2one(comodel_name='res.partner', string='Vendedor',
                                            domain=[('seller', '=', True)], track_visibility='always')
        currency_id_vendedor = fields.Many2one(comodel_name='res.currency', string='Moneda', track_visibility='always')
        seller_commission = fields.Float(string='Comisión Vendedor', track_visibility='always')
        load_type = fields.Selection(
            [('bulk', 'Bulk-Carga Suelta'), ('contenedor', 'Contenedor'), ('liquido_granel', u'Granel Líquido'),
             ('solido_granel', u'Granel Solido')], string='Tipo de Carga')
        container_type = fields.Many2one(comodel_name='fleet.vehicle', string='Tipo de Contenedor')
        container_number = fields.Char(string=u'Número de contenedor', size=13)
        make_container_number_invisible = fields.Boolean(string='Exception', default=False)
        container_number_exception = fields.Char(string=u'Nº de contenedor Excepción', size=13)
        valid_cointaner_number_text = fields.Boolean(
            help='Este booleano es para que se muestre un texto si el número de container es válido')
        invalid_cointaner_number_text = fields.Boolean(
            help='Este booleano es para que se muestre un texto si el número de container no es válido')


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
            else:
                linea.add_driver_commission()

        @api.onchange('product_type', 'vehicle_id', 'matricula_dos_id')
        def _onchange_vehicle(self):
            """
            Funcion temporaria que impide al usuario cargas vehiculos que no debe
            :return:
            """
            domain = {}
            res = {}
            employee_obj = self.env['hr.employee']
            condiciones_busqueda = []
            condiciones_busqueda.append(('category_ids.name', '=', 'Chofer'))
            if condiciones_busqueda:
                employee = employee_obj.search(condiciones_busqueda)
            else:
                employee = employee_obj.search([])

            fleet_obj = self.env['fleet.vehicle']
            fleet_vehicle_id = fleet_obj.search([('state_id', 'in', ('Tractores', 'Camiones', 'Camionetas'))])
            fleet_matricula_dos_id = fleet_obj.search([('state_id', 'in', 'Semi Remolques y Remolques')])

            domain = {
                'driver_id': [('id', 'in', employee.ids)],
                'matricula_dos_id': [('id', 'in', fleet_matricula_dos_id.ids)],
                'vehicle_id': [('id', 'in', fleet_vehicle_id.ids)],
            }

            if self.vehicle_id:
                if self.vehicle_id.state_id.name not in ('Tractores', 'Camiones', 'Camionetas'):
                    self.vehicle_id = False
                    raise Warning(
                        'El vehiculo debe tener una matricula \n No puede elegir un contenedor \n Selecione: Tractores, Camiones o Camionetas')

            if self.matricula_dos_id:
                if self.matricula_dos_id.state_id.name not in ('Semi Remolques y Remolques'):
                    self.matricula_dos_id = False
                    raise Warning('Solo puede selecionar Semi Remolques y Remolques')

            if self.vehicle_id:
                self.driver_id = self.vehicle_id.driver_id.id

            if not self.currency_id_chofer:
                self.currency_id_chofer = 46

            if domain:
                res['domain'] = domain
            return res

        @api.onchange('container_number')
        def check_container_number(self):
            for rec in self:
                # Valida existencia
                if rec.container_number != False:
                    # Valida largo correcto
                    if len(rec.container_number) != 13:
                        rec.container_number = False
                        return {'warning': {'title': "Error",
                                            'message': "Se espera un número de 13 cifras ej: BMOU-123456-7"}}
                    # Valida existencia de - para poder realizar split
                    if rec.container_number.count('-') != 2:
                        rec.container_number = False
                        return {'warning': {'title': "Error", 'message': "Formato inválido, se espera BMOU-123456-7"}}
                    # letras_c,numeros_c,digitov_c = rec.container_number.split("-") Si es necesario utlizar para verificar otras cosas
                    string_container, numeros_container, digitov_container = rec.container_number.split("-")
                    if not string_container.isalpha():
                        rec.container_number = False
                        return {'warning': {'title': "Error",
                                            'message': "Se espera un número de 13 cifras ej: BMOU-123456-7"}}
                    try:
                        type(int(numeros_container)) == int
                    except ValueError:
                        rec.container_number = False
                        return {'warning': {'title': "Error",
                                            'message': "Se espera un número de 13 cifras ej: BMOU-123456-7"}}
                    try:
                        type(int(numeros_container)) == int
                    except ValueError:
                        rec.container_number = False
                        return {
                            'warning': {'title': "Error",
                                        'message': "Se espera un número de 13 cifras ej: BMOU-123456-7"}}
                    try:
                        type(int(digitov_container)) == int
                    except ValueError:
                        rec.container_number = False
                        return {
                            'warning': {'title': "Error",
                                        'message': "Se espera un número de 13 cifras ej: BMOU-123456-7"}}
                    # validar el numero con el algoritmo iso6346
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
                            'warning': {'title': "Error",
                                        'message': "Se espera un número de 13 cifras ej: BMOU-123456-7"}}
                    # Valida existencia de - para poder realizar split
                    if rec.container_number_exception.count('-') != 2:
                        rec.container_number_exception = False
                        return {'warning': {'title': "Error", 'message': "Formato inválido, se espera BMOU-123456-7"}}
                    # letras_c,numeros_c,digitov_c = rec.container_number_exception.split("-") Si es necesario utlizar para verificar otras cosas
                    string_container, numeros_container, digitov_container = rec.container_number_exception.split("-")
                    if not string_container.isalpha():
                        rec.container_number_exception = False
                        return {
                            'warning': {'title': "Error",
                                        'message': "Se espera un número de 13 cifras ej: BMOU-123456-7"}}
                    try:
                        type(int(numeros_container)) == int
                    except ValueError:
                        rec.container_number_exception = False
                        return {
                            'warning': {'title': "Error",
                                        'message': "Se espera un número de 13 cifras ej: BMOU-123456-7"}}
                    try:
                        type(int(numeros_container)) == int
                    except ValueError:
                        rec.container_number_exception = False
                        return {
                            'warning': {'title': "Error",
                                        'message': "Se espera un número de 13 cifras ej: BMOU-123456-7"}}
                    try:
                        type(int(digitov_container)) == int
                    except ValueError:
                        rec.container_number_exception = False
                        return {
                            'warning': {'title': "Error",
                                        'message': "Se espera un número de 13 cifras ej: BMOU-123456-7"}}

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

        @api.onchange('load_type')
        def _onchange_load_type(self):
            domain = {}
            warning = {}
            res = {}
            vehicles_obj = self.env['fleet.vehicle']
            contenedores = vehicles_obj.search([('vehicle_type', '=', 'container')]).ids
            domain = {'container_type': [('id', 'in', contenedores)]}

            if warning:
                res['warning'] = warning
            if domain:
                res['domain'] = domain
            return res

        @api.multi
        def add_supplier_to_product_line(self):
            if self._module:
                if self._module == 'deposito':
                    tax_obj = self.env['account.tax']
                    taxes = tax_obj.search([('name', '=', 'IVA Directo Op  Grav B')])
                    if self.product_id.name == 'Alquiler':
                        taxes = tax_obj.search([('name', '=', 'Compras Exentos IVA')])
                    lineas = []
                    for rec in self:
                        line_dict = {}
                        line_dict['deposito_id'] = rec.deposito_srv_id.id
                        line_dict['supplier_id'] = rec.supplier_id.id
                        line_dict['currency_id'] = rec.valor_compra_currency_id.id
                        line_dict['amount'] = rec.valor_compra


                        if self.product_id.name == 'Alquiler':
                            line_dict['price_subtotal'] = rec.valor_compra
                        else:
                            line_dict['price_subtotal'] = rec.valor_compra * 1.22
                        line_dict['ref'] = self.deposito_srv_id.referencia
                        line_dict['rt_service_id'] = False
                        line_dict['rt_consol_product_id'] = False
                        line_dict['rt_marfrig_product_id'] = False
                        line_dict['rt_deposito_product_id'] = self.id
                        line_dict['service_state'] = rec.state
                        line_dict['tax_ids'] = [(6, 0, taxes.ids)]
                        line_dict['service_date'] = rec.start
                        # line_dict['tack_id'] = rec.container_number
                        # line_dict['dua'] = self.get_dua()
                        # line_dict['mic'] = ' '
                        line_dict['origin_id'] = rec.origin_id.id
                        line_dict['destiny_id'] = rec.destiny_id.id
                        line_dict['product_id'] = rec.product_id.id
                        line_dict['output_reference'] = self.name
                        line_dict['partner_invoice_id'] = self.deposito_srv_id.partner_invoice_id.id
                        lineas.append((0, 0, line_dict))

                    self.supplier_ids = lineas

