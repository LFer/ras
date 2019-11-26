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

class TipoConsolidado(models.Model):
    _name = "tipo.consolidado"
    _description = "Tipos de Consolidado"

    name = fields.Char(string='Codigo')
    destino = fields.Many2one(comodel_name='res.country.city', string='Destino')
    agente_consolidador_id = fields.Many2one(comodel_name='res.partner', string='Agente Consolidador')

    @api.multi
    @api.depends('name', 'destino', 'agente_consolidador_id')
    def name_get(self):
        return [(rec.id, '%s - %s - %s' % (rec.name, rec.agente_consolidador_id.name, rec.destino.name)) for rec in self]

    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        recs = self.browse()
        recs = self.search(['|', '|', ('name', operator, name), ('agente_consolidador_id', operator, name), ('destino', operator, name)] + args, limit=limit)
        return recs.name_get()



class CargaCamion(models.Model):
    _name = "carga.camion"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'rating.mixin']
    _description = "Cargas"
    _order = "id ASC"

    def _default_camion_id(self):
        #team = self.env['crm.team'].sudo()._get_default_team_id(user_id=self.env.uid)
        return self.env['carpeta.camion'].search([], limit=1).id
        #return self._stage_find(team_id=team.id, domain=[('fold', '=', False)]).id

    @api.multi
    def _get_operation_type(self):

        operation_international = [('transit_inter_in', '80 - Transito Internacional Ingreso'),
                                   ('transit_inter_out', '80 - Transito Internacional Salida'),
                                   ('impo_inter', '10 - IMPO Internacional'),
                                   ('expo_inter', '40 - EXPO Internacional')]

        return operation_international

    tipo_consolidado = fields.Many2one(comodel_name='tipo.consolidado', string='Tipo Consolidado', required=True)
    name = fields.Char(string='Referencia')
    camion_id = fields.Many2one('carpeta.camion', string='Camion', default=lambda self: self._default_camion_id(), group_expand='_read_group_stage_ids')
    regimen = fields.Selection(_get_operation_type, string="Regimen", store=True)
    factura_carga_ids = fields.One2many('consolidado.factura.carga', 'rt_carga_id', ondelete='cascade')
    packing_list_carga_ids = fields.One2many('consolidado.packing.list.carga', 'rt_carga_id', ondelete='cascade')
    bill_of_landing_ids = fields.One2many('consolidado.bill.of.landing.carga', 'rt_carga_id', ondelete='cascade')
    partner_id = fields.Many2one('res.partner', string='Customer')
    load_type = fields.Selection([('bulk', 'Bulk'), ('contenedor', 'Contenedor'), ('liquido_granel', u'Granel Líquido'),('solido_granel', u'Granel Solido')], string='Tipo de Carga')
    libre_devolucion = fields.Datetime(string='Libre de Devolución')
    tare = fields.Float('Tara')
    payload = fields.Float(string='Payload')
    carga_m3 = fields.Float(string='m3')
    volume = fields.Float(string='Volumen')
    net_kg = fields.Float(string='Kg Neto')
    raw_kg = fields.Float(string='Kg Bruto')
    precio_flete = fields.Char(string="Precio del Flete")
    precio_seguro = fields.Char(strin="Precio del Seguro")
    cut_off_documentario = fields.Datetime('Cut off Documentario')
    container_number = fields.Char(string=u'Número de contenedor', size=32)
    container_number_exception = fields.Char(string=u'Nº de contenedor Excepción', size=13)
    dua_linea = fields.Char(string='DUA')
    dua_aduana = fields.Char(string='Aduana', size=3)
    dua_anio = fields.Char(string='Año', size=4)
    dua_numero = fields.Char(string='Dua_Numero', size=6)
    dua_anionumero = fields.Char()
    dangers_loads = fields.Boolean(string='Carga Peligrosa')
    load_presentation = fields.Selection([('pallet', 'Pallet'), ('paquete','Paquete'), ('otros', 'Otros')], string=u'Presentación')
    pallet_type = fields.Selection([('euro', 'Europeo'), ('merco','Mercosur')], string=u'Tipo Pallet')
    preasignado = fields.Boolean(string='Preasignado')
    container_size = fields.Float(u'Tamaño')
    package = fields.Float(string='Bultos')
    container_type = fields.Many2one(comodel_name='fleet.vehicle', string='Tipo de Contenedor',  domain=[('vehicle_type', '=', 'container')])
    cut_off_operative = fields.Datetime('Cut off Operativo')
    bookingk = fields.Char('Booking', size=32)
    costo_estimado = fields.Float(string='Costo Referencia')
    partner_seller_id = fields.Many2one(comodel_name='res.partner', string='Vendedor', domain=[('seller', '=', True)])
    seal_number = fields.Char(string='Número de precinto', size=32)
    route = fields.Text(string='Rutas')
    #Campos nuevos
    carga_qty = fields.Integer(string='Cantidad')
    contenedor_ingreso = fields.Char(string='Contenedor de ingreso')
    ref = fields.Char(string='Referencia Pluscargo')
    bl = fields.Char(string='B/L')
    producto_servicio_carga_ids = fields.One2many('producto.servicio.camion', 'rt_carga_id', string='Cargas', ondelete='cascade', copy=True)
    market_origin = fields.Char(string='Origen de la mercadería')
    invoice_description = fields.Text(string='Descripción de Facturas')
    invoice_list = fields.Char(string='Listado de Facturas')
    ncm = fields.Char(string='NCM')
    remitente_id = fields.Many2one(comodel_name='asociados.carpeta', string='Remitente', domain="[('type', '=','remitente')]")
    partner_remitente_id = fields.Many2one(comodel_name='res.partner', string= 'Partner Remitente', domain=[('remittent', '=', True)])
    consigantario_id = fields.Many2one(comodel_name='asociados.carpeta', string='Consignatario', domain="[('type', '=','consignatario')]")
    partner_consigantario_id = fields.Many2one(comodel_name='res.partner', string= 'Partner Consignatario', domain=[('consignee', '=', True)])
    destinatario_id = fields.Many2one(comodel_name='asociados.carpeta', string='Destinatario', domain="[('type', '=','destino')]")
    partner_destinatario_id = fields.Many2one(comodel_name='res.partner', string='Partner Destinatario', domain=[('receiver', '=', True)])
    partner_notificar_id = fields.Many2one(comodel_name='res.partner', string='Partner Notificar a ', domain=[('notificar','=', True)])
    notificar_id = fields.Many2one(comodel_name='asociados.carpeta', string='Notificar a ',domain="[('type', '=','notificar')]")
    country_id = fields.Many2one(comodel_name='res.country', string='País')
    mic_number = fields.Char(string='Numero MIC')
    kilaje_carga = fields.Float(string='Kilage de la Carga')
    volumen_est = fields.Char(string='Volumen Estimado')
    company_id = fields.Many2one('res.company', string='Compañia', default=lambda self: self.env.user.company_id)
    valid_cointaner_number_text = fields.Boolean(help='Este booleano es para que se muestre un texto si el número de container es válido')
    invalid_cointaner_number_text = fields.Boolean(help='Este booleano es para que se muestre un texto si el número de container no es válido')
    terminal_retreat = fields.Many2one(comodel_name='res.partner.address.ext', string='Terminal de Retiro',ondelete='restrict')
    terminal_return = fields.Many2one(comodel_name='res.partner.address.ext', string=u'Terminal de Devolución',ondelete='restrict')
    terminal_ingreso_cargado = fields.Many2one(comodel_name='res.partner.address.ext',string=u'Terminal de Ingreso Cargado', ondelete='restrict')
    invisible_in_transit = fields.Boolean()
    invisible_in_transit_out = fields.Boolean()
    make_crt_number_readonly = fields.Boolean()
    make_presentacion_invisible = fields.Boolean(help='Esto va hacer el campo presentacion invisible')
    make_container_number_invisible = fields.Boolean(string='Exception', default=False)
    make_factura_invisible = fields.Boolean(help='Este booleano es para hacer invisible la facutra si esta vacia',
                                            default=False)
    make_packing_list_invisible = fields.Boolean(
        help='Este booleano es para hacer invisible el packing list si esta vacio', default=False)
    make_bill_of_landing_invisible = fields.Boolean(
        help='Este booleano es para hacer invisible el bill of landing si esta vacio', default=False)
    pricelist_id = fields.Many2one('product.pricelist.item', string='Tarifa')
    partner_invoice_id = fields.Many2one(comodel_name='res.partner', string='Cliente a facturar',domain=[('customer', '=', True)])
    make_page_invisible = fields.Boolean(help='Este booleano es para hacer invisible la pagina si no se cargo regimen, cliente a facturar')
    aduana_origen_id = fields.Many2one('fronteras', 'Aduana Origen')
    aduana_destino_id = fields.Many2one('fronteras', 'Aduana Destino')
    booking = fields.Char('Booking', size=32)
    cointainer_kg = fields.Float(string='Peso de la carga')
    origin_id = fields.Many2one(comodel_name='res.partner.address.ext', string='Origen')
    destiny_id = fields.Many2one(comodel_name='res.partner.address.ext', string='Destino')
    market_value = fields.Float(string='Valor de la Mercaderia')
    crt_number = fields.Char(string='Numero CRT')
    crt_origin = fields.Selection([('propio', 'Propio'), ('terceros', 'Terceros')], string='Origen CRT')
    _sql_constraints = [
        ('dua_anio_unique', 'unique(dua_anionumero)', "NO puede haber dos numeros de DUA iguales en el mismo año!"),
    ]

    @api.multi
    def get_crt_number(self):
        for rec in self:
            if rec.regimen == 'transit_inter_out' or rec.regimen == 'transit_inter_out' or rec.regimen == 'impo_inter' or rec.regimen == 'expo_inter':
                rec.crt_number = 'UY'
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
        return
    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        search_vacio = [('active', '=', True)]
        stage_ids = stages._search(search_vacio, order=order, access_rights_uid=SUPERUSER_ID)
        return stages.browse(stage_ids)

    @api.onchange('pricelist_id')
    def onchange_pricelist_id(self):
        if self.camion_id.pricelist_id:
            domain = {}
            warning = {}
            res = {}
            regimen_tarifa = self.camion_id.regimen
            cliente = self.camion_id.pricelist_id.partner_id.id
            linea_tarifa_obj = self.env['product.pricelist.item']
            tarifa = linea_tarifa_obj.search([('partner_id', '=', cliente), ('regimen', '=', regimen_tarifa)]).ids
            domain = {'pricelist_id': [('id', 'in', tarifa)]}

            if warning:
                res['warning'] = warning
            if domain:
                res['domain'] = domain
            return res

    @api.onchange('crt_origin')
    def onchange_crt_origin(self):
        if self.crt_origin == 'propio':
            self.make_crt_number_readonly = True
        if self.crt_origin == 'terceros':
            self.make_crt_number_readonly = False


    @api.onchange('aduana_origen_id', 'aduana_destino_id')
    def invisible_en_transito(self):
        """
        Invisible si:
         es contenedor
         transito
         aduana_origen_id es Montevideo

        :return:
        """

        res = {}
        domain = {}
        aduana_obj = self.env['fronteras']
        for rec in self:
            if rec.load != 'contenedor':
                if rec.aduana_origen_id.codigo_dna == '001' and rec.regimen in ('transit_inter_in', 'transit_inter_out'):
                    rec.invisible_in_transit = True

                # Transito OUT
                if rec.aduana_origen_id.codigo_dna != '001':
                    if rec.aduana_destino_id.codigo_dna == '001':
                        print('Transito OUT')
                        rec.invisible_in_transit_out = True

            if rec.dua_aduana:

                if rec.regimen in ('impo_nat', 'impo_inter'):
                    aduana = aduana_obj.search([('codigo_dna', '=', rec.dua_aduana), ('country_id', '=', 234)])
                    if len(aduana) == 1:
                        rec.aduana_origen_id = aduana.id
                    else:
                        domain = {'aduana_origen_id': [('id', 'in', aduana.ids)]}


                elif rec.regimen in ('expo_nat', 'expo_inter'):
                    aduana = aduana_obj.search([('codigo_dna', '=', rec.dua_aduana), ('country_id', '=', 234)])
                    if len(aduana) == 1:
                        rec.aduana_origen_id = aduana.id
                    else:
                        domain = {'aduana_origen_id': [('id', 'in', aduana.ids)]}

        if domain:
            res['domain'] = domain
        return res

    @api.multi
    @api.onchange('volume', 'raw_kg', 'package', 'aduana_origen_id', 'load_type', 'cointainer_kg', 'container_type','dangers_loads')
    def get_pricelist_item(self):
        pricelist_item_obj = self.env['product.pricelist.item']
        carpeta = self.camion_id
        partner = carpeta.partner_invoice_id.id
        #self.partner_seller_id = carpeta.partner_invoice_id.user_id.partner_id.id
        #self.importe_currency_id = carpeta.currency_id.id
        condiciones_busqueda = []
        if self.load_type:
            if self.load_type == 'bulk':
                condiciones_busqueda.append(('load_type', '=', self.load_type))
                if partner:
                    condiciones_busqueda.append(('partner_id', '=', partner))
                if self.volume:
                    condiciones_busqueda.append(('mt3_to', '<=', self.volume))
                if self.raw_kg:
                    condiciones_busqueda.append(('kg_from', '<=', self.raw_kg))
                    condiciones_busqueda.append(('kg_to', '>=', self.raw_kg))
                if self.aduana_origen_id:
                    condiciones_busqueda.append(('aduana_origen_id', '=', self.aduana_origen_id.id))
                if condiciones_busqueda:
                    pricelist_item = pricelist_item_obj.search(condiciones_busqueda)
                    if len(pricelist_item) > 1:
                        return
                    if pricelist_item:
                        self.search_conditions = condiciones_busqueda
                        self.pricelist_id = pricelist_item.id
                        self.importe_currency_id = pricelist_item.currency_id.id
                        self.importe = pricelist_item.sale_price
            if self.load_type == 'contenedor':
                condiciones_busqueda.append(('load_type', '=', self.load_type))
                if partner:
                    condiciones_busqueda.append(('partner_id', '=', partner))
                if self.container_type.size == 20:
                    if self.cointainer_kg:
                        condiciones_busqueda.append(('kg_from', '<=', self.cointainer_kg))
                        condiciones_busqueda.append(('kg_to', '>=', self.cointainer_kg))

                else:
                    condiciones_busqueda.append(('size_from', '<=', self.container_type.size))
                    condiciones_busqueda.append(('size_to', '>=', self.container_type.size))


            if self.aduana_origen_id:
                condiciones_busqueda.append(('aduana_origen_id', '=', self.aduana_origen_id.id))
        if condiciones_busqueda:
            pricelist_item = pricelist_item_obj.search(condiciones_busqueda)
            if len(pricelist_item) > 1:
                aux = max([x.sale_price for x in pricelist_item])
                for pl in pricelist_item:
                    if pl.sale_price == aux:
                        pricelist_item = pl
            if pricelist_item:
                self.search_conditions = condiciones_busqueda
                self.pricelist_id = pricelist_item.id
                self.importe_currency_id = pricelist_item.currency_id.id
                self.importe = pricelist_item.sale_price



    @api.onchange('partner_invoice_id', 'name', 'libre_devolucion', 'load_type')
    def _onchange_partner_id(self):
        domain = {}
        warning = {}
        res = {}
        terminal_devolucion = []
        address_obj = self.env['res.partner.address.ext']
        partner_obj = self.env['res.partner']
        playas_contenedor_vacios = address_obj.search([('address_type', '=', 'beach_empty')]).ids
        playas_contenedor_cargado = address_obj.search([('address_type', '=', 'beach_load')]).ids
        domain = {'terminal_retreat': [('id', 'in', playas_contenedor_vacios)], 'terminal_return': [('id', 'in', playas_contenedor_vacios)], 'terminal_ingreso_cargado': [('id', 'in', playas_contenedor_cargado)]}
        for prod in self.producto_servicio_carga_ids:
            prod.partner_invoice_id = self.partner_invoice_id.id
        if warning:
            res['warning'] = warning
        if domain:
            res['domain'] = domain
        return res

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
            else:
                rec.valid_cointaner_number_text = False
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
        res = {}
        domain = {}
        aduana_obj = self.env['fronteras']
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

                if rec.regimen in ('impo_nat', 'impo_inter'):
                    aduana = aduana_obj.search([('codigo_dna', '=', rec.dua_aduana), ('country_id', '=', 234)])
                    if len(aduana) == 1:
                        rec.aduana_origen_id = aduana.id
                    else:
                        domain = {'aduana_origen_id': [('id', 'in', aduana.ids)]}


                elif rec.regimen in ('expo_nat', 'expo_inter'):
                    aduana = aduana_obj.search([('codigo_dna', '=', rec.dua_aduana), ('country_id', '=', 234)])
                    if len(aduana) == 1:
                        rec.aduana_origen_id = aduana.id
                    else:
                        domain = {'aduana_origen_id': [('id', 'in', aduana.ids)]}

        if domain:
            res['domain'] = domain
        return res

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
            if (rec.regimen == 'transit_inter_out' or rec.regimen == 'transit_inter_in') and int_dua not in dua_transitos:
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
            if (regimen == 'transit_inter_in' or regimen == 'transit_inter_out') and int_dua not in dua_transitos:
                    if int_dua in dua_importaciones:
                        dua_type = '000001 - 499999 - Importaciones'
                    if int_dua in dua_exportaciones:
                        dua_type = '500000 - 699999 - Exportaciones'
                        self.dua_numero = False
                        return {'warning': {'title': "Error", 'message': 'DUA inválido para el Regimen TRANSITO \n El DUA ingresado corresponde al regimen  %s' % dua_type}}
        if self.dua_anio:
            if not self.dua_anionumero:
                self.dua_anionumero = self.dua_anio + self.dua_numero