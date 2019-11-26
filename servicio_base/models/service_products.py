# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import ipdb
import odoo.addons.decimal_precision as dp
from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning
import datetime

_logger = logging.getLogger(__name__)

class rt_product_profit(models.Model):
    _name = "rt.product.profit"
    _description = "Profit del Servicio"


    rt_product_id = fields.Many2one(comodel_name='rt.service.productos', string='Servicio Relacionado')
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


class rt_service_productos(models.Model):
    _name = "rt.service.productos"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _description = "Productos"

    def _get_operation_type(self):
        res = []
        operation_national = [('transit_nat', '80 - Transito Nacional'),
                              ('impo_nat', '10 - IMPO Nacional'),
                              ('expo_nat', '40 - EXPO Nacional'),
                              ('interno_plaza_nat', 'Interno Plaza Nacional'),
                              ('interno_fiscal_nat', 'Interno Fiscal Nacional')]

        operation_international = [('transit_inter_in', '80 - Transito Internacional Ingreso'),
                                   ('transit_inter_out', '80 - Transito Internacional Salida'),
                                   ('impo_inter', '10 - IMPO Internacional'),
                                   ('expo_inter', '40 - EXPO Internacional')]
        both = operation_national + operation_international
        return both

    partner_id = fields.Many2one(comodel_name='res.partner', string='Dueño de la Mercadería', domain=[('customer', '=', True), ('dispatcher', '=', False)], track_visibility='always')
    invoices_ids = fields.One2many('account.invoice', 'rt_service_product_id', string='Facturas de Clientes', domain=[('type', '=', 'out_invoice')], track_visibility='always')
    supplier_invoices_ids = fields.One2many('account.invoice', 'rt_service_product_id', string='Facturas de Cliente',domain=[('type', '=', 'in_invoice')], track_visibility='always')
    rt_carga_id = fields.Many2one(comodel_name='rt.service.carga', string='Carga Relacioada', track_visibility='always')
    rt_service_id = fields.Many2one(related='rt_carga_id.rt_service_id', string='Carpeta Relacionada', store=True, track_visibility='always')
    rt_carpeta_id = fields.Many2one(comodel_name='rt.service', string='Carpeta Relacionada', track_visibility='always')
    operation_type = fields.Selection(related='rt_carga_id.operation_type', string='Tipo de Servicio', readonly=False, store=True, track_visibility='always')
    crt_number = fields.Char(related='rt_carga_id.crt_number', string='Número de CRT', readonly=False, store=True, track_visibility='always')
    mic_number = fields.Char(related='rt_carga_id.mic_number', string='Número de MIC', readonly=False, store=True, track_visibility='always')
    invisible_in_transit_out = fields.Boolean(related='rt_carga_id.invisible_in_transit_out')
    pricelist_id = fields.Many2one('product.pricelist.item', string='Tarifa')
    regimen = fields.Selection(related='rt_carga_id.regimen', string='Regimen')
    invoice_line_id = fields.Many2one('account.invoice.line', string='Linea Factura')
    partner_invoice_id = fields.Many2one(related='rt_service_id.partner_invoice_id', string='Cliente a facturar', domain=[('customer', '=', True)], store=True, track_visibility='always')
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('confirm', 'Confirmado'),
        ('inprocess', 'En proceso'),
        ('cancel', 'Cancelado'),
        ('done', 'Realizado'),
    ], string='Status', index=True, readonly=True, default='draft',
        track_visibility='always', copy=False,
    )
    load_type = fields.Selection(related='rt_carga_id.load_type', string='Tipo de Carga', track_visibility='always')
    name = fields.Char(string='Referencia Producto', track_visibility='always')
    fecha_fin = fields.Datetime(string='Fin', track_visibility='always')
    product_type = fields.Selection([('propio', 'Propio'), ('terceros', 'Terceros')], string='Origen del Servicio', track_visibility='always')
    product_id = fields.Many2one(comodel_name='product.product', string='Servicio', domain=[('product_tmpl_id.type', '=',  'service'), ('sale_ok', '=', True), ('active', '=', True)], required=False, change_default=True, ondelete='restrict', track_visibility='always')
    matricula = fields.Char(string=u'Matricula', track_visibility='always')
    matricula_dos_id = fields.Many2one(comodel_name='fleet.vehicle', string=u'Matrícula dos', track_visibility='always')
    vehicle_id = fields.Many2one(comodel_name='fleet.vehicle', string=u'Matrícula', domain=[('is_ras_property', '=', True)], track_visibility='always')
    vehicle_type = fields.Selection(related='vehicle_id.vehicle_type', type='char', readonly=True, track_visibility='always')
    driver_id = fields.Many2one('hr.employee', 'Chofer', help=u'Chofer del Vehículo', track_visibility='always')
    driver_commission = fields.Float('Comisión de chofer', track_visibility='always')
    action_type_id = fields.Many2one('tipo.accion', string="Tipo de Acción", track_visibility='always')
    origin_id = fields.Many2one(comodel_name='res.partner.address.ext', string='Origen', track_visibility='always')
    destiny_id = fields.Many2one(comodel_name='res.partner.address.ext', string='Destino', track_visibility='always')
    flujo_id = fields.Many2one(comodel_name='res.partner.address.ext', string='Direccion', track_visibility='always')
    frontera_nacional = fields.Many2one(comodel_name='res.country.city', string='Frontera Nacional', track_visibility='always')
    frontera_internacional = fields.Many2one(comodel_name='res.country.city', string='Frontera Internacional', track_visibility='always')
    partner_seller_id = fields.Many2one(comodel_name='res.partner', string='Vendedor', domain=[('seller', '=', True)], track_visibility='always')
    supplier_id = fields.Many2one(comodel_name='res.partner', string='Proveedor', domain=[('supplier', '=', True)], track_visibility='always')
    currency_id = fields.Many2one(comodel_name='res.currency', string='Moneda', track_visibility='always')
    remito = fields.Char(string='Remito', track_visibility='always')
    attach_remito = fields.Many2many(comodel_name='ir.attachment', relation='prod_attach_precinto', column1='prod_id', column2='attach_remito_id', track_visibility='always')
    costo_estimado = fields.Monetary(string='Costo Indicativo', currency_field='currency_id', track_visibility='always')
    valor_compra_currency_id = fields.Many2one(comodel_name='res.currency', string='Moneda Compra', track_visibility='always')
    valor_compra = fields.Monetary(string='Valor Compra', currency_field='valor_compra_currency_id', track_visibility='always')
    invoiced = fields.Boolean(string='¿Facturado?', track_visibility='always')
    invoiced_supplier = fields.Boolean(string='Es para saber si este servicio ya fue facturado o no', track_visibility='always')
    provision_creada = fields.Boolean(string='Para saber si se creo o no la provision para este servicio', track_visibility='always')
    #Para la vista calendario
    start = fields.Datetime('Inicio', help="Start date of an event, without time for full days events", track_visibility='always')
    stop = fields.Datetime('Fin', help="Stop date of an event, without time for full days events", track_visibility='always')
    allday = fields.Boolean('All Day', default=False)
    start_datetime = fields.Datetime('Start DateTime', track_visibility='always')
    stop_date = fields.Date('End Date', track_visibility='always')
    stop_datetime = fields.Datetime('End Datetime', track_visibility='always')
    cliente_id = fields.Many2one(comodel_name='res.partner', string='Cliente', track_visibility='always')
    seller_commission = fields.Float(string='Comisión Vendedor', track_visibility='always')
    matricula_fletero = fields.Many2one(comodel_name='fleet.vehicle', string='Matricula Fletero', domain=[('is_ras_property', '=', False)], track_visibility='always')
    matricula_dos_fletero = fields.Char(string='Matricula Dos Fletero', track_visibility='always')
    chofer = fields.Char('Chofer', track_visibility='always')
    chofer_sustituto = fields.Boolean('Chofer Sustituto', track_visibility='always')
    #Facturable
    is_invoiced = fields.Boolean('Facturable', help='Marque esta casilla si este servicio se factura', default=True, track_visibility='always')
    tramo_inter = fields.Boolean()
    tramo_nat = fields.Boolean()
    # Es Gasto
    is_outgoing = fields.Boolean('¿Es Gasto?', help='Marque esta casilla si este servicio es un Gasto', default=True, track_visibility='always')
    importe = fields.Float(string='Valor de Venta', store=True, track_visibility='always')
    aduana_origen_id = fields.Many2one('fronteras', 'Depósito de Retiro', track_visibility='always')
    make_aduana_origen_readonly = fields.Boolean()
    make_frontera_visible = fields.Boolean()
    make_terminal_de_vacio_invisible = fields.Boolean()
    make_terminal_de_cargado_invisible = fields.Boolean()
    make_origen_invisible = fields.Boolean()
    make_regimen_exception = fields.Boolean(string='Hacer Regimen Excepcion')
    make_destino_invisible = fields.Boolean()
    ver_importe_flujo = fields.Boolean()
    flujo = fields.Boolean(string="Flujo")
    currency_id_vendedor = fields.Many2one(comodel_name='res.currency', string='Moneda', track_visibility='always')
    currency_id_chofer = fields.Many2one(comodel_name='res.currency', string='Moneda Comisión Chofer', track_visibility='always')
    terminal_return = fields.Many2one(comodel_name='res.partner.address.ext', string=u'Terminal de Devolución', ondelete='restrict', track_visibility='always')
    terminal_ingreso_cargado = fields.Many2one(comodel_name='res.partner.address.ext', string=u'Terminal de Ingreso Cargado', ondelete='restrict', track_visibility='always')
    route = fields.Text('Ruta', track_visibility='always')
    profit_servicio_uyu = fields.Float(string='Profit UYU', readonly=True)
    profit_servicio_usd = fields.Float(string='Profit USD', readonly=True)
    profit_servicios_ids = fields.One2many('rt.product.profit', 'rt_product_id', string='Profit Servicio')
    invisible_in_transit = fields.Boolean()
    make_origin_readonly = fields.Boolean()
    alquilado = fields.Boolean(string='Alquilado', track_visibility='always')
    es_plantilla = fields.Boolean(string='Es plantilla', track_visibility='always')
    # Proveedores
    supplier_ids = fields.One2many('rt.service.product.supplier', 'rt_service_product_id', 'Proveedores', copy=True, track_visibility='always')
    invoiced_rejected = fields.Boolean(string='Factura Rechazada', track_visibility='always')
    corresponde_comision = fields.Boolean(string='¿Corresponde Comisión?', track_visibility='always')
    comision_excepcion = fields.Boolean(string='Comision Eventual', track_visibility='always')
    solo_lectura = fields.Boolean(string='Volver de Solo lectura')
    motivo_solicitud = fields.Char(track_visibility='always')
    estado_comision = fields.Selection([('comision_ok', 'Comisión Válida'), ('correcion_solicitada', 'Correción Solicitada'), ('correcion_aprobada', 'Correción Aprobada'), ('correcion_rechazada', 'Solicitud de Correción Rechazada')], string='Estado de la Comisión', default='comision_ok', track_visibility='always')
    attach_motivo_correcion_comision = fields.Many2many(comodel_name='ir.attachment', relation='attach_motivo_correcion_comision', column1='motivo_id',
                                                        column2='attach_motivo_correcion_comision_id', track_visibility='always')
    regimen_excepcion = fields.Selection(_get_operation_type, string="Regimen Excepcion", store=True)


    motivo_solicitud_costo = fields.Char(track_visibility='always', string='Motivo')
    estado_costo = fields.Selection([('costo_ok', 'Costo Valido'), ('correcion_solicitada', 'Correción Solicitada'), ('correcion_aprobada', 'Correción Aprobada'), ('correcion_rechazada', 'Solicitud de Correción Rechazada')], string='Estado del Costo', default='costo_ok', track_visibility='always')
    attach_motivo_correcion_costo = fields.Many2many(comodel_name='ir.attachment', relation='attach_motivo_correcion_costo', column1='costo_id',column2='attach_motivo_correcion_costo_id', track_visibility='always')
    user_cost_id = fields.Many2one(comodel_name='res.users', string='Usuario Solicitante Correcion Costo', track_visibility='always')
    user_comision_id = fields.Many2one(comodel_name='res.users', string='Usuario Solicitante Correcion Viaje', track_visibility='always')



    @api.multi
    def solicitar_correccion(self):
        for rec in self:
            if not rec.attach_motivo_correcion_comision:
                raise Warning('Debe adjuntar el archivo justificando la correción')
            if not rec.motivo_solicitud:
                raise Warning('Debe ingresar el motivo de la solicitud de correción')
            rec.estado_comision = 'correcion_solicitada'
            rec.user_comision_id = self._context['uid']

        body = u"Motivo de Solicitud: %s" % self.motivo_solicitud
        # message = self.message_post(attachment=[(self.attach_motivo_correcion_comision)])
        message = self.message_post(body=body, message_type='notification', subtype=None, parent_id=False, attachment=[(self.attach_motivo_correcion_comision)])
        message.attachment_ids = self.attach_motivo_correcion_comision

        message_carpeta = self.rt_service_id.message_post(body=body, message_type='notification', subtype=None, parent_id=False, attachment=[(self.attach_motivo_correcion_comision)])
        message_carpeta.attachment_ids = self.attach_motivo_correcion_comision

        odoobot = "odoobot@example.com"
        users_to_nofity = self.env['hr.employee'].search([('revisa_comisiones', '=', True)])
        users_to_send = ''
        if len(users_to_nofity) > 1:
            lastindex = len(users_to_nofity)
            iter = 0
            for user in users_to_nofity:
                iter += 1
                if lastindex != iter:
                    users_to_send += user.user_id.login + ';'
                if lastindex == iter:
                    users_to_send += user.user_id.login

        else:
            users_to_send = users_to_nofity.user_id.login


        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        base_url += '/web?#id=%s&action=935&model=%s&view_type=form&menu_id=%s' % (self.id, self._name, self._name)
        message_body = 'El usuario %s ha solicitado una correccion de Comisión para el siguiente documento ' % self.env['res.users'].browse(self._context['uid']).name
        message_body += '<br/>'
        message_body += 'Motivo: %s' % self.motivo_solicitud
        message_body += '<br/>'
        message_body += "<a href='%s' > Haga click aqui para ver </a>" % base_url



        mail = self.env['mail.mail']
        mail_data = {'subject': 'Solicitud de Correccion de Comision : ' + self.motivo_solicitud,
                     'email_from': odoobot,
                     'email_to': users_to_send,
                     'body_html': message_body,
                     'attachment_ids': [(6, 0, [att.id for att in self.attach_motivo_correcion_comision])],
                     }
        mail_out = mail.create(mail_data)
        mail_out.send()

        return True

    @api.multi
    def aprobar_correcion(self):
        for rec in self:
            rec.estado_comision = 'correcion_aprobada'

        body = 'Solicitud de correción aprobada'
        # message = self.message_post(attachment=[(self.attach_motivo_correcion_comision)])
        message = self.message_post(body=body, message_type='notification', subtype=None, parent_id=False)

        message_carpeta = self.rt_service_id.message_post(body=body, message_type='notification', subtype=None, parent_id=False)

        odoobot = "odoobot@example.com"
        user_to_notify = self.user_comision_id.login

        message_body = 'Su solicitud de correción de viaje ha sido aprobada'
        message_body += '<br/>'


        mail = self.env['mail.mail']
        mail_data = {'subject': 'Solicitud de Corrección de Comisión Aprobada',
                     'email_from': odoobot,
                     'email_to': user_to_notify,
                     'body_html': message_body,
                     }
        mail_out = mail.create(mail_data)
        mail_out.send()

        return True

    @api.multi
    def aprobar_correcion_costo(self):
        for rec in self:
            rec.estado_costo = 'correcion_aprobada'
        body = 'Solicitud de correción aprobada'
        # message = self.message_post(attachment=[(self.attach_motivo_correcion_comision)])
        message = self.message_post(body=body, message_type='notification', subtype=None, parent_id=False)

        message_carpeta = self.rt_service_id.message_post(body=body, message_type='notification', subtype=None, parent_id=False)

        odoobot = "odoobot@example.com"
        user_to_notify = self.user_cost_id.login

        message_body = 'Su solicitud de correción de costo ha sido aprobada'
        message_body += '<br/>'


        mail = self.env['mail.mail']
        mail_data = {'subject': 'Solicitud de Corrección de costo aprobada',
                     'email_from': odoobot,
                     'email_to': user_to_notify,
                     'body_html': message_body,
                     }
        mail_out = mail.create(mail_data)
        mail_out.send()
        return True

    @api.multi
    def rechazar_correcion_costo(self):
        for rec in self:
            if not rec.self.motivo_rechazo:
                raise Warning('Debe ingresar un motivo para la solicitud de correción')
            rec.estado_costo = 'correcion_rechazada'
            rec.user_cost_id = self._context['uid']

        body = u"Motivo Rechazo de Solicitud: %s" % self.motivo_rechazo
        message = self.message_post(body=body, message_type='notification', subtype=None, parent_id=False)
        message_carpeta = self.rt_service_id.message_post(body=body, message_type='notification', subtype=None, parent_id=False)
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')

        base_url += '/web?#id=%s&action=935&model=%s&view_type=form&menu_id=%s' % (rec.id, rec._name, rec._name)
        message_body = 'El usuario %s ha rechazado una solicitud de  corrección de Comisión para el siguiente documento ' % self.env['res.users'].browse(self._context['uid']).name
        message_body += '<br/>'
        message_body += 'Motivo: %s' % self.motivo
        message_body += '<br/>'
        message_body += "<a href='%s' > Haga click aquí para ver </a>" % base_url
        odoobot = "odoobot@example.com"
        user_to_notify = rec.user_cost_id.login
        mail = self.env['mail.mail']
        mail_data = {'subject': 'Solicitud de Corrección de Comisión Rechazada: ' + self.motivo,
                     'email_from': odoobot,
                     'email_to': user_to_notify,
                     'body_html': message_body,
                     }
        mail_out = mail.create(mail_data)
        mail_out.send()
        return True

    @api.multi
    def rechazar_correcion_comision(self):
        for rec in self:
            rec.estado_comision = 'correcion_rechazada'
        body = u"Motivo Rechazo de Solicitud: %s" % self.motivo_rechazo
        message = self.message_post(body=body, message_type='notification', subtype=None, parent_id=False)
        message_carpeta = self.rt_service_id.message_post(body=body, message_type='notification', subtype=None, parent_id=False)
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')

        base_url += '/web?#id=%s&action=935&model=%s&view_type=form&menu_id=%s' % (rec.id, rec._name, rec._name)
        message_body = 'El usuario %s ha rechazado una solicitud de  corrección de Comisión para el siguiente documento ' % self.env['res.users'].browse(self._context['uid']).name
        message_body += '<br/>'
        message_body += 'Motivo: %s' % self.motivo
        message_body += '<br/>'
        message_body += "<a href='%s' > Haga click aquí para ver </a>" % base_url
        odoobot = "odoobot@example.com"
        user_to_notify = rec.user_comision_id.login
        mail = self.env['mail.mail']
        mail_data = {'subject': 'Solicitud de Corrección de Comisión Rechazada: ' + self.motivo,
                     'email_from': odoobot,
                     'email_to': user_to_notify,
                     'body_html': message_body,
                     }
        mail_out = mail.create(mail_data)
        mail_out.send()
        return True





    @api.multi
    def solicitar_correccion_costo(self):

        for rec in self:
            if not rec.motivo_solicitud_costo:
                raise Warning('Debe ingresar un motivo para la solicitud de correción de costo')
            if not rec.attach_motivo_correcion_costo:
                raise Warning('Debe ingresar un adjunto para la solicitud de correción de costo')
            rec.estado_costo = 'correcion_solicitada'
            rec.user_cost_id = self._context['uid']

        body = u"Motivo de Solicitud: %s" % self.motivo_solicitud_costo
        message = self.message_post(body=body, message_type='notification', subtype=None, parent_id=False, attachment=[(self.attach_motivo_correcion_costo)])
        message.attachment_ids = self.attach_motivo_correcion_costo

        message_carpeta = self.rt_service_id.message_post(body=body, message_type='notification', subtype=None, parent_id=False, attachment=[(self.attach_motivo_correcion_costo)])
        message_carpeta.attachment_ids = self.attach_motivo_correcion_costo

        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        base_url += '/web?#id=%s&action=940&model=%s&view_type=form&menu_id=%s' % (self.id, self._name, self._name)
        message_body = 'El usuario %s ha solicitado una corrección de Costo para el siguiente documento ' % self.env['res.users'].browse(self._context['uid']).name
        message_body += '<br/>'
        message_body += 'Motivo: %s' % self.motivo_solicitud_costo
        message_body += '<br/>'
        message_body += "<a href='%s' > Haga click aqui para ver </a>" % base_url



        users_to_nofity = self.env['hr.employee'].search([('revisa_costos', '=', True)])

        users_to_send = ''

        if len(users_to_nofity) > 1:
            lastindex = len(users_to_nofity)
            iter = 0
            for user in users_to_nofity:
                iter += 1
                if lastindex != iter:
                    users_to_send += user.user_id.login + ';'
                if lastindex == iter:
                    users_to_send += user.user_id.login

        else:
            users_to_send = users_to_nofity.user_id.login

        odoobot = "odoobot@example.com"
        mail = self.env['mail.mail']
        mail_data = {'subject': 'Solicitud de Corrección de Costo : ' + self.motivo_solicitud_costo if self.motivo_solicitud_costo else 'N/A',
                     'email_from': odoobot,
                     'email_to': users_to_send,
                     'body_html': message_body,
                     }
        mail_out = mail.create(mail_data)
        mail_out.send()


        return True



    @api.onchange('flujo', 'action_type_id')
    def onchange_flujo(self):
        # FLUJO
        if self.operation_type == 'international' and self.flujo:
            if self.action_type_id.name != 'Frontera':
                self.make_frontera_visible = False
            if self.action_type_id.name == 'Frontera':
                self.make_frontera_visible = True
            if self.action_type_id.name == 'Frontera' or self.action_type_id.name == 'Salida' or self.action_type_id.name == 'Descarga':
                self.ver_importe_flujo = True
            else:
                self.ver_importe_flujo = False





    @api.multi
    def write(self, values):
        """
        Escribimos y luego vemos si el estado es el correcto
        La idea es recorrer las lineas y si son facturadas ver si
        la factura esta rechazada y asi actualizar el estado de la carpeta
        :param values:
        :return:
        """
        producto = super(rt_service_productos, self).write(values)
        carpeta = self.rt_service_id
        estados_productos = []
        estados_invoiced = []
        for carp in carpeta:
            for carga in carp.carga_ids:
                for prod in carga.producto_servicio_ids:
                    if prod.is_invoiced:
                        estados_productos.append(prod.invoiced_rejected)
                        estados_invoiced.append(prod.invoiced)

        if not any(estados_productos):
            if any(estados_invoiced):
                carpeta.stae = 'progress'

        return producto


    def get_pricelist_item_to_product(self):
        if self.pricelist_id:
            expense = self.env['default.expenses'].search([('pricelist_item_parent_id', '=', self.pricelist_id.id), ('product_id', '=', self.product_id.id)])
            if expense:
                self.currency_id = expense.currency_id.id
                self.importe = expense.sale_price
        else:
            expense = self.env['default.expenses'].search([('product_id', '=', self.product_id.id)], limit=1)
            if expense:
                self.currency_id = expense.currency_id.id
                self.importe = expense.sale_price
        return



    @api.onchange('product_id')
    def _onchange_product_id(self):
        res = {}
        names = []
        domain = {}
        if self.product_type == 'terceros':
            self.supplier_id = False
            if self.product_id.seller_ids:
                if len(self.product_id.seller_ids) > 1:
                    for line in self.product_id.seller_ids:
                        names.append(line.name.id)
                    domain = {'supplier_id': [('id', 'in', names)]}
                else:
                    self.supplier_id = self.product_id.seller_ids.name.id
            else:
                names = self.env['res.partner'].search([('supplier', '=', True)]).ids
                domain = {'supplier_id' : [('id', 'in', names)]}
        if self.product_id:
            if self.product_id.name == 'Verificación':
                self.get_pricelist_item_to_product()

            if self.product_id.name == 'Estadia':
                self.get_pricelist_item_to_product()

            if self.product_id.name == 'Desconsolidacion contenedor de 20':
                self.get_pricelist_item_to_product()

            if self.product_id.name == 'Desconsolidacion contenedor de 40':
                self.get_pricelist_item_to_product()

            if self.product_id.name == 'Almacenaje':
                self.get_pricelist_item_to_product()

        if domain:
            res['domain'] = domain
        return res

    @api.onchange('product_type')
    def _cargar_dominio_vehiculo(self):
        domain = {}
        warning = {}
        res = {}
        fleet_obj = self.env['fleet.vehicle']
        fleet_vehicle_id = fleet_obj.search([('state_id', 'in', ('Tractores', 'Camiones', 'Camionetas'))])
        fleet_matricula_dos_id = fleet_obj.search([('state_id', 'in', 'Semi Remolques y Remolques')])
        domain = {'vehicle_id': [('id', 'in', fleet_vehicle_id.ids)], 'matricula_dos_id': [('id', 'in', fleet_matricula_dos_id.ids)]}
        if not self.partner_invoice_id:
            if self.rt_carga_id.partner_invoice_id:
                self.partner_invoice_id = self.rt_carga_id.partner_invoice_id.id
            else:
                print('EEEEEEEEEEEEERRRRRRRRRRRRRRRRRRRRRRRROOOOOOOOOOOOOOOOOOOOORRRRRRRRRRRRRRRRRRRRRRR')
        if (not self.pricelist_id) or self.pricelist_id.pricelist_id.es_generica:
            if self.partner_invoice_id:
                self.partner_seller_id = self.partner_invoice_id.user_id.id

        if warning:
            res['warning'] = warning
        if domain:
            res['domain'] = domain
        return res

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

    @api.onchange('vehicle_id', 'matricula_dos_id')
    def _onchange_vehicle(self):
        """
        Funcion temporaria que impide al usuario cargas vehiculos que no debe
        :return:
        """
        domain = {}
        res = {}
        fleet_obj = self.env['fleet.vehicle']
        employee_obj = self.env['hr.employee']
        employee_obj_categ = self.env['hr.employee.category']
        driver_categ = employee_obj_categ.search([('name', '=', 'Chofer')]).id
        driver_categ_inter = employee_obj_categ.search([('name', '=', 'Internacional')]).id
        driver_categ_nat = employee_obj_categ.search([('name', '=', 'Nacional')]).id

        condiciones_busqueda = []
        condiciones_busqueda.append(('category_ids.name', '=', 'Chofer'))
        if condiciones_busqueda:
            employee = employee_obj.search(condiciones_busqueda)
        else:
            employee = employee_obj.search([])

        domain = {'driver_id': [('id', 'in', employee.ids)]}


        if self.vehicle_id:
            if self.vehicle_id.state_id.name not in ('Tractores', 'Camiones', 'Camionetas'):
                self.vehicle_id  = False
                raise Warning('El vehiculo debe tener una matricula \n No puede elegir un contenedor \n Selecione: Tractores, Camiones o Camionetas')

        if self.matricula_dos_id:
            if self.matricula_dos_id.state_id.name not in ('Semi Remolques y Remolques'):
                self.matricula_dos_id = False
                raise Warning('Solo puede selecionar Semi Remolques y Remolques')

        if self.vehicle_id:
            self.driver_id = self.vehicle_id.driver_id.id

        if domain:
            res['domain'] = domain
        return res

    @api.onchange('driver_id')
    def _onchange_driver(self):
        if self.driver_id:
            if self.driver_id.job_id.x_studio_categora_mtss == 'A2 - Chofer de Camión y Camioneta':
                self.comision_eventual = True
                self.driver_commission = False
                self.currency_id_chofer = False
            if self.driver_id.job_id.x_studio_categora_mtss == 'A3 - Chofer de semirremolque':
                self.comision_eventual = False


    def create_profit_line_cost(self, line):
        return {
            'rt_product_id': line.id,
            'name': line.name,
            'venta': 0,
            'costo': 0,
        }

    def create_profit_line_sale(self, line):
        return {
            'rt_product_id': line.id,
            'name': line.name,
            'venta': 0,
            'costo': 0,
        }

    def convert_to_pesos(self, amount):
        curr_obj = self.env['res.currency']
        cot = curr_obj.search([('name', '=', 'USD')])
        return amount * cot.rate

    def convert_to_dolares(self, amount):
        curr_obj = self.env['res.currency']
        cot = curr_obj.search([('name', '=', 'USD')])
        return amount / cot.rate

    @api.multi
    def compute_service_profit(self):
        rt_product_id = fields.Many2one(comodel_name='rt.service.productos', string='Servicio Relacionado')
        # currency_operation = fields.Many2one('res.currency')
        # name = fields.Char(string='Concepto')
        # venta = fields.Monetary(string='Venta', default=0.0, currency_field='currency_operation')
        # costo = fields.Monetary(string='Costo', default=0.0, currency_field='currency_operation')
        # usd_currency_id = fields.Many2one('res.currency')
        # uyu_currency_id = fields.Many2one('res.currency')
        #
        # venta_usd = fields.Monetary(string='Venta USD', default=0.0, currency_field='usd_currency_id')
        # costo_usd = fields.Monetary(string='Costo USD', default=0.0, currency_field='usd_currency_id')
        #
        # venta_uyu = fields.Monetary(string='Venta UYU', default=0.0, currency_field='uyu_currency_id')
        # costo_uyu = fields.Monetary(string='Costo UYU', default=0.0, currency_field='uyu_currency_id')


        lineas = []
        line_dict = {}
        self.profit_servicios_ids = False
        for srv in self:
            if srv.product_type == 'propio':
                line_dict['rt_product_id'] = self.id
                line_dict['name'] = 'Flete'
                line_dict['venta'] = srv.importe
                line_dict['venta_usd'] = self.convert_to_dolares(srv.importe) if self.currency_id.name != 'USD' else srv.importe
                line_dict['venta_uyu'] = self.convert_to_pesos(srv.importe) if self.currency_id.name == 'USD' else srv.importe
                line_dict['usd_currency_id'] = 2
                line_dict['uyu_currency_id'] = 46
                line_dict['currency_operation'] = self.currency_id.id
                lineas.append((0, 0, line_dict))
                line_dict = {}
                if srv.costo_estimado:
                    line_dict['rt_product_id'] = self.id
                    line_dict['name'] = 'Chofer'
                    line_dict['costo'] = srv.costo_estimado
                    line_dict['costo_usd'] = self.convert_to_dolares(srv.costo_estimado) if self.currency_id.name != 'USD' else srv.costo_estimado
                    line_dict['costo_uyu'] = self.convert_to_pesos(srv.costo_estimado) if self.currency_id.name == 'USD' else srv.costo_estimado
                    line_dict['usd_currency_id'] = 2
                    line_dict['uyu_currency_id'] = 46
                    line_dict['currency_operation'] = self.currency_id.id
                    lineas.append((0, 0, line_dict))
        self.profit_servicios_ids = lineas
        self.profit_servicio_usd = sum(pro.venta_usd for pro in self.profit_servicios_ids.filtered(lambda x: x.venta_usd)) - sum(pro.costo_usd for pro in self.profit_servicios_ids.filtered(lambda x: x.costo_usd))
        self.profit_servicio_uyu = sum(pro.venta_uyu for pro in self.profit_servicios_ids.filtered(lambda x: x.venta_uyu)) - sum(pro.costo_uyu for pro in self.profit_servicios_ids.filtered(lambda x: x.costo_uyu))


    @api.multi
    @api.depends('html_field')
    def get_info_from_nodes(self):
        lista = [1,2,3]
        saldo = 20
        dua = ''
        dua_linea = ''
        table = ''
        table += '<table style="width:100%;">'
        table += '<thead style="border: thin solid gray;">'
        table += '<tr style="border: thin solid gray;">'
        table += '<th style="border: thin solid gray; text-align: center">Concepto</th>'
        table += '<th style="border: thin solid gray; text-align: center">Costo</th>'
        table += '<th style="border: thin solid gray; text-align: center">Venta</th>'
        table += '</tr style="border: thin solid gray;">'
        table += '</thead>'
        table += '<tbody>'
        for line in self:
            table += '<tr style="border: thin solid gray;">'
            #Concepto
            table += '<td style="border: thin solid gray;text-align:center;"````>%(dep)s</td>' % {'dep': 'Viaje'}
            #Costo
            table += '<td style="border: thin solid gray;text-align:center;"````>%(dep)s</td>' % {'dep': line.driver_commission}
            #Venta
            table += '<td style="border: thin solid gray;text-align:center;"````>%(dep)s</td>' % {'dep': line.importe}

        #TOTALES
        for line in range(1):
            table += '<tr style="border: thin solid gray;">'
            table += '<td style="border: thin solid gray;text-align:center;"````></td>'
            table += '<td style="border: thin solid gray;text-align:center;"````></td>'
            table += '<td style="border: thin solid gray;text-align:center;"````></td>' % {'dep': 39392}
            table += '</tr>'

        table += '</tbody>'
        table += '</table>'
        self.profit_servicio = table

    @api.onchange('supplier_id', 'action_type_id', 'product_type', 'pricelist_id', 'vehicle_id', 'matricula_fletero')
    def _onchange_product_type(self):
        condiciones_busqueda = []
        pricelist_item_obj = self.env['product.pricelist.item']
        carpeta = self.rt_carga_id.rt_service_id
        partner = carpeta.partner_invoice_id.id
        pesos = self.env['res.currency'].search([('name', '=', 'UYU')])
        dolares = self.env['res.currency'].search([('name', '=', 'USD')])
        for rec in self:
            # if rec.action_type_id.name != 'Viaje':
            #     rec.importe = 0
            #     rec.currency_id = False
            if rec.product_type:
                pricelist_item = rec.pricelist_id
                if pricelist_item:
                    rec.aduana_origen_id = pricelist_item.aduana_origen_id.id
                    rec.make_aduana_origen_readonly = True
                    if pricelist_item.partner_seller_id:
                        rec.partner_seller_id = pricelist_item.partner_seller_id.id
                    if not rec.driver_commission:
                        rec.driver_commission = 0
                        rec.currency_id_chofer = False
                    # rec.driver_commission = pricelist_item.comision_chofer
                    # rec.seller_commission = pricelist_item.comision_vendedor
                    # rec.currency_id_chofer = pricelist_item.comision_chofer_currency_id.id
                    # rec.currency_id_vendedor = pricelist_item.comision_vendedor_currency_id.id
            if rec.action_type_id.name == 'Viaje' and rec.product_id.name != 'Verificación':
                if rec.operation_type == 'national':
                    rec.valor_compra_currency_id = pesos.id
                if rec.operation_type == 'international':
                    rec.valor_compra_currency_id = dolares.id
                if rec.product_type:
                    pricelist_item = rec.pricelist_id
                    if pricelist_item:
                        rec.importe = pricelist_item.sale_price
                        rec.currency_id = pricelist_item.currency_id.id
                        rec.aduana_origen_id = pricelist_item.aduana_origen_id.id
                        rec.make_aduana_origen_readonly = True
                        if pricelist_item.partner_seller_id:
                            rec.partner_seller_id = pricelist_item.partner_seller_id.id
                        rec.driver_commission = pricelist_item.comision_chofer
                        rec.seller_commission = pricelist_item.comision_vendedor
                        rec.currency_id_chofer = pricelist_item.comision_chofer_currency_id.id
                        rec.currency_id_vendedor = pricelist_item.comision_vendedor_currency_id.id



            if rec.action_type_id.name == 'Retiro de Vacío':
                rec.make_terminal_de_cargado_invisible = True
                rec.is_invoiced = False

            if rec.action_type_id and rec.product_id.name == 'Flete':
                if rec.action_type_id.name != 'Viaje':
                    rec.is_invoiced = False
                if rec.action_type_id.name == 'Viaje':
                    rec.is_invoiced = True
            else:
                rec.is_invoiced = True;

            if rec.action_type_id.name == 'Ingreso Cargado' or rec.action_type_id.name == 'Retiro de Cargado':
                rec.driver_commission = 150

            rec.make_terminal_de_vacio_invisible = True
            if not rec.action_type_id.name == 'Retiro de Vacío':
                rec.make_terminal_de_cargado_invisible = False
            if rec.action_type_id.name == 'Liberación fiscal':
                rec.make_origen_invisible = True
                rec.make_destino_invisible = True
            if not rec.action_type_id.name == 'Liberación fiscal':
                rec.make_origen_invisible = False
                rec.make_destino_invisible = False
            if rec.action_type_id.name == 'Carga':
                rec.make_destino_invisible = True
            if not rec.action_type_id.name == 'Carga':
                rec.make_destino_invisible = False



    @api.onchange('cliente_id', 'rt_carpeta_id')
    def _onchange_cliente_id(self):
        res = {}
        folder_obj = self.env['rt.service']
        carga_obj = self.env['rt.service.carga']
        cargas = []
        ctx = self._context.copy()
        cliente = False
        folder_id = False
        if self.cliente_id:
            cliente = self.cliente_id.id
        if 'is_from_calendar_view' in ctx:
            folders = folder_obj.search([('partner_invoice_id', '=', cliente)])
            domain = {'rt_carpeta_id': [('id', 'in', folders.ids)]}

            if self.rt_carpeta_id:
                cargas = self.rt_carpeta_id.carga_ids.ids
                domain['rt_carga_id'] = [('id', 'in', cargas)]

            if domain:
                res['domain'] = domain
        return res

    @api.onchange('currency_id')
    def onchange_service_values(self):
        res = {}
        address_obj = self.env['res.partner.address.ext']
        partner_obj = self.env['res.partner']
        partner_id = self.pricelist_id.partner_id.id
        partner_playa = partner_obj.search([('playa', '=', True)])
        return res

    @api.onchange('action_type_id', 'product_type')
    def onchange_aduana_origen_id(self):
        domain = {}
        warning = {}
        res = {}
        address_obj = self.env['res.partner.address.ext']
        partner_obj = self.env['res.partner']
        partner_id = self.partner_id.id
        partner_playa = partner_obj.search([('playa', '=', True)])
        aduana_obj = self.env['fronteras']

        if self.operation_type == 'national':
            if self.regimen in ('impo_nat', 'impo_inter'):
                if self.load_type == 'contenedor':
                    if self.product_id.name == 'Flete':
                        for rt in self.rt_carga_id.producto_servicio_ids:
                            terminal = rt.rt_carga_id.terminal_return.id

                            if self.action_type_id.name == 'Viaje':
                                if rt.action_type_id.name == 'Retiro de Cargado':
                                    self.origin_id = rt.destiny_id.id
                                self.terminal_return = rt.rt_carga_id.terminal_return.id
                                dir_partners = address_obj.search(
                                    [('partner_id', '=', partner_id), ('address_type', '=', 'load')]).ids
                                domain = {'destiny_id': [('id', 'in', dir_partners)]}

                            if self.action_type_id.name == 'Viaje':
                                dir_partners = address_obj.search(
                                    [('partner_id', '=', partner_id), ('address_type', '=', 'load')]).ids
                                domain = {'destiny_id': [('id', 'in', dir_partners)]}
                                res['domain'] = domain

                            if self.action_type_id.name == 'Devolucion de Vacio':
                                if rt.action_type_id.name == 'Viaje':
                                    if rt.terminal_return:
                                        self.origin_id = rt.terminal_return.id
                                        self.destiny_id = rt.rt_carga_id.terminal_return.id
                if self.load_type == 'bulk':
                    self.make_origin_readonly = True
                    dua_aduana = self.rt_carga_id.dua_aduana
                    aduana = aduana_obj.search([('codigo_dna', '=', dua_aduana), ('country_id', '=', 234)])
                    if len(aduana) == 1:
                        origenes = address_obj.search(
                            [('address_type', '=', 'load'), ('aduana_id', '=', aduana.id)]).ids
                    else:
                        origenes = address_obj.search(
                            [('address_type', '=', 'load'), ('aduana_id', 'in', aduana.ids)]).ids
                    destinos = address_obj.search([('address_type', '=', 'load')]).ids
                    domain = {'origin_id': [('id', 'in', origenes)], 'destiny_id': [('id', 'in', destinos)]}

                if self.load_type == 'bulk':
                    self.make_origin_readonly = True
                    for rt in self.rt_carga_id:
                        if rt.origin_id:
                            self.origin_id = rt.origin_id.id
                        if rt.destiny_id:
                            self.destiny_id = rt.destiny_id.id

            if self.regimen in ('impo_nat', 'impo_inter'):
                if self.load_type == 'contenedor':
                    if self.action_type_id.name == 'Viaje':
                        dir_partners = address_obj.search(
                            [('partner_id', '=', partner_id), ('address_type', '=', 'load')]).ids
                        puertos = address_obj.search(
                            [('partner_id', '=', partner_playa.ids), ('address_type', '=', 'beach_load')]).ids
                        domain = {'origin_id': [('id', 'in', puertos)], 'destiny_id': [('id', 'in', dir_partners)]}
                        if self.product_id.name == 'Flete':
                            self.destiny_id = self.pricelist_id.destiny_dir.id
                        if self.action_type_id.name == 'Viaje':
                            self.terminal_return = self.rt_carga_id.terminal_return.id

                    if self.action_type_id.name == 'Retiro de Cargado':
                        destiny = address_obj.search(
                            [('partner_id', 'in', partner_playa.ids), ('aduana_id', '=', False)]).ids
                        puertos = address_obj.search(
                            [('partner_id', '=', partner_playa.ids), ('address_type', '=', 'beach_load')]).ids
                        domain = {'origin_id': [('id', 'in', puertos)], 'destiny_id': [('id', 'in', destiny)]}

            if self.regimen in ('expo_nat', 'expo_inter'):
                if self.load_type == 'contenedor':
                    self.terminal_ingreso_cargado = self.rt_carga_id.terminal_ingreso_cargado.id
                    if self.product_id.name == 'Flete' and self.action_type_id.name == 'Retiro de Vacio':
                        self.origin_id = self.rt_carga_id.terminal_retreat.id
                        playas = address_obj.search(
                            [('partner_id', '=', partner_playa.ids), ('address_type', '=', 'beach_empty')]).ids
                        domain = {'destiny_id': [('id', 'in', playas)]}

                    if self.product_id.name == 'Flete':
                        for rt in self.rt_carga_id.producto_servicio_ids:
                            if self.action_type_id.name == 'Viaje':
                                if rt.action_type_id.name == 'Retiro de Vacio':
                                    if rt.destiny_id:
                                        self.origin_id = rt.destiny_id.id
                                        self.terminal_ingreso_cargado = rt.rt_carga_id.terminal_ingreso_cargado.id
                                        depositos_cliente = address_obj.search(
                                            [('partner_id', '=', partner_id), ('address_type', '=', 'load')]).ids
                                        domain = {'destiny_id': [('id', 'in', depositos_cliente)]}

                            if self.action_type_id.name == 'Ingreso Cargado':
                                if rt.action_type_id.name == 'Viaje':
                                    self.origin_id = rt.terminal_ingreso_cargado.id
                                    self.destiny_id = rt.rt_carga_id.terminal_ingreso_cargado.id

                            if self.action_type_id.name == 'Devolucion de Vacio':
                                if rt.action_type_id.name == 'Retiro de Vacio':
                                    self.origin_id = rt.destiny_id.id
                                    self.destiny_id = rt.rt_carga_id.terminal_retreat.id

            if self.regimen in ('transit_nat', 'transit_inter'):
                if self.load_type == 'contenedor':
                    self.terminal_ingreso_cargado = self.rt_carga_id.terminal_ingreso_cargado.id
                    aduana_origen = self.rt_carga_id.aduana_origen_id.id
                    aduana_destino = self.rt_carga_id.aduana_destino_id.id
                    origenes = address_obj.search(
                        [('partner_id', 'in', partner_playa.ids), ('aduana_id', '=', aduana_origen),
                         ('address_type', '=', 'beach_load')])
                    destinos = address_obj.search(
                        [('aduana_id', '=', aduana_destino), ('address_type', 'in', ('beach_load', 'load'))])
                    domain = {'origin_id': [('id', 'in', origenes.ids)], 'destiny_id': [('id', 'in', destinos.ids)]}
                    self.destiny_id = self.pricelist_id.destiny_dir.id
                    self.terminal_return = self.rt_carga_id.terminal_return.id

                    if self.action_type_id.name == 'Retiro de Vacío':
                        self.origin_id = self.rt_carga_id.terminal_retreat.id
                        destinos = address_obj.search([('address_type', '=', 'beach_empty')])
                        domain = {'destiny_id': [('id', 'in', destinos.ids)]}
                    if self.action_type_id.name == 'Viaje':
                        for rt in self.rt_carga_id.producto_servicio_ids:
                            if rt.action_type_id.name == 'Retiro de Vacio':
                                self.origin_id = rt.destiny_id.id
                                depositos_cliente = address_obj.search(
                                    [('partner_id', '=', partner_id), ('address_type', '=', 'load')]).ids
                                domain = {'destiny_id': [('id', 'in', depositos_cliente)]}
                                self.terminal_ingreso_cargado = self.rt_carga_id.terminal_ingreso_cargado.id

        # if self.operation_type == 'international':
        #     if self.regimen in ('impo_nat', 'impo_inter'):
        #
        #
        #     if self.regimen in ('expo_nat', 'expo_inter'):
        #         if self.load_type == 'bulk':
        #             dua_aduana = self.rt_carga_id.dua_aduana
        #             aduana = aduana_obj.search([('codigo_dna', '=', dua_aduana), ('country_id', '=', 234)])
        #             if len(aduana) == 1:
        #                 destinos = address_obj.search([('address_type', '=', 'load'),('aduana_id', '=', aduana.id)]).ids
        #             else:
        #                 destinos = address_obj.search([('address_type', '=', 'load'), ('aduana_id', 'in', aduana.ids)]).ids
        #             origenes = address_obj.search([('partner_id', '=', partner_id)]).ids
        #             domain = {'origin_id': [('id', 'in', origenes)], 'destiny_id': [('id', 'in', destinos)]}

        if warning:
            res['warning'] = warning
        if domain:
            res['domain'] = domain
        return res

    @api.onchange('action_type_id')
    def onchange_action_type_id(self):
        domain = {}
        warning = {}
        res = {}
        action_type_obj = self.env['tipo.accion']
        retiro_vacio = action_type_obj.search([('name', '=', 'Retiro de Vacío')])
        pricelist = self.env['product.pricelist']
        pricelist_item = self.env['product.pricelist.item']
        verificacion_prod = self.env['product.product'].search([('name', '=', 'Verificación')])
        expense = self.env['default.expenses']
        if self.action_type_id:
            if self.action_type_id.name == 'Verificación':
                item = expense.search([('product_id', '=', verificacion_prod.id), ('pricelist_item_parent_id', '!=', False)])
                if item:
                    if len(item) > 1:
                        ver_mas_cara = max([x.sale_price for x in item])
                        for it in item:
                            if it.sale_price == ver_mas_cara:
                                new_item = it
                        self.currency_id = new_item.pcurrency_id.id
                        self.importe = new_item.sale_price

                    if len(item) == 1:
                        self.currency_id = item.pcurrency_id.id
                        self.importe = item.sale_price

                #Si no encuentra le ponemos 3 mil pesos
                else:
                    self.currency_id = 46
                    self.importe = 30000

            if self.action_type_id.name == 'Retiro de Vacío':
                item = expense.search([('action_type_id', '=', retiro_vacio.id), ('pricelist_item_parent_id', '!=', False)])
                if item:
                    if len(item) > 1:
                        item_mas_caro = max([x.sale_price for x in item])
                        for it in item:
                            if it.sale_price == item_mas_caro:
                                new_item = expense.browse(it.id)
                        self.driver_commission = new_item.comision
                        self.currency_id_chofer = new_item.currency_id.id
                        self.seller_commission = 0.0

                    elif len(item) == 1:
                        self.driver_commission = item.comision
                        self.currency_id_chofer = item.currency_id.id
                        self.seller_commission = 0.0

                    #Si no encuentro nada pongo 150
                    else:
                        self.driver_commission = 150
                        self.currency_id_chofer = 46


            if self.action_type_id.name == 'Salida' or self.action_type_id.name == 'Frontera':
                self.make_frontera_nacional_visible = True
            if self.action_type_id.name != 'Salida' and self.action_type_id.name != 'Frontera':
                self.make_frontera_nacional_visible = False
            if self.action_type_id.name == 'Arribo a fiscal' or self.action_type_id.name == 'Frontera':
                self.make_frontera_internacional_visible = True
            if self.action_type_id.name != 'Arribo a fiscal' and self.action_type_id.name != 'Frontera':
                self.make_frontera_internacional_visible = False

        if self.operation_type == 'national':
            if self.load_type == 'contenedor':
                operation_search = self.action_type_id.search(
                    [('nacional', '=', True), ('contenedores', '=', True)]).ids
                domain = {'action_type_id': [('id', 'in', operation_search)]}
            if self.load_type == 'bulk':
                operation_search = self.action_type_id.search(
                    [('nacional', '=', True), ('carga_suelta', '=', True)]).ids
                domain = {'action_type_id': [('id', 'in', operation_search)]}

        if self.operation_type == 'international':
            if self.load_type == 'contenedor':
                operation_search = self.action_type_id.search(
                    [('internacional', '=', True), ('contenedores', '=', True)]).ids
                domain = {'action_type_id': [('id', 'in', operation_search)]}
            if self.load_type == 'bulk':
                operation_search = self.action_type_id.search(
                    [('internacional', '=', True), ('carga_suelta', '=', True)]).ids
                domain = {'action_type_id': [('id', 'in', operation_search)]}
        for rec in self:
            if rec.rt_carga_id.raw_kg:
                if rec.partner_invoice_id.name == 'Flavio Aleman':
                    if rec.pricelist_id:
                        rec.importe = rec.pricelist_id.sale_price * (rec.rt_carga_id.raw_kg/1000)
                        rec.currency_id = rec.pricelist_id.currency_id.id
                        rec.driver_commission = rec.pricelist_id.comision_chofer
                        rec.currency_id_chofer = rec.pricelist_id.comision_chofer_currency_id.id
                        rec.partner_seller_id = rec.pricelist_id.partner_seller_id.id
                if rec.rt_carga_id:
                    rec.origin_id = rec.rt_carga_id.origin_id.id
                    rec.destiny_id = rec.rt_carga_id.destiny_id.id

        if self.product_id.name == 'Flete':
            fleteros_obj = self.env['res.partner'].search([('supplier', '=', True), ('freighter', '=', True)]).ids
            domain['supplier_id'] = [('id', 'in', fleteros_obj)]

        if warning:
            res['warning'] = warning
        if domain:
            res['domain'] = domain
        return res

    @api.onchange('pricelist_id')
    def onchange_pricelist_id(self):
        domain = {}
        warning = {}
        res = {}
        regimen_tarifa = self.rt_service_id.regimen
        cliente = self.rt_service_id.pricelist_id.partner_id.id
        linea_tarifa_obj = self.env['product.pricelist.item']
        tarifa = linea_tarifa_obj.search([('partner_id', '=', cliente), ('regimen', '=', regimen_tarifa)]).ids
        domain = {'pricelist_id': [('id', 'in', tarifa)]}

        if self.pricelist_id:
            self.importe_currency_id = self.pricelist_id.currency_id
            self.importe = self.pricelist_id.sale_price

        if warning:
            res['warning'] = warning
        if domain:
            res['domain'] = domain
        return res

    def get_tack_id(self):
        if self.rt_carga_id.container_number:
            return self.rt_carga_id.container_number
        else:
            return ' '

    def get_dua(self):
        dua = ''
        if self.rt_service_id.dua_type == 'cabezal':
            carpeta = self.rt_service_id
            dua = carpeta.dua_aduana + '-' if carpeta.dua_aduana else ''
            dua += carpeta.dua_anio + '-' if carpeta.dua_anio else ''
            dua += carpeta.dua_numero if carpeta.dua_numero else ''
        elif self.rt_service_id.dua_type == 'linea':
            carga = self.rt_carga_id
            if not carga.multiple_dua:
                dua = carga.dua_aduana + '-' if carga.dua_aduana else ''
                dua += carga.dua_anio + '-' if carga.dua_anio else ''
                dua += carga.dua_numero if carga.dua_numero else ''
            if carga.multiple_dua:
                dua = ''
                for duas in carga.duas_ids:
                    if dua:
                        dua += ' / '
                        dua += duas.dua_aduana + '-' + duas.dua_anio + '-' + duas.dua_numero
                    else:
                        dua += duas.dua_aduana + '-' + duas.dua_anio + '-' + duas.dua_numero
        else:
            dua = ' '
        return dua

    def get_mic(self):
        mic = self.rt_carga_id.mic_number
        return mic

    def get_crt(self):
        crt = self.rt_carga_id.crt_number
        return crt

    @api.multi
    def generar_oc(self):
        if self.supplier_ids:
            linea = self.supplier_ids
            linea.generar_oc()
        if not self.supplier_ids:
            raise Warning('¡Debe genrar el costo primero!')


    @api.multi
    def add_supplier_to_product_line(self):
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
        cost_obj = self.env['rt.service.product.supplier']

        for rec in self:
            if not rec.supplier_id:
                raise Warning('el servicio ' + rec.product_id.name + ' de la linea de prodcuto ' + rec.name + ' de la carpeta ' + str(rec.rt_service_id.name) + ' de id ' + str(rec.rt_service_id.id) + ' no tiene proveedor ')

            line_dict = {}
            line_dict['ref'] = self.rt_service_id.name
            line_dict['supplier_id'] = rec.supplier_id.id
            line_dict['currency_id'] = rec.valor_compra_currency_id.id
            line_dict['amount'] = rec.valor_compra
            # line_dict['price_subtotal'] = float(rec.valor_compra * float('1.' + str(int(taxes.amount))))
            line_dict['price_subtotal'] = float(rec.valor_compra * (1 + (taxes.amount / 100)))
            line_dict['rt_service_id'] = self.rt_service_id.id
            line_dict['rt_service_product_id'] = self.id
            line_dict['service_state'] = rec.rt_carga_id.rt_service_id.state
            line_dict['tax_ids'] = [(6, 0, taxes.ids)]
            line_dict['service_date'] = rec.start
            line_dict['tack_id'] = self.get_tack_id()
            line_dict['dua'] = self.get_dua()
            line_dict['mic'] = self.get_mic()
            line_dict['crt'] = self.get_crt()
            line_dict['origin_id'] = self.origin_id.id
            line_dict['destiny_id'] = self.destiny_id.id
            line_dict['product_id'] = self.product_id.id
            line_dict['output_reference'] = self.name
            line_dict['partner_invoice_id'] = self.partner_invoice_id.id
            result = cost_obj.create(line_dict)



rt_service_productos()
