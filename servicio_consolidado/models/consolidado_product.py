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

class ProdcutoServicioCamion(models.Model):
    _name = 'producto.servicio.camion'
    _description = 'Servicios Asociados al Camion'



    rt_carga_id = fields.Many2one('carga.camion', string='Carga')
    camion_id = fields.Many2one('carpeta.camion', string='Camion')
    name = fields.Char(string='Referencia')
    partner_invoice_id = fields.Many2one('res.partner', string='Cliente a facturar', domain=[('customer', '=', True)], store=True)
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('confirm', 'Confirmado'),
        ('inprocess', 'En proceso'),
        ('cancel', 'Cancelado'),
        ('done', 'Realizado'),
    ], string='Status', index=True, readonly=True, default='draft',
        track_visibility='onchange', copy=False,
    )
    regimen = fields.Selection(related='rt_carga_id.regimen', string='Regimen', store=True)
    invisible_in_transit_out = fields.Boolean(related='rt_carga_id.invisible_in_transit_out')
    product_type = fields.Selection([('propio', 'Propio'), ('terceros', 'Terceros')], string='Origen del Servicio') #Este campo va determinar muchisimos comportamientos
    product_id = fields.Many2one(comodel_name='product.product', string='Servicio', domain=[('product_tmpl_id.type', '=',  'service'), ('sale_ok', '=', True)], required=False, change_default=True, ondelete='restrict')
    action_type_id = fields.Many2one('tipo.accion', string="Tipo de Acción")
    origin_id = fields.Many2one(comodel_name='res.partner.address.ext', string='Origen')
    destiny_id = fields.Many2one(comodel_name='res.partner.address.ext', string='Destino')
    frontera_nacional = fields.Many2one(comodel_name='res.country.city', string='Frontera Nacional')
    frontera_internacional = fields.Many2one(comodel_name='res.country.city', string='Frontera Internacional')
    partner_seller_id = fields.Many2one(comodel_name='res.partner', string='Vendedor', domain=[('seller', '=', True)], readonly=False)
    supplier_id = fields.Many2one(comodel_name='res.partner', string='Proveedor', domain=[('supplier', '=', True)])
    currency_id = fields.Many2one(comodel_name='res.currency', string='Moneda')
    valor_compra_currency_id = fields.Many2one(comodel_name='res.currency', string='Moneda Compra')
    valor_compra = fields.Monetary(string='Valor Compra', currency_field='valor_compra_currency_id')
    remito = fields.Char(string='Remito')
    attach_remito = fields.Many2many(comodel_name='ir.attachment', relation='prod_attach_remito_consolidado', column1='prod_id', column2='attach_remito_id')
    pricelist_id = fields.Many2one('product.pricelist.item', string='Tarifa')
    invoiced_supplier = fields.Boolean(string='Es para saber si este servicio ya fue facturado o no')
    provision_creada = fields.Boolean(string='Para saber si se creo o no la provision para este servicio')
    crt_number = fields.Char(string='Numero CRT')
    cliente_id = fields.Many2one(comodel_name='res.partner', string='Cliente')
    seller_commission = fields.Float(string='Comisión Vendedor')
    #Facturable
    is_invoiced = fields.Boolean('Facturable', help='Marque esta casilla si este servicio no se factura')
    invoiced = fields.Boolean(string='¿Facturado?')
    tramo_inter = fields.Boolean(string='Tramo Internacional')
    tramo_nat = fields.Boolean(string='Tramo Nacional')
    # Es Gasto
    is_outgoing = fields.Boolean('¿Es Gasto?', help='Marque esta casilla si este servicio es un Gasto')
    importe = fields.Float(string='Valor de Venta', store=True)
    currency_id_vendedor = fields.Many2one(comodel_name='res.currency', string='Moneda')
    make_frontera_nacional_visible = fields.Boolean()
    make_frontera_internacional_visible = fields.Boolean()
    invoiced_rejected = fields.Boolean(string='Factura Rechazada')
    # Proveedores
    supplier_ids = fields.One2many('rt.service.product.supplier', 'rt_consol_product_id', 'Proveedores', copy=True)
    vehicle_id = fields.Many2one(comodel_name='fleet.vehicle', string=u'Matrícula',domain=[('is_ras_property', '=', True)])
    driver_id = fields.Many2one('hr.employee', 'Chofer', help=u'Chofer del Vehículo')
    driver_commission = fields.Float('Comisión de chofer')
    currency_id_chofer = fields.Many2one(comodel_name='res.currency', string='Moneda Comisión Chofer')


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

    def get_tack_id(self):
        if self.rt_carga_id.container_number:
            return self.rt_carga_id.container_number
        else:
            return ' '

    def get_dua(self):
        dua = ''
        if self.rt_carga_id.dua_aduana:
            carga = self.rt_carga_id
            dua = carga.dua_aduana + '-' if carga.dua_aduana else ''
            dua += carga.dua_anio + '-' if carga.dua_anio else ''
            dua += carga.dua_numero if carga.dua_numero else ''
        if self.rt_carga_id.camion_id.dua_aduana:
            camion = self.rt_carga_id.camion_id
            dua = camion.dua_aduana + '-' if camion.dua_aduana else ''
            dua += camion.dua_anio + '-' if camion.dua_anio else ''
            dua += camion.dua_numero if camion.dua_numero else ''
        else:
            dua = ' '
        return dua

    def get_mic(self):
        mic = ''
        if self.camion_id:
            mic = self.camion_id.mic_number
        if self.rt_carga_id.camion_id:
            mic = self.rt_carga_id.camion_id.mic_number
        return mic

    def get_crt(self):
        if self.rt_carga_id:
            crt = self.rt_carga_id.crt_number
        else:
            crt = ' '
        return crt

    @api.multi
    def add_supplier_to_product_line(self, id_necesario=None):
        if self._module:
            if self._module == 'servicio_consolidado':
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
                tax_obj = self.env['account.tax']
                regimen = self.regimen
                if not self.camion_id and not self.rt_carga_id:
                    taxes = tax_obj.search([('name', '=', 'IVA Directo Op  Grav B')])
                else:
                    if not self.regimen:
                        if self.camion_id:
                            regimen = self.camion_id.regimen
                        if self.rt_carga_id:
                            regimen = self.rt_carga_id.regimen
                    else:
                        regimen = self.regimen
                    regimen = regimen_map[regimen]
                    regimen_obj = self.env['regimenes']
                    regimen_id = regimen_obj.search([('name', '=', regimen)])

                    taxes = tax_obj.search([('regimen_ids', 'in', regimen_id.ids)])
                lineas = []
                if self.product_id.id in [106, 78] and self.supplier_id.id == 40:
                    print('chanchada')
                    taxes = tax_obj.search([('name', '=', 'IVA Directo Op  Grav B')])
                for rec in self:
                    if not rec.supplier_id:
                        raise Warning(
                            'el servicio ' + str(rec.product_id.name) +
                            ' de la linea de prodcuto ' + str(rec.name) +
                            ' de la carpeta ' + str(self.camion_id.name if self.camion_id else 'NO TIENE' or self.rt_carga_id.camion_id.name if self.rt_carga_id.camion_id else 'NO TIENE' )
                            + 'de id ' + str(self.id)
                            + ' no tiene proveedor ')
                    line_dict = {}
                    line_dict['ref'] = rec.rt_carga_id.camion_id.name if rec.rt_carga_id.camion_id.id else rec.camion_id.name
                    line_dict['supplier_id'] = rec.supplier_id.id
                    line_dict['currency_id'] = rec.valor_compra_currency_id.id
                    line_dict['amount'] = rec.valor_compra
                    # line_dict['price_subtotal'] = float(rec.valor_compra * float('1.' + str(int(taxes.amount))))
                    line_dict['price_subtotal'] = float(rec.valor_compra * (1 + (taxes.amount / 100)))
                    line_dict['rt_service_id'] = False
                    line_dict['consol_id'] = rec.rt_carga_id.camion_id.id if rec.rt_carga_id.camion_id.id else rec.camion_id.id
                    line_dict['rt_consol_product_id'] = self.id
                    line_dict['service_state'] = rec.rt_carga_id.camion_id.state if rec.rt_carga_id.camion_id.state else rec.camion_id.state
                    line_dict['tax_ids'] = [(6, 0, taxes.ids)]
                    line_dict['service_date'] = rec.rt_carga_id.camion_id.start_datetime if rec.rt_carga_id.camion_id.start_datetime else rec.camion_id.start_datetime
                    line_dict['tack_id'] = self.get_tack_id()
                    line_dict['dua'] = self.get_dua()
                    line_dict['mic'] = self.get_mic()
                    line_dict['crt'] = self.get_crt()
                    line_dict['origin_id'] = self.rt_carga_id.origin_id.id if self.rt_carga_id else self.origin_id.id
                    line_dict['destiny_id'] = self.rt_carga_id.destiny_id.id if self.rt_carga_id else self.destiny_id.id
                    line_dict['product_id'] = self.product_id.id
                    line_dict['output_reference'] = self.rt_carga_id.camion_id.name if self.rt_carga_id and self.rt_carga_id.camion_id else self.camion_id.name if self.camion_id else 'N/A'
                    line_dict['partner_invoice_id'] = self.partner_invoice_id.id
                    lineas.append((0, 0, line_dict))

                self.supplier_ids = lineas


    @api.onchange('product_id')
    def onchange_product_id(self):
        expense_obj = self.env['default.expenses']
        if self.product_id:
            res = expense_obj.search([('product_id', '=', self.product_id.id)], limit=1)
            self.importe = res.sale_price
            self.currency_id = res.currency_id.id
            if not self.pricelist_id:
                self.pricelist_id = res.pricelist_item_parent_id.id


    @api.onchange('pricelist_id')
    def onchange_pricelist_id(self):
        domain = {}
        warning = {}
        res = {}
        regimen_tarifa = self.camion_id.regimen
        cliente = self.camion_id.pricelist_id.partner_id.id
        linea_tarifa_obj = self.env['product.pricelist.item']
        tarifa = linea_tarifa_obj.search([('partner_id', '=', cliente), ('regimen', '=', regimen_tarifa)]).ids
        domain = {'pricelist_id': [('id', 'in', tarifa)]}
        self.partner_seller_id = self.pricelist_id.partner_id.id

        if warning:
            res['warning'] = warning
        if domain:
            res['domain'] = domain
        return res

    @api.onchange('vehicle_id')
    def onchange_vehicle_id(self):
        for rec in self:
            if not rec.vehicle_id:
                return
            rec.driver_id = rec.vehicle_id.driver_id.id

    @api.onchange('product_type')
    def _cargar_dominio_vehiculo(self):
        domain = {}
        warning = {}
        res = {}
        fleet_obj = self.env['fleet.vehicle']
        fleet_vehicle_id = fleet_obj.search([('state_id', 'in', ('Tractores', 'Camiones', 'Camionetas'))])
        fleet_matricula_dos_id = fleet_obj.search([('state_id', 'in', 'Semi Remolques y Remolques')])
        domain = {'vehicle_id': [('id', 'in', fleet_vehicle_id.ids)],
                  'matricula_dos_id': [('id', 'in', fleet_matricula_dos_id.ids)]}
        if self.camion_id:
            self.regimen = self.camion_id.regimen
        if self.rt_carga_id:
            self.camion_id = self.rt_carga_id.camion_id.id
            self.crt_number = self.rt_carga_id.crt_number
        if warning:
            res['warning'] = warning
        if domain:
            res['domain'] = domain
        return res

    @api.onchange('action_type_id')
    def onchange_action_type_id(self):
        if self.action_type_id:
            if self.action_type_id.name == 'Salida' or self.action_type_id.name == 'Frontera':
                self.make_frontera_nacional_visible = True
            if self.action_type_id.name != 'Salida' and self.action_type_id.name != 'Frontera':
                self.make_frontera_nacional_visible = False
            if self.action_type_id.name == 'Descarga' or self.action_type_id.name == 'Frontera':
                self.make_frontera_internacional_visible = True
            if self.action_type_id.name != 'Descarga' and self.action_type_id.name != 'Frontera':
                self.make_frontera_internacional_visible = False

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

