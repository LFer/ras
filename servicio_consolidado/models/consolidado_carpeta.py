import logging
from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
import ipdb
from odoo.exceptions import UserError, RedirectWarning, Warning
_logger = logging.getLogger(__name__)
from odoo import api, fields, models, tools, SUPERUSER_ID
from stdnum import iso6346
import datetime
AVAILABLE_PRIORITIES = [
    ('0', 'Low'),
    ('1', 'Medium'),
    ('2', 'High'),
    ('3', 'Very High'),
]


class CarpetaCamion(models.Model):
    _name = "carpeta.camion"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'rating.mixin']
    _description = "Camiones para la vista Kanban"
    _order = "id ASC"

    @api.depends('invoices_ids', 'invoice_count')
    def compute_invoice(self):
        for order in self:
            invoices = self.env['account.invoice']
            inves = invoices.search([('camion_id', '=', order.id)])
            order.invoice_count = len(inves)

    @api.one
    @api.depends('cargas_ids.package', 'cargas_ids.raw_kg', 'cargas_ids.volume', 'cargas_ids.market_value', 'cargas_ids.make_factura_invisible')
    def _compute_consol_totals(self):
        self.volume_total = sum(line.volume for line in self.cargas_ids)
        self.kg_total = sum(line.raw_kg for line in self.cargas_ids)
        self.package_total = sum(line.package for line in self.cargas_ids)
        self.market_value_total = sum(line.market_value for line in self.cargas_ids)
        for carga in self.cargas_ids:
            if carga.make_factura_invisible:
                for inv in carga.factura_carga_ids:
                    self.market_value_currency_id = inv.market_value_currency_id.id
                    self.market_value_total += inv.market_value


    @api.multi
    def _get_operation_type(self):

        operation_international = [('transit_inter_in', '80 - Transito Internacional Ingreso'),
                                   ('transit_inter_out', '80 - Transito Internacional Salida'),
                                   ('impo_inter', '10 - IMPO Internacional'),
                                   ('expo_inter', '40 - EXPO Internacional')]

        return operation_international

    name = fields.Char(string='Nombre')
    regimen = fields.Selection(_get_operation_type, string="Regimen", store=True)
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('confirm', 'Confirmado'),
        ('inprocess', 'En proceso'),
        ('progress_national', 'Servicio Facturado Nacional'),
        ('progress_international', 'Servicio Facturado Internacional'),
        ('progress', 'Servicio Facturado'),
        ('rejected', 'Factura Rechazada'),
        ('cancel', 'Cancelado'),
        ('done', 'Realizado'),
    ], string='Status', index=True, readonly=True, default='draft',
        track_visibility='onchange', copy=False,
        help=" * The 'Draft' status is used when a user is encoding a new and unconfirmed Invoice.\n"
             " * The 'Open' status is used when user creates invoice, an invoice number is generated. It stays in the open status till the user pays the invoice.\n"
             " * The 'Paid' status is set automatically when the invoice is paid. Its related journal entries may or may not be reconciled.\n"
             " * The 'Cancelled' status is used when user cancel invoice.")
    active = fields.Boolean(string='Activo', default=True)
    crt_number = fields.Char(string='Numero CRT')
    mic_number = fields.Char(string='Numero MIC')
    invoices_ids = fields.One2many('account.invoice', 'camion_id', string='Facturas de Cliente', domain=[('type', '=', 'out_invoice')])
    matricula_dos_id = fields.Many2one(comodel_name='fleet.vehicle', string=u'Matrícula dos', domain=[('vehicle_type', '=', 'semi_tow')])
    vehicle_id = fields.Many2one(comodel_name='fleet.vehicle', string=u'Matrícula', domain=[('vehicle_type', 'in', ('truck', 'tractor', 'camioneta'))])
    matricula_fletero = fields.Many2one(comodel_name='fleet.vehicle', string='Matricula Fletero', domain=[('is_ras_property', '=', False)])
    matricula_dos_fletero = fields.Char(string='Matricula Dos Fletero')
    chofer = fields.Char('Chofer')
    product_type = fields.Selection([('propio', 'Propio'), ('terceros', 'Terceros')], string='Origen del Servicio')  # Este campo va determinar muchisimos comportamientos
    productos_servicios_camion_ids = fields.One2many('producto.servicio.camion', 'camion_id', 'Servicios', domain=[('rt_carga_id', '=', False)], copy=True)
    user_id = fields.Many2one('res.users', string='Usuario', default=lambda self: self.env.user,track_visibility="onchange")
    cargas_ids = fields.One2many('carga.camion', 'camion_id', 'Cargas', copy=True)
    mensaje_simplificado = fields.Char(string='MS')
    company_id = fields.Many2one('res.company', string='Compañia', default=lambda self: self.env.user.company_id)
    dua_cabezal = fields.Char(string='DUA')
    dua_aduana = fields.Char(string= 'Mes', size=3)
    dua_anio = fields.Char(string='Año', size=4)
    dua_numero = fields.Char(string='Dua_Numero', size=6)
    dua_anionumero = fields.Char()
    route = fields.Text(string='Rutas')
    partner_id = fields.Many2one(comodel_name='res.partner', string='Origen del Consolidado')
    partner_invoice_id = fields.Many2one(comodel_name='res.partner', string='Cliente a facturar', domain=[('customer', '=', True)])
    partner_dispatcher_id = fields.Many2one(comodel_name='res.partner', string='Despachante', domain=[('dispatcher', '=', True)])
    pricelist_id = fields.Many2one(comodel_name='product.pricelist', string='Tarifa')
    currency_id = fields.Many2one(comodel_name="res.currency", string="Moneda", related="pricelist_id.currency_id", index=True, readonly=True, store=True)
    start_datetime = fields.Datetime(string='Fecha Inicio', required=True, index=True, copy=False, default=fields.datetime.now())
    stop_datetime = fields.Datetime('Fecha Fin', index=True, copy=False)
    make_page_invisible = fields.Boolean(help='Este booleano es para hacer invisible la pagina si no se cargo regimen, cliente a facturar')
    make_mic_number_readonly = fields.Boolean()
    #Informacion del consolidado
    kg_total = fields.Float('Kg', compute='_compute_consol_totals', store=True)#, multi='_totals')
    market_value_total = fields.Float('Valor de mercadería', compute='_compute_consol_totals', store=True)#, multi='_totals')
    volume_total = fields.Float('Volumen', compute='_compute_consol_totals', store=True)#, multi='_totals')
    market_value_cap = fields.Float('Valor de mercadería')
    market_value_total_indicator = fields.Float('Market Value')#, compute='_compute_consol_totals', store=True,multi='_totals')
    market_value = fields.Float(string='Valor de la Mercaderia')
    package_total = fields.Float('Bultos', compute='_compute_consol_totals', store=True)#, multi='_totals'),
    package_total_indicator = fields.Float('Bultos')#, compute='_compute_consol_totals', store=True, multi='_totals'),
    package_cap = fields.Float('Bultos')
    kg_cap = fields.Float('Kg')
    volume_cap = fields.Float('Volumen')
    volume_total_indicator = fields.Float('Volume')#, compute='_compute_consol_totals', store=True, multi='_totals'),
    kg_total_indicator = fields.Float('Kg')#, compute='_compute_consol_totals', store=True, multi='_totals'),
    driver_commission = fields.Float('Comisión de chofer')
    currency_id_chofer = fields.Many2one(comodel_name='res.currency', string='Moneda Cmision Chofer')
    driver_id = fields.Many2one('hr.employee', 'Chofer', help=u'Chofer del Vehículo')
    qty_cargas = fields.Integer(string='Cantidad de Cargas', help='Cantidad de cargas a generar de forma automática')
    market_value_currency_id = fields.Many2one(comodel_name='res.currency')
    invoice_count = fields.Integer(compute="compute_invoice", string='Conteo de Facturas', copy=False, default=0, store=True)
    aduana_origen_id = fields.Many2one('fronteras', 'Aduana Origen')
    aduana_destino_id = fields.Many2one('fronteras', 'Aduana Destino')
    suppliers_invoices_ids = fields.Many2many('account.invoice')
    invoice_id = fields.Many2one('account.invoice')

    _sql_constraints = [
        ('dua_anio_unique', 'unique(dua_anionumero)', "NO puede haber dos numeros de DUA iguales en el mismo año!"),
    ]

    @api.onchange('aduana_origen_id', 'aduana_destino_id')
    def carga_aduans(self):
        if self.aduana_origen_id:
            for carga in self.cargas_ids:
                carga.aduana_origen_id = self.aduana_origen_id.id
        if self.aduana_destino_id:
            for carga in self.cargas_ids:
                carga.aduana_destino_id = self.aduana_destino_id.id

    @api.multi
    def get_crt_number(self):
        for rec in self:
            sequence_crt = ''
            if rec.regimen == 'transit_inter_out' or rec.regimen == 'transit_inter_out' or rec.regimen == 'impo_inter' or rec.regimen == 'expo_inter':
                sequence_crt = 'UY'
                if rec.camion_id.aduana_destino_id.country_id.name == 'Argentina':
                    rec.crt_number += '1448'
                    anio = str(datetime.datetime.today().year)
                    rec.crt_number += anio[2:4]
                    sequence_crt_argentina = self.env['ir.sequence'].next_by_code('rt.service.crt.argentina')
                    rec.crt_number += sequence_crt_argentina
                if rec.camion_id.aduana_destino_id.country_id.name == 'Paraguay':
                    rec.crt_number += '1476'
                    anio = str(datetime.datetime.today().year)
                    rec.crt_number += anio[2:4]
                    sequence_crt_paraguay = self.env['ir.sequence'].next_by_code('rt.service.crt.paraguay')
                    rec.crt_number += sequence_crt_paraguay
                if rec.camion_id.aduana_destino_id.country_id.name == 'Brasil':
                    rec.crt_number += '1554'
                    anio = str(datetime.datetime.today().year)
                    rec.crt_number += anio[2:4]
                    sequence_crt_brasil = self.env['ir.sequence'].next_by_code('rt.service.crt.brasil')
                    rec.crt_number += sequence_crt_brasil
            for carga in rec.cargas_ids:
                carga.crt_number = sequence_crt

    @api.multi
    def get_mic_number(self):
        for rec in self:
            if rec.regimen == 'transit_inter_out' or rec.regimen == 'transit_inter_out' or rec.regimen == 'impo_inter' or rec.regimen == 'expo_inter':
                rec.mic_number = 'UY'
                if rec.aduana_destino_id.country_id.name == 'Argentina':
                    rec.mic_number += '1448'
                    anio = str(datetime.datetime.today().year)
                    rec.mic_number += anio[2:4]
                    sequence_mic_argentina = self.env['ir.sequence'].next_by_code('rt.service.mic.argentina')
                    rec.mic_number += sequence_mic_argentina
                if rec.aduana_destino_id.country_id.name == 'Paraguay':
                    rec.mic_number += '1476'
                    anio = str(datetime.datetime.today().year)
                    rec.mic_number += anio[2:4]
                    sequence_mic_paraguay = self.env['ir.sequence'].next_by_code('rt.service.mic.paraguay')
                    rec.mic_number += sequence_mic_paraguay
                if rec.aduana_destino_id.country_id.name == 'Brasil':
                    rec.mic_number += '1554'
                    anio = str(datetime.datetime.today().year)
                    rec.mic_number += anio[2:4]
                    sequence_mic_brasil = self.env['ir.sequence'].next_by_code('rt.service.mic.brasil')
                    rec.mic_number += sequence_mic_brasil
        return

    @api.onchange('product_type')
    def onchange_product_type(self):
        if self.product_type == 'propio':
            self.make_mic_number_readonly = True
        if self.product_type == 'terceros':
            self.make_mic_number_readonly = False

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

    @api.multi
    def a_borrador(self):
        return self.write({'state': 'draft'})

    @api.multi
    def borrador_a_confirmado(self):
        return self.write({'state': 'confirm'})

    @api.multi
    def confirmado_a_proceso(self):
        return self.write({'state': 'inprocess'})

    @api.multi
    def cancelado(self):
        return self.write({'state': 'inprocess'})

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

    def load_products_bolivia(self):
        product_lines = []
        productos = self.env['product.template'].search([('is_bolivian_consol', '=', True)])
        if not productos:
            raise Warning('No se encontraron productos por defecto para Bolivia')
        for srv in productos:
            data_prod = {
                'product_type': 'terceros',
                'name': srv.name,
                'product_id': srv.id,
                'currency_id': self.pricelist_id.currency_id.id,
                'partner_invoice_id': self.partner_invoice_id.id,
                'is_invoiced': True,
            }
            product_lines.append((0, 0, data_prod))
        return product_lines

    @api.multi
    def refrescar_valores(self):
        prod_trasbordo_name = 'Gastos de Trasbordo'
        prod_trasbordo = self.env['product.template'].search([('name', '=', prod_trasbordo_name)])

        item_tarifa = self.env['default.expenses'].search([('pricelist_item_parent_id', '=', self.pricelist_id[0].item_ids[0].id), ('product_id', '=', prod_trasbordo.id)])


        if self.productos_servicios_camion_ids:
            for prod in self.productos_servicios_camion_ids:
                if prod.product_id.name == prod_trasbordo_name:
                    if prod.importe:
                        prod.importe = 0
                    if prod.valor_compra:
                        prod.valor_compra = 0
                    prod.importe = item_tarifa.sale_price * self.qty_cargas
                    prod.valor_compra = item_tarifa.cost_price * self.qty_cargas

    @api.multi
    def generar_cargas(self):

        prod_trasbordo = 'Gastos de Trasbordo'
        if not self.qty_cargas:
            raise Warning('Debe ingresar cantidad de cargas')
        lineas = []
        if not (self.partner_invoice_id.name == 'Pluscargo Bolivia SRL' and self.partner_invoice_id.vat == 'BO1025847023'):
            for line in range(self.qty_cargas):
                # Creo una carga por iteracion de cantidad
                vals = {
                    'camion_id': self.id,
                    'name': '/',
                    'load_presentation': 'paquete',
                    'partner_invoice_id': self.partner_invoice_id.id,
                }
                lineas.append((0, 0, vals))
            self.cargas_ids = lineas

        if self.partner_invoice_id.name == 'Pluscargo Bolivia SRL' and self.partner_invoice_id.vat == 'BO1025847023':
            if self.cargas_ids:
                self.cargas_ids = False
            for line in range(self.qty_cargas):
                #Creo una carga por iteracion de cantidad
                vals = {
                    'camion_id': self.id,
                    'name': '/',
                    'load_presentation': 'paquete',
                    'partner_invoice_id': self.partner_invoice_id.id,
                    'producto_servicio_carga_ids': self.load_products_bolivia()
                }
                lineas.append((0, 0, vals))
            self.cargas_ids = lineas

        if self.productos_servicios_camion_ids:
            for prod in self.productos_servicios_camion_ids:
                if prod.product_id.name == prod_trasbordo:
                    prod.importe = prod.importe * self.qty_cargas
                    prod.valor_compra = prod.valor_compra * self.qty_cargas

    @api.onchange('vehicle_id', 'matricula_dos_id')
    def _onchange_vehicle(self):
        if self.vehicle_id:
            self.driver_id = self.vehicle_id.driver_id.id


    @api.onchange('matricula_fletero')
    def onchange_matricula_fletero(self):
        domain = {}
        warning = {}
        res = {}

        for rec in self:
            rec.chofer = rec.matricula_fletero.chofer

        vehiculo = self.env['fleet.vehicle']
        matriculas_fleteros = vehiculo.search([('is_ras_property', '!=', True)])
        domain = {'matricula_fletero': [('id', 'in', matriculas_fleteros.ids)]}

        if warning:
            res['warning'] = warning
        if domain:
            res['domain'] = domain
        return res


    @api.multi
    def load_product_lines(self, pricelist_id):
        new_prod_ids = []
        pricelist_item_obj = self.env['product.pricelist.item']
        if not pricelist_id:
            return False
        pricelist_row = pricelist_item_obj.search([('pricelist_id', '=', pricelist_id[0].id)], limit=1)
        for exp in pricelist_row.expenses_ids:

            val = {'product_id': exp.product_id.id,
                   'product_qty': exp.product_qty,
                   'is_invoiced': exp.invoiceable,
                   'is_outgoing': exp.is_outgoing,
                   'product_type': 'terceros',
                   'camion_id': self.id,
                   'currency_id': exp.currency_id.id,
                   'importe': exp.sale_price,
                   'pricelist_id': exp.pricelist_item_parent_id.id,
                   'name': 'ref',
                   'valor_compra': exp.cost_price,
                   'valor_compra_currency_id': exp.currency_id.id,
                   'partner_invoice_id': self.partner_invoice_id.id,

                   }
            # if pricelist_id:
            #     val['currency_id'] = pricelist_row.currency_id.id
            new_prod_ids.append((0, 0, val))

        return new_prod_ids


    @api.onchange('regimen')
    def _cargar_dominio_vehiculo(self):
        domain = {}
        warning = {}
        res = {}
        fleet_obj = self.env['fleet.vehicle']
        fleet_vehicle_id = fleet_obj.search([('state_id', 'in', ('Tractores', 'Camiones', 'Camionetas'))])
        fleet_matricula_dos_id = fleet_obj.search([('state_id', 'in', 'Semi Remolques y Remolques')])
        domain = {'vehicle_id': [('id', 'in', fleet_vehicle_id.ids)],
                  'matricula_dos_id': [('id', 'in', fleet_matricula_dos_id.ids)]}

        if warning:
            res['warning'] = warning
        if domain:
            res['domain'] = domain
        return res

    @api.multi
    def show_service_lines(self):
        context = self._context.copy()
        srv_ids = self.ids
        act_window = self.env['ir.actions.act_window']
        wizard = self
        # open the list view of service product to invoice
        res = act_window.for_xml_id('servicio_consolidado', 'action_consolidado_servicio_tree')
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

    @api.multi
    def show_rejected_service_lines(self):
        context = self._context.copy()
        srv_ids = self.ids
        act_window = self.env['ir.actions.act_window']
        wizard = self
        # open the list view of service product to invoice
        res = act_window.for_xml_id('servicio_consolidado', 'action_consolidado_servicio_rechazado')
        res['context'] = {
            'search_default_invoiced_rejected': 1,
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
            res['domain'] = []
            res['domain'].append(('id', 'in', ids_guardadas))
            res['domain'].append(('invoiced', '=', False))
            res['domain'].append(('is_invoiced', '=', True))
            res['domain'].append(('invoiced_rejected', '=', True))
        return res

    @api.onchange('partner_invoice_id', 'partner_id')
    def onchange_partner_invoice_id(self):
        if self.partner_invoice_id:
            if self.cargas_ids:
                for carga in self.cargas_ids:
                    carga.partner_invoice_id = self.partner_invoice_id.id
                    if carga.producto_servicio_carga_ids:
                        for prod in carga.producto_servicio_carga_ids:
                            prod.partner_invoice_id = self.partner_invoice_id.id

                if self.productos_servicios_camion_ids:
                    for prod_camion in self.productos_servicios_camion_ids:
                        prod_camion.partner_invoice_id = self.partner_invoice_id.id

    @api.onchange('partner_invoice_id', 'company_id', 'pricelist_id')
    @api.multi
    def _onchange_partner_id(self):
        domain = {}
        warning = {}
        res = {}
        pricelist_obj = self.env['product.pricelist']
        pricelist_item_obj = self.env['product.pricelist.item']

        for rec in self:
            if rec.productos_servicios_camion_ids:
                rec.productos_servicios_camion_ids = False
            if rec.partner_invoice_id:
                partner_id = rec.partner_invoice_id.id
                pricelist = pricelist_obj.search([('partner_id', '=', partner_id)])
                if len(pricelist) == 1:
                    rec.pricelist_id = pricelist.id
                if rec.productos_servicios_camion_ids:
                    rec.productos_servicios_camion_ids = False
                if len(pricelist) == 1 or self.pricelist_id:
                    if rec.productos_servicios_camion_ids:
                        rec.productos_servicios_camion_ids = False
                        rec.productos_servicios_camion_ids = self.load_product_lines(pricelist_id=pricelist)
                    elif rec.pricelist_id:
                        rec.productos_servicios_camion_ids = False
                        rec.productos_servicios_camion_ids = self.load_product_lines(pricelist_id=self.pricelist_id)
                    else:
                        rec.productos_servicios_camion_ids = False
                        rec.productos_servicios_camion_ids = self.load_product_lines(pricelist_id=pricelist)
                if len(pricelist) == 1:
                    rec.productos_servicios_camion_ids = False
                    rec.productos_servicios_camion_ids = self.load_product_lines(pricelist_id=pricelist)
                if not pricelist:
                    rec.pricelist_id = False
                    warning = {
                        'title': _("Alerta para %s") % self.partner_invoice_id.name,
                        'message': "No se encontró Tarifa para el cliente"
                    }
                domain = {'pricelist_id': [('id', 'in', pricelist.ids)]}
                if rec.pricelist_id:
                    pricelis_item = pricelist_item_obj.search([('pricelist_id', '=', self.pricelist_id.id)], limit=1)
                    rec.driver_commission = pricelis_item.comision_chofer
                    rec.currency_id_chofer = pricelis_item.comision_chofer_currency_id.id

        if warning:
            res['warning'] = warning
        if domain:
            res['domain'] = domain
        return res

    @api.onchange('dua_aduana')
    def check_mes(self):
        for rec in self:
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

    @api.onchange('dua_anio', 'dua_numero')
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
    @api.onchange('dua_numero')
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
            if (rec.regimen == 'impo_inter' or rec.regimen == 'impo_nat') and int_dua not in dua_importaciones:
                if int_dua in dua_exportaciones:
                    dua_type = 'Exportaciones (500000 - 699999)'
                if int_dua in dua_transitos:
                    dua_type = 'Transitos (700000 - 999999)'
                if rec.dua_numero != False:
                    rec.dua_numero = False
                    return {'warning': {'title': "Error",
                                        'message': 'DUA inválido para el Regimen IMPO \n El DUA ingresado corresponde al regimen  %s' % dua_type}}
            if (rec.regimen == 'expo_inter' or rec.regimen == 'expo_nat') and int_dua not in dua_exportaciones:
                if int_dua in dua_transitos:
                    dua_type = '700000 - 999999 - Transitos'
                if int_dua in dua_importaciones:
                    dua_type = '000001 - 499999 - Importaciones'
                if rec.dua_numero != False:
                    rec.dua_numero = False
                    return {'warning': {'title': "Error",
                                        'message': 'DUA inválido para el Regimen EXPO \n El DUA ingresado corresponde al regimen  %s' % dua_type}}
            if (rec.regimen == 'transit_inter_in' or rec.regimen == 'transit_inter_out') and int_dua not in dua_transitos:
                if int_dua in dua_importaciones:
                    dua_type = '000001 - 499999 - Importaciones'
                if int_dua in dua_exportaciones:
                    dua_type = '500000 - 699999 - Exportaciones'
                if rec.dua_numero != False:
                    rec.dua_numero = False
                    return {'warning': {'title': "Error",
                                        'message': 'DUA inválido para el Regimen TRANSITO \n El DUA ingresado corresponde al regimen  %s' % dua_type}}
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
            # 6 es el largo esperado
            if self.dua_numero != False:
                if len(self.dua_numero) != 6:
                    self.dua_numero = False
                    return {'warning': {'title': "Error", 'message': "Se espera un número de 6 cifras ej: 457882"}}
            # Validar regimen
            int_dua = int(self.dua_numero)
            if (regimen == 'impo_inter' or regimen == 'impo_nat') and int_dua not in dua_importaciones:
                if int_dua in dua_exportaciones:
                    dua_type = 'Exportaciones (500000 - 699999)'
                if int_dua in dua_transitos:
                    dua_type = 'Transitos (700000 - 999999)'
                    self.dua_numero = False
                    return {'warning': {'title': "Error",
                                        'message': 'DUA inválido para el Regimen IMPO \n El DUA ingresado corresponde al regimen  %s' % dua_type}}
            if (regimen == 'expo_inter' or regimen == 'expo_nat') and int_dua not in dua_exportaciones:
                if int_dua in dua_transitos:
                    dua_type = '700000 - 999999 - Transitos'
                if int_dua in dua_importaciones:
                    dua_type = '000001 - 499999 - Importaciones'
                    self.dua_numero = False
                    return {'warning': {'title': "Error",
                                        'message': 'DUA inválido para el Regimen EXPO \n El DUA ingresado corresponde al regimen  %s' % dua_type}}
            if (regimen == 'transit_inter_in' or regimen == 'transit_inter_out') and int_dua not in dua_transitos:
                if int_dua in dua_importaciones:
                    dua_type = '000001 - 499999 - Importaciones'
                if int_dua in dua_exportaciones:
                    dua_type = '500000 - 699999 - Exportaciones'
                    self.dua_numero = False
                    return {'warning': {'title': "Error",
                                        'message': 'DUA inválido para el Regimen TRANSITO \n El DUA ingresado corresponde al regimen  %s' % dua_type}}
        if self.dua_anio:
            if not self.dua_anionumero:
                self.dua_anionumero = self.dua_anio + self.dua_numero
