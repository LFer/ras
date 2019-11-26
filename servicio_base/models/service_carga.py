# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import ipdb
from stdnum import iso6346
import odoo.addons.decimal_precision as dp
from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning
from lxml import etree
from dateutil.relativedelta import relativedelta
_logger = logging.getLogger(__name__)
import datetime



class MultipleDua(models.Model):
    _name = 'multiple.dua'
    _description = "Multiples DUA"

    rt_carga_id = fields.Many2one(comodel_name='rt.service.carga', string='Carga Relacioada')
    dua_aduana = fields.Char(string= 'Aduana', size=3)
    dua_anio = fields.Char(string='Año', size=4)
    dua_numero = fields.Char(string='Dua_Numero', size=6)
    regimen = fields.Selection(related='rt_carga_id.regimen', string='Regimen', readonly=False,store=True)

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
            if (rec.regimen == 'transit_inter' or rec.regimen == 'transit_nat') and int_dua not in dua_transitos:
                if int_dua in dua_importaciones:
                    dua_type = '000001 - 499999 - Importaciones'
                if int_dua in dua_exportaciones:
                    dua_type = '500000 - 699999 - Exportaciones'
                if rec.dua_numero != False:
                    rec.dua_numero = False
                    return {'warning': {'title': "Error", 'message': 'DUA inválido para el Regimen TRANSITO \n El DUA ingresado corresponde al regimen  %s' % dua_type}}
        if rec.dua_anio:
            rec.dua_anionumero = rec.dua_anio + rec.dua_numero

class rt_service_profit_carga(models.Model):
    _name = "rt.service.profit.carga"
    _description = "Profit de la Carga"

    rt_carga_id = fields.Many2one(comodel_name='rt.service.carga', string='Carga Relacioada')
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


class DocumentType(models.Model):
    _name = 'document.type'
    _description = "Tipo de Documento"

    factura_carga = fields.Char(string='Factura Carga')
    packing_listo_carga = fields.Char(string='Packing Listo Carga')

class rt_service_documents_carga(models.Model):
    _name = 'rt.service.documents.carga'
    _description = "Service Carga Documentos"

    rt_carga_id = fields.Many2one(comodel_name='rt.service.carga', string='Carga', ondelete="cascade")
    document_type_id = fields.Selection([('factura_carga', 'Factura Carga'), ('packing_listo_carga', u'Packing Listo Carga')], string='Tipo de Documento')
    attachment = fields.Many2many('ir.attachment')
    number = fields.Integer('Número')

class rt_service_carga(models.Model):
    _name = "rt.service.carga"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'rating.mixin']
    _description = "Cargas"
    _order = "seq ASC"

    @api.one
    @api.depends('profit_carga_ids')
    def compute_carga_profit(self):
        debit = sum(x.debit for x in self.profit_carga_ids)
        credit = sum(x.credit for x in self.profit_carga_ids)
        balance = credit - debit
        self.profit_carga = balance

    @api.one
    @api.depends('producto_servicio_ids.importe')
    def _compute_importe_carga(self):
        self.importe_total_carga = sum(line.importe for line in self.producto_servicio_ids if line.is_invoiced)

    state = fields.Selection([
        ('draft', 'Borrador'),
        ('ready_to_ingress', 'Lista Para Ingresar'),
        ('ingress', ' Ingresada'),
        ('wait_process', 'Proceso Pendiente'),
        ('ready', 'Realizada'),
    ], string='Status', index=True, readonly=True, default='draft',
        track_visibility='onchange', copy=False,
    )
    start_datetime = fields.Datetime(string='Fecha', index=True, copy=False)
    operation_type = fields.Selection(related='rt_service_id.operation_type', string='Tipo de Servicio', readonly=False, store=True)
    regimen = fields.Selection(related='rt_service_id.regimen', string='Regimen', store=True)
    pricelist_id = fields.Many2one('product.pricelist.item', string='Tarifa')
    partner_seller_id = fields.Many2one(comodel_name='res.partner', string='Vendedor', domain=[('seller', '=', True)])
    seller_commission_fixed_by_user = fields.Float('Commisión fijada por el usuario', size=64)
    payment_date = fields.Date(string='Fecha de Pago', copy=False, readonly=True)
    active = fields.Boolean(default=True)
    xls_name = fields.Char(string='File Name', size=128)
    gen_crt_report = fields.Boolean(string='Seleccionar')
    producto_servicio_ids = fields.One2many('rt.service.productos', 'rt_carga_id', string='Cargas', ondelete='cascade', copy=True)
    profit_carga_ids = fields.One2many('rt.service.profit.carga', 'rt_carga_id', string='Profit Carga', ondelete='cascade')#, compute='compute_load_profit')
    documents_carga_ids = fields.One2many('rt.service.documents.carga', 'rt_carga_id', string='Documentos', ondelete='cascade')
    factura_carga_ids = fields.One2many('rt.service.factura.carga', 'rt_carga_id', ondelete='cascade')
    packing_list_carga_ids = fields.One2many('rt.service.packing.list.carga', 'rt_carga_id', ondelete='cascade')
    bill_of_landing_ids = fields.One2many('rt.service.bill.of.landing.carga', 'rt_carga_id', ondelete='cascade')
    rt_service_id = fields.Many2one(comodel_name='rt.service', string='Carpeta Relacionada')
    dangers_loads = fields.Boolean(string='Carga Peligrosa')
    name = fields.Char(string='Referencia Carga')
    load_type = fields.Selection([('bulk', 'Bulk-Carga Suelta'), ('contenedor','Contenedor'), ('liquido_granel',u'Granel Líquido'), ('solido_granel', u'Granel Solido')], string='Tipo de Carga')
    load_presentation = fields.Many2one(comodel_name='catalogo.tipo.bulto', string=u'Tipo de bultos')
    pallet_type = fields.Selection([('euro', 'Europeo'), ('merco','Mercosur')], string=u'Tipo Pallet')
    company_id = fields.Many2one('res.company', string='Compañia', default=lambda self: self.env.user.company_id)
    container_type = fields.Many2one(comodel_name='fleet.vehicle', string='Tipo de Contenedor')#, domain=[('vehicle_type','=', 'container')])
    doc_count = fields.Integer(compute='_compute_attached_docs_count', string="Number of documents attached")
    purchase_order = fields.Char(string='Orden de Compra')
    gex_number = fields.Char(string='Nº de Gex')
    received_by = fields.Char(string= 'Recibido por:')
    # container_size = fields.Float('Size', readonly=True, compute="_get_container_size")
    #Cuando es Contenedor
    dua_linea = fields.Char(string='DUA')
    dua_aduana = fields.Char(string= 'Aduana', size=3)
    dua_anio = fields.Char(string='Año', size=4)
    dua_numero = fields.Char(string='Dua_Numero')
    container_size = fields.Float(u'Tamaño')
    booking = fields.Char('Booking', size=32)
    tack = fields.Char('Virada', size=32)
    cut_off_operative = fields.Datetime('Cut off Operativo')
    cut_off_documentario = fields.Datetime('Cut off Documentario')
    container_number = fields.Char(string=u'Número de contenedor', size=13)
    seal_number = fields.Char(string='Número de precinto', size=32)
    remito = fields.Char(string='Remito')
    payload = fields.Float(string='Payload')
    tare = fields.Float('Tara')
    attach_tipo_contenedor = fields.Many2many(comodel_name='ir.attachment', relation='carga_attach_tipo_contenedor', column1='carga_id', column2='attach_cont_id')
    attach_remito = fields.Many2many(comodel_name='ir.attachment', relation='carga_attach_remito', column1='carga_id', column2='attach_remito_id')
    attach_precinto = fields.Many2many(comodel_name='ir.attachment', relation='carga_attach_precinto', column1='carga_id', column2='attach_cont_id')
    #Cuando es Bulk
    volume = fields.Float(string='Volumen')
    net_kg = fields.Float(string='Kg Neto')
    raw_kg = fields.Float(string='Kg Bruto')
    package = fields.Integer(string='Bultos')
    km_recorridos = fields.Integer(string='Km Recorridos')
    # profit_carga = fields.Float(string='Profit Carga', compute='compute_carga_profit')
    profit_carga_uyu = fields.Float(string='Profit Carga UYU')
    profit_carga_usd = fields.Float(string='Profit Carga USD')
    container_kg = fields.Float(string='Peso de la carga')
    ras_is_carrier = fields.Boolean('Ras es transportista')
    imo = fields.Boolean('IMO')
    crt = fields.Boolean('CRT')
    mic = fields.Boolean('MIC')
    container_qty = fields.Integer('Cantidad de contenedores')
    precio_flete = fields.Char(string="Precio del Flete")
    precio_seguro = fields.Char(strin="Precio del Seguro")
    #Datos para el CRT
    description = fields.Text(string='Descripción')
    origen_destino = fields.Char(string='Origen-Destino')
    importe = fields.Float(string='Valor de Venta', store=True)
    costo_estimado = fields.Float(string='Costo Referencia')
    importe_currency_id = fields.Many2one(comodel_name="res.currency", string="Moneda", index=True, store=True)
    costo_estimado_currency_id = fields.Many2one(comodel_name="res.currency", string="Moneda", index=True, store=True)
    make_page_invisible = fields.Boolean(help='Este booleano es para hacer invisible la pagina si no se cargo regimen, cliente a facturar')
    valid_cointaner_number_text = fields.Boolean(help= 'Este booleano es para que se muestre un texto si el número de container es válido')
    make_presentacion_invisible = fields.Boolean(help='Esto va hacer el campo presentacion invisible')
    make_dua_invisible_or_required = fields.Boolean(help='Este campo me va ayudar hacer el dua de las cargas invisible o visible y requerido')
    make_gex_invisible_or_required = fields.Boolean(help='Este campo me va ayudar hacer el gex de las cargas invisible o visible y requerido')
    make_terminal_devolucion_invisible = fields.Boolean(help='Esto hace el campo terminal de devolucion invisible')
    make_container_number_invisible = fields.Boolean(string='Exception', default=False)
    make_factura_invisible = fields.Boolean(help='Este booleano es para hacer invisible la facutra si esta vacia', default=False)
    make_packing_list_invisible = fields.Boolean(help='Este booleano es para hacer invisible el packing list si esta vacio', default=False)
    make_bill_of_landing_invisible = fields.Boolean(help='Este booleano es para hacer invisible el bill of landing si esta vacio', default=False)
    container_number_exception = fields.Char(string=u'Nº de contenedor Excepción', size=13)
    carga_qty = fields.Integer(string='Cantidad')
    carga_m3 = fields.Float(string='m3')
    libre_devolucion = fields.Datetime(string='Libre de Devolución')
    preasignado = fields.Boolean(string='Preasignado')
    partner_id = fields.Many2one(comodel_name='res.partner', string='Dueño de la Mercadería', domain=[('customer', '=', True), ('dispatcher', '=', False)])
    comentarios = fields.Text(string='Referencia')
    partner_invoice_id = fields.Many2one(comodel_name='res.partner', string='Cliente a facturar', domain=[('customer', '=', True)])
    peso_total = fields.Float(string='Peso Total')
    search_conditions = fields.Char(string='Condiciones Busqueda', store=True)
    terminal_retreat = fields.Many2one(comodel_name='res.partner.address.ext', string='Terminal de Retiro', ondelete='restrict')
    terminal_return = fields.Many2one(comodel_name='res.partner.address.ext', string=u'Terminal de Devolución', ondelete='restrict')
    terminal_ingreso_cargado = fields.Many2one(comodel_name='res.partner.address.ext', string=u'Terminal de Ingreso Cargado', ondelete='restrict')
    aduana_origen_id = fields.Many2one('fronteras', 'Aduana Origen')
    aduana_destino_id = fields.Many2one('fronteras', 'Aduana Destino')
    invisible_in_factura_cliente = fields.Boolean(help='Este campo va a ayudar con la vista de los Documentos de la carga')
    invisible_in_packing_listo_carga = fields.Boolean(help='Este campo va a ayudar con la vista de los Documentos de la carga')
    invisible_in_transit = fields.Boolean()
    invisible_in_transit_out = fields.Boolean()
    dua_muestra = fields.Boolean()
    invalid_cointaner_number_text = fields.Boolean(help='Este booleano es para que se muestre un texto si el número de container no es válido')
    dua_anionumero = fields.Char()
    action_type_id = fields.Many2one('tipo.accion', string="Tipo de Acción")
    origin_id = fields.Many2one(comodel_name='res.partner.address.ext', string='Origen')
    destiny_id = fields.Many2one(comodel_name='res.partner.address.ext', string='Destino')
    dua_not_gex = fields.Boolean()
    gex_not_dua = fields.Boolean()
    es_plantilla = fields.Boolean(string='Es plantilla')
    mic_aduana = fields.Char(string='MIC Aduana')
    has_dua_cabezal = fields.Boolean()
    seq = fields.Char(string='Secuencia')
    search_conditions_html = fields.Html(string='Condiciones de Busqueda')
    multiple_dua = fields.Boolean(string='DUA Multiple')
    duas_ids = fields.One2many('multiple.dua', 'rt_carga_id', 'Lista de DUA')
    delivery_order = fields.Char(string='Delivery Order')
    importe_total_carga = fields.Float(string='Valor de Carga', compute="_compute_importe_carga", store=False)
    stock_in_id = fields.Many2one(comodel_name='stock.picking', string='Orden de Ingreso')
    stock_out_id = fields.Many2one(comodel_name='stock.picking', string='Orden de Salida')
    fecha_ingreso = fields.Datetime(string='Fecha Ingreso', related='stock_in_id.scheduled_date')
    recurring_next_date = fields.Datetime(string='Proxima fecha Servicio Recurrente')
    # fecha_ingreso = fields.Datetime(string='Fecha Ingreso', related='stock_in_id.date_done')
    to_renew = fields.Boolean()
    solo_lectura = fields.Boolean(string='Volver de Solo lectura')
    estado_correccion = fields.Selection([('correcion_ok', 'Correción OK'), ('correcion_solicitada', 'Correción Solicitada'),
                                     ('correcion_aprobada', 'Correción Aprobada'),
                                     ('correcion_rechazada', 'Solicitud de Correción Rechazada')],
                                    string='Estado de Correción', default='correcion_ok', track_visibility='always')
    motivo_solicitud = fields.Char(track_visibility='always')
    motivo_rechazo = fields.Char(track_visibility='always')
    attach_motivo_correccion = fields.Many2many(comodel_name='ir.attachment', relation='attach_motivo_correcion', column1='motivo_carga_id',
                                                        column2='attach_motivo_comision_id', track_visibility='always')
    attach_motivo_rechazo = fields.Many2many(comodel_name='ir.attachment', relation='attach_rechazo_correcion', column1='motivo_carga_rechazo_id',
                                                        column2='attach_motivo_rechazo_id', track_visibility='always')
    user_correction_id = fields.Many2one(comodel_name='res.users', string='Usuario Solicitante Correción',
                                   track_visibility='always')

    @api.multi
    def solicitar_correccion(self):
        for rec in self:
            rec.estado_correccion = 'correcion_solicitada'
            user_correction_id = self._context['uid']

        body = u"Motivo de solicitud: %s" % self.motivo_solicitud
        # message = self.message_post(attachment=[(self.attach_motivo_correcion_comision)])
        message = self.message_post(body=body, message_type='notification', subtype=None, parent_id=False, attachment=[(self.attach_motivo_correccion)])
        message.attachment_ids = self.attach_motivo_correccion

        message_carpeta = self.rt_service_id.message_post(body=body, message_type='notification', subtype=None, parent_id=False, attachment=[(self.attach_motivo_correccion)])
        message_carpeta.attachment_ids = self.attach_motivo_correccion

        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        base_url += '/web?#id=%s&action=950&model=%s&view_type=form&menu_id=%s' % (self.id, self._name, self._name)
        message_body = 'El usuario %s ha solicitado una corrección de una carga para el siguiente documento ' % self.env['res.users'].browse(self._context['uid']).name
        message_body += '<br/>'
        message_body += 'Motivo: %s' % self.motivo_solicitud
        message_body += '<br/>'
        message_body += "<a href='%s' > Haga click aquí para ver </a>" % base_url




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
        mail_data = {'subject': 'Solicitud de corrección de carga : ' + self.motivo_solicitud,
                     'email_from': odoobot,
                     'email_to': users_to_send,
                     'body_html': message_body,
                     'attachment_ids': [(6, 0, [att.id for att in self.attach_motivo_correccion])],
                     }
        mail_out = mail.create(mail_data)
        mail_out.send()

        return True


    @api.multi
    def aprobar_correcion(self):
        for rec in self:
            rec.estado_correccion = 'correcion_aprobada'
        body = 'Solicitud de correción aprobada'
        # message = self.message_post(attachment=[(self.attach_motivo_correcion_comision)])
        message = self.message_post(body=body, message_type='notification', subtype=None, parent_id=False)

        message_carpeta = self.rt_service_id.message_post(body=body, message_type='notification', subtype=None, parent_id=False)

        odoobot = "odoobot@example.com"
        user_to_notify = self.user_correction_id.login

        message_body = 'Su solicitud de correción de carga ha sido aprobada'
        message_body += '<br/>'


        mail = self.env['mail.mail']
        mail_data = {'subject': 'Solicitud de corrección de carga aprobada',
                     'email_from': odoobot,
                     'email_to': user_to_notify,
                     'body_html': message_body,
                     }
        mail_out = mail.create(mail_data)
        mail_out.send()
        return True

    @api.multi
    def rechazar_correcion(self):
        for rec in self:
            if not rec.motivo_rechazo:
                raise Warning('Debe ingresar un motivo de rechazo')
            rec.estado_correccion = 'correcion_rechazada'

        body = u"Motivo deñ Rechazo: %s" % self.motivo_rechazo
        message = self.message_post(body=body, message_type='notification', subtype=None, parent_id=False)

        message_carpeta = self.rt_service_id.message_post(body=body, message_type='notification', subtype=None, parent_id=False)


        return True




    @api.onchange('stock_in_id')
    def onchange_stock_in_id(self):
        if self.stock_in_id:
            self.recurring_next_date = self.stock_in_id.scheduled_date

    def send_mail(self, object=None):
        mail_pool = self.env['mail.mail']
        values = {}
        values.update({'subject': 'Servicio Generado Automaticamente'})
        # values.update({'email_to': 'lferreira@proyectasoft.com'})
        values.update({'email_to': 'pablo@rastransport.com.uy'})
        values.update({'body_html': 'Se genero automaticamente el servicio de almacenaje para la carga %s de la %s' % (object.name, object.rt_service_id.name)})
        values.update({'body': 'body'})
        values.update({'res_id': object.id})  # [optional] here is the record id, where you want to post that email after sending
        values.update({'model': 'rt.service.carga'})  # [optional] here is the object(like 'project.project')  to whose record id you want to post that email after sending
        msg_id = mail_pool.create(values)
        if msg_id:
            mail_pool.send([msg_id])


    @api.model
    def _cron_recurring_create_services(self):
        return self._recurring_create_service()

    def _prepare_service_data(self, carga=None, pricelist=None):
        almacenaje = self.env['product.product'].search([('name', '=', 'Almacenaje')])
        if pricelist:
            expense = self.env['default.expenses'].search([('pricelist_item_parent_id', '=', pricelist.id)])

        return {
            'product_type': 'propio',
            'name': '/',
            'product_id': expense.product_id.id,
            'currency_id': expense.currency_id.id,
            'importe': expense.sale_price,
            # 'action_type_id': srv.action_type_id.id,
            'partner_id': carga.partner_id.id,
            'is_invoiced': True,
            'rt_service_id': carga.rt_service_id.id,
            'rt_carga_id': carga.id,
        }

    def recurring_service(self):
        return self._recurring_create_service()

    @api.multi
    def _recurring_create_service(self):
        current_date = datetime.date.today()
        domain = [('recurring_next_date', '<=', current_date), ('to_renew', '=', True)]
        subscriptions = self.search(domain)
        if subscriptions:
            sub_data = subscriptions.read(fields=['id', 'company_id'])
            for company_id in set(data['company_id'][0] for data in sub_data):
                sub_ids = [s['id'] for s in sub_data if s['company_id'][0] == company_id]
                subs = self.with_context(company_id=company_id, force_company=company_id).browse(sub_ids)
                context_company = dict(self.env.context, company_id=company_id, force_company=company_id)
                for subscription in subs:
                    subscription = subscription[0]  # Trick to not prefetch other subscriptions, as the cache is currently invalidated at each iteration
                    service_values = subscription.with_context(lang=subscription.partner_id.lang)._prepare_service_data(subscription, subscription.pricelist_id)
                    new_service = self.env['rt.service.productos'].with_context(context_company).create(service_values)
                    self.send_mail(subscription)
                    periods = {'daily': 'days', 'weekly': 'weeks', 'monthly': 'months', 'yearly': 'years'}
                    new_date = subscription.recurring_next_date + relativedelta(**{periods[subscription.pricelist_id.recurring_rule_type]: subscription.pricelist_id.recurring_interval})
                    subscription.recurring_next_date = new_date
    @api.model
    def create(self, vals):
        fechas = []
        context = self._context.copy()
        if context is None:
            context = {}
        if not vals.get('seq', False):
            vals['seq'] = self.env['ir.sequence'].next_by_code('rt.carga.nacional') or '/'
        else:
            vals['seq'] = self.env['ir.sequence'].next_by_code('rt.carga.nacional') or '/'
        rt_service_id = context.get('default_rt_service_id')
        es_plantilla = context.get('default_es_plantilla')
        if rt_service_id and not es_plantilla:
            calendario_obj = self.env['servicio.calendario']
            calendarios = calendario_obj.search([('rt_service_id', '=', rt_service_id)])
            if calendarios:
                for calendario in calendarios:
                    if calendario.start:
                        fechas.append(calendario.start)
                if fechas:
                    fecha = max(fechas)
                    try:
                        fecha = max(fechas)
                    except Exception:
                        raise UserError("La Carpeta tiene que ser creada desde el Calendario")
                if fecha:
                    vals['start_datetime'] = fecha
            else:
                raise UserError("No se encontró una entrada de calendario vinculada a esta carpeta, cree una y vuelva a ingresar la carga")

        return super(rt_service_carga, self).create(vals)

    @api.multi
    def ingresar_carga(self):
        for rec in self:
            rec.state = 'ingress'

    @api.multi
    def carga_realizada(self):
        return

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
                if rec.aduana_origen_id.codigo_dna == '001' and rec.regimen in ('transit_nat', 'transit_inter'):
                    rec.invisible_in_transit = True

                #Transito OUT
                if rec.aduana_origen_id.codigo_dna != '001':
                    if rec.aduana_destino_id.codigo_dna == '001':
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
    def abrir_contenedor(self):
        # {'search_default_picking_type_id': [active_id], 'default_picking_type_id': active_id,
        #  'contact_display': 'partner_address', }

        picking_obj = self.env['stock.picking']
        act_window = self.env['ir.actions.act_window']
        res = act_window.for_xml_id('stock', 'stock_picking_action_picking_type')
        partner_id = self.rt_service_id.partner_invoice_id
        picking_type_id = self.env['stock.picking.type'].search([('name', '=', 'Recepciones Operativas')])
        location_dest_id = picking_type_id.default_location_dest_id.id
        vals_pick = {
            'partner_id': partner_id.id,
            'picking_type_id': picking_type_id.id,
            'location_dest_id': location_dest_id,
            'origin': self.rt_service_id.name,
            'location_id': partner_id.property_stock_supplier.id,
        }
        #res.append((0, 0, vals_pick))
        pick = picking_obj.create(vals_pick)
        pick.onchange_picking_type()

        if not res.get('domain', False) or not isinstance(res.get('domain', False), (list,)):
            res['domain'] = []
        res['domain'].append(('id', 'in', pick.ids))
        ctx = {'search_default_picking_type_id': [picking_type_id.id], 'default_picking_type_id': picking_type_id.id, 'contact_display': 'partner_address'}
        self.state = 'ingress'
        res['context'] = str(ctx)


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

    @api.onchange('gex_number')
    def onchange_gex(self):
        if self.gex_number:
            self.dua_not_gex = False
        else:
            self.dua_not_gex = True

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

    def convert_to_pesos(self, amount):
        curr_obj = self.env['res.currency']
        cot = curr_obj.search([('name', '=', 'USD')])
        return amount / cot.rate

    def convert_to_dolares(self, amount):
        curr_obj = self.env['res.currency']
        cot = curr_obj.search([('name', '=', 'USD')])
        return amount * cot.rate

    @api.multi
    def compute_load_profit(self):
        self.profit_carga_ids = False
        lineas = []
        line_dict = {}
        for srv in self.producto_servicio_ids:
            line_dict['rt_carga_id'] = self.id
            line_dict['name'] = srv.name
            line_dict['venta_usd'] = srv.profit_servicio_usd
            line_dict['venta_uyu'] = srv.profit_servicio_uyu
            line_dict['usd_currency_id'] = 2
            line_dict['uyu_currency_id'] = 46
            lineas.append((0, 0, line_dict))
        self.profit_carga_ids = lineas
        self.profit_carga_usd = sum(pro.venta_usd for pro in self.profit_carga_ids.filtered(lambda x: x.venta_usd))
        self.profit_carga_uyu = sum(pro.venta_uyu for pro in self.profit_carga_ids.filtered(lambda x: x.venta_uyu))




    @api.onchange('dua_aduana')
    def check_mes(self):
        res = {}
        domain = {}
        aduana_obj = self.env['fronteras']
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

                    self.gex_not_dua = False

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
            else:
                self.gex_not_dua = True

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
                if (rec.regimen == 'transit_inter' or rec.regimen == 'transit_nat') and int_dua not in dua_transitos:
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
            if self.dua_muestra:
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
                if (regimen == 'transit_inter' or regimen == 'transit_nat') and int_dua not in dua_transitos:
                        if int_dua in dua_importaciones:
                            dua_type = '000001 - 499999 - Importaciones'
                        if int_dua in dua_exportaciones:
                            dua_type = '500000 - 699999 - Exportaciones'
                            self.dua_numero = False
                            return {'warning': {'title': "Error", 'message': 'DUA inválido para el Regimen TRANSITO \n El DUA ingresado corresponde al regimen  %s' % dua_type}}
        if self.dua_anio:
            if not self.dua_anionumero:
                self.dua_anionumero = self.dua_anio + self.dua_numero

    @api.onchange('partner_invoice_id', 'name', 'libre_devolucion', 'load_type')
    def _onchange_partner_id(self):
        self.make_dua_invisible_or_required = self.rt_service_id.make_dua_invisible_or_required
        domain = {}
        warning = {}
        res = {}
        terminal_devolucion = []
        if self.rt_service_id.aduana_origen_id:
            self.aduana_origen_id = self.rt_service_id.aduana_origen_id.id
        if self.rt_service_id.aduana_destino_id:
            self.aduana_destino_id = self.rt_service_id.aduana_destino_id
        vehicles_obj = self.env['fleet.vehicle']
        address_obj = self.env['res.partner.address.ext']
        partner_obj = self.env['res.partner']
        contenedores = vehicles_obj.search([('vehicle_type', '=', 'container')]).ids
        playas_contenedor_vacios = address_obj.search([('address_type', '=', 'beach_empty')]).ids
        playas_contenedor_cargado = address_obj.search([('address_type', '=', 'beach_load')]).ids
        domain = {'terminal_retreat': [('id', 'in', playas_contenedor_vacios)], 'terminal_return': [('id', 'in', playas_contenedor_vacios)], 'terminal_ingreso_cargado': [('id', 'in', playas_contenedor_cargado)], 'container_type': [('id', 'in', contenedores)]}

        if warning:
            res['warning'] = warning
        if domain:
            res['domain'] = domain
        return res

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

    @api.onchange('raw_kg')
    def onchange_raw_kg(self):
        for rec in self:
            if rec.raw_kg:
                if rec.partner_invoice_id.name == 'Flavio Aleman':
                    if rec.pricelist_id:
                        rec.importe = rec.pricelist_id.sale_price * (rec.raw_kg/1000)
                if rec.partner_invoice_id.name == 'Cargill Uruguay S.A.':
                    if rec.pricelist_id:
                        rec.importe = rec.pricelist_id.sale_price * (rec.raw_kg / 1000)

    def get_km_adicionales(self, km_recorridos=False):
        km_adicionales = 0
        importe_km_adicionales = 0
        if km_recorridos:
            if km_recorridos >= 300:
                km_adicionales = abs(km_recorridos - 300)
                importe_km_adicionales = km_adicionales * .10
        return importe_km_adicionales
    
    def load_default_products(self, productos=None):
        product_lines = []
        if not productos:
            raise Warning('No se encontraron productos por defecto')
        for srv in productos:
            data_prod = {
                'product_type': 'propio',
                'name': '/',
                'product_id': srv.product_id.id,
                'currency_id': srv.currency_id.id,
                'importe': srv.sale_price,
                'action_type_id': srv.action_type_id.id,
                'partner_id': self.partner_id.id,
                'is_invoiced': True,
            }
            product_lines.append((0, 0, data_prod))
        return product_lines

    @api.multi
    @api.onchange('volume', 'raw_kg', 'package', 'aduana_origen_id', 'load_type', 'container_type', 'dangers_loads', 'km_recorridos', 'destiny_id')
    def get_pricelist_item(self):
        pricelist_item_obj = self.env['product.pricelist.item']
        pricelist_obj = self.env['product.pricelist']
        carpeta = self.rt_service_id
        partner = self.partner_id.id
        #self.partner_seller_id = carpeta.partner_invoice_id.user_id.partner_id.id
        #self.importe_currency_id = carpeta.currency_id.id
        condiciones_busqueda = [('active', '=', True)]
        menor_o_igual = '<='
        mayor_o_igual = '>='
        igual = '='
        importe_km_adicionales = 0
        condiciones_busqueda.append(('regimen', '=', self.regimen))
        partner_igual_en_tarifa_y_carga = False
        partner_pricelist_item = False
        if partner:
            #El cliente tiene el cabezal del tarifario asociado en su ficha
            #Filtro las lineas del tarifario con el many2one ID de esa tarifa
            if self.partner_id.property_product_pricelist:
                pricelist_partner_id = self.partner_id.property_product_pricelist.id
                condiciones_busqueda.append(('pricelist_id', '=', pricelist_partner_id))

            # Tiene tarifa asociada en el cliente
            # Hay casos que tenemos que buscar por el partner de la tarifa asociada al cliente
            # Si el partner asociado a la tarifa es igual al partenr de la carpeta/carga. no hacemos nada
            # if self.partner_id.id == self.partner_id.property_product_pricelist.partner_id.id:
                partner_igual_en_tarifa_y_carga = True
                pricelist_item_partner = pricelist_item_obj.search([('partner_id', '=', partner)])
                #SI es diferente, nos quedamos con el partner de asociado a la tarifa asociada al partner de la carpeta
                #Caso de uso --> Hamburg Sud es el partner_id Maersk es el partner_id de la tarifa asociada a Hamburg Sud
                #Me quedo con Maersk
            # else:
            #     partner_pricelist_item = self.partner_id.property_product_pricelist.partner_id.id
            #     partner_igual_en_tarifa_y_carga = False
            #     pricelist_item_partner = pricelist_item_obj.search([('partner_id', '=', partner_pricelist_item)])


            if pricelist_item_partner:
                if partner_igual_en_tarifa_y_carga:
                    condiciones_busqueda.append(('partner_id', '=', partner))
                if not partner_igual_en_tarifa_y_carga:
                    condiciones_busqueda.append(('partner_id', '=', partner_pricelist_item))
            else:
                # Tarifa generica
                condiciones_busqueda.append(('partner_id', '=', False))

        if self.load_type:
            if self.load_type == 'bulk':
                condiciones_busqueda.append(('load_type', '=', self.load_type))
                #Si tengo km recorridos
                if self.km_recorridos:
                    if self.km_recorridos > 300:
                        km_recorridos = 300
                    else:
                        km_recorridos = self.km_recorridos
                    condiciones_busqueda.append(('km_from', menor_o_igual, km_recorridos))
                    condiciones_busqueda.append(('km_to', mayor_o_igual, km_recorridos))

                if self.volume:
                    # condiciones_busqueda.append(('mt3_from', mayor_o_igual, self.volume))
                    # condiciones_busqueda.append(('mt3_to', menor_o_igual, self.volume))
                    condiciones_busqueda.append(('mt3_to', '<=', self.volume))

                #Por Kilos
                if self.raw_kg:
                    condiciones_busqueda.append(('kg_from', '<=', self.raw_kg))
                    condiciones_busqueda.append(('kg_to', '>=', self.raw_kg))

                if self.aduana_origen_id:
                    condiciones_busqueda.append(('aduana_origen_id', '=', self.aduana_origen_id.id))

                #Por destinos. es probable que deje de funcionar para las demas.. quiza deje solo para renner por ahora
                if self.partner_id.name == 'Lojas Renner Uruguay SA':
                    if self.origin_id:
                        condiciones_busqueda.append(('origin_dir', igual, self.origin_id.id))
                    if self.destiny_id:
                        condiciones_busqueda.append(('destiny_dir', igual, self.destiny_id.id))

                # if condiciones_busqueda:
                #     pricelist_item = pricelist_item_obj.search(condiciones_busqueda)
                #     if len(pricelist_item) > 1:
                #         return
                #         #raise Warning('Se encontró mas de una tarifa  "%s" \n Ingrese mas parametros de busqueda, kg, volumen' % [("%s" % (rec.name)) for rec in pricelist_item])
                #     if pricelist_item:
                #         self.search_conditions = condiciones_busqueda
                #         self.pricelist_id = pricelist_item.id
                #         self.importe_currency_id = pricelist_item.currency_id.id
                #         self.importe = pricelist_item.sale_price
            if self.load_type == 'contenedor':
                condiciones_busqueda.append(('load_type', '=', self.load_type))
                if self.container_type.size == 20:
                    if self.raw_kg:
                        condiciones_busqueda.append(('size_to', '=', self.container_type.size))
                        condiciones_busqueda.append(('kg_from', '<=', self.raw_kg))
                        condiciones_busqueda.append(('kg_to', '>=', self.raw_kg))
                    else:
                        condiciones_busqueda.append(('size_to', '=', self.container_type.size))
                else:
                    condiciones_busqueda.append(('size_from', '<=', self.container_type.size))
                    condiciones_busqueda.append(('size_to', '>=', self.container_type.size))
        if self.aduana_origen_id:
            condiciones_busqueda.append(('aduana_origen_id', '=', self.aduana_origen_id.id))
        if self.aduana_destino_id:
            condiciones_busqueda.append(('aduana_destino_id', '=', self.aduana_destino_id.id))
        if (self.origin_id or self.destiny_id):
            if self.origin_id:
                condiciones_busqueda_origen = condiciones_busqueda.copy()
                condiciones_busqueda_origen.append(('origin_dir', '=', self.origin_id.id))
                pricelist_item = pricelist_item_obj.search(condiciones_busqueda_origen)
                if pricelist_item:
                    condiciones_busqueda = condiciones_busqueda_origen.copy()

            if self.destiny_id:
                condiciones_busqueda_destino = condiciones_busqueda.copy()
                condiciones_busqueda_destino.append(('destiny_dir', '=', self.destiny_id.id))
                pricelist_item = pricelist_item_obj.search(condiciones_busqueda_destino)
                if pricelist_item:
                    condiciones_busqueda = condiciones_busqueda_destino.copy()
        if condiciones_busqueda:
            pricelist_item = pricelist_item_obj.search(condiciones_busqueda)
            if len(pricelist_item) > 1:
                aux = max([x.sale_price for x in pricelist_item])
                for pl in pricelist_item:
                    if pl.sale_price == aux:
                        pricelist_item = pl
            if pricelist_item:
                #Si tiene productos asociados, los cargo
                #Va a sobrescribir los que ya estan creados.. #FIXME ojo con esto
                #if pricelist_item.expenses_ids:
                    #self.producto_servicio_ids = self.load_default_products(pricelist_item.expenses_ids)
                self.search_conditions = condiciones_busqueda
                self.search_conditions_html = condiciones_busqueda
                self.pricelist_id = pricelist_item.id
                self.importe_currency_id = pricelist_item.currency_id.id
                if self.partner_invoice_id.name == 'Cargill Uruguay S.A.':
                    #Para los km adicionales
                    if self.km_recorridos > 300:
                        importe_km_adicionales = self.get_km_adicionales(km_recorridos=self.km_recorridos)
                    self.importe = self.pricelist_id.sale_price * (self.raw_kg / 1000) + importe_km_adicionales
                else:
                    self.importe = pricelist_item.sale_price

    @api.multi
    def get_crt_number(self):
        for rec in self:
            if rec.destiny_id.country_id.name == False or rec.origin_id.country_id.name == False:
                rec.crt_number = False
                raise Warning('Le falta el origen o el destino al servcio')
            if rec.regimen == 'impo_inter' or rec.regimen == 'expo_inter':
                rec.crt_number = 'UY'
                if rec.destiny_id.country_id.name == 'Argentina':
                    rec.crt_number += '1448'
                    anio = str(datetime.datetime.today().year)
                    rec.crt_number += anio[2:4]
                    sequence_crt_argentina = self.env['ir.sequence'].next_by_code('rt.service.crt.argentina')
                    rec.crt_number += sequence_crt_argentina
                if rec.destiny_id.country_id.name == 'Paraguay':
                    rec.crt_number += '1476'
                    anio = str(datetime.datetime.today().year)
                    rec.crt_number += anio[2:4]
                    sequence_crt_paraguay = self.env['ir.sequence'].next_by_code('rt.service.crt.paraguay')
                    rec.crt_number += sequence_crt_paraguay
                if rec.destiny_id.country_id.name == 'Brasil':
                    rec.crt_number += '1554'
                    anio = str(datetime.datetime.today().year)
                    rec.crt_number += anio[2:4]
                    sequence_crt_brasil = self.env['ir.sequence'].next_by_code('rt.service.crt.brasil')
                    rec.crt_number += sequence_crt_brasil
        return

    @api.multi
    def get_mic_number(self):
        for rec in self:
            if rec.destiny_id.country_id.name == False or rec.origin_id.country_id.name == False:
                rec.mic_number = False
                raise Warning('Le falta el origen o el destino al servcio')
            if rec.regimen == 'impo_inter' or rec.regimen == 'expo_inter':
                rec.mic_number = 'UY'
                if rec.destiny_id.country_id.name == 'Argentina':
                    rec.mic_number += '1448'
                    anio = str(datetime.datetime.today().year)
                    rec.mic_number += anio[2:4]
                    sequence_mic_argentina = self.env['ir.sequence'].next_by_code('rt.service.mic.argentina')
                    rec.mic_number += sequence_mic_argentina
                if rec.destiny_id.country_id.name == 'Paraguay':
                    rec.mic_number += '1476'
                    anio = str(datetime.datetime.today().year)
                    rec.mic_number += anio[2:4]
                    sequence_mic_paraguay = self.env['ir.sequence'].next_by_code('rt.service.mic.paraguay')
                    rec.mic_number += sequence_mic_paraguay
                if rec.destiny_id.country_id.name == 'Brasil':
                    rec.mic_number += '1554'
                    anio = str(datetime.datetime.today().year)
                    rec.mic_number += anio[2:4]
                    sequence_mic_brasil = self.env['ir.sequence'].next_by_code('rt.service.mic.brasil')
                    rec.mic_number += sequence_mic_brasil
        return


    @api.multi
    @api.onchange('load_type', 'dua_aduana')
    def get_container_size(self):
        res = {}
        aduana_obj = self.env['fronteras']
        domain = {}
        warning = {}
        address_obj = self.env['res.partner.address.ext']
        partner_id = self.partner_id.id
        carpeta = self.rt_service_id
        self.make_dua_invisible_or_required = carpeta.make_dua_invisible_or_required
        self.has_dua_cabezal = carpeta.has_dua_cabezal
        for rec in self:
            if rec.container_type:
                rec.container_size = rec.container_type.size
            if rec.container_type.license_plate in ('20OT', '20FR', '40FR-HC', '40FR', '40OT', '40OT-HC'):
                warning = {
                    'title': ('¡Alerta!'),
                    'message': ('¿Tiene sobremedidas?'),
                }
            if rec.regimen in ('impo_nat', 'impo_inter'):
                if rec.load_type == 'bulk':
                    if rec.multiple_dua:
                        for line in rec.duas_ids:
                            dua_aduana = line.dua_aduana
                    else:
                        dua_aduana = rec.dua_aduana
                    aduana = aduana_obj.search([('codigo_dna', '=', dua_aduana), ('country_id', '=', 234)])
                    if len(aduana) == 1:
                        origenes = address_obj.search([('address_type', '=', 'load'), ('aduana_id', '=', aduana.id)]).ids
                    else:
                        origenes = address_obj.search([('address_type', '=', 'load'), ('aduana_id', 'in', aduana.ids)]).ids
                    destinos = address_obj.search([('partner_id', '=', partner_id)]).ids
                    domain = {'origin_id': [('id', 'in', origenes)], 'destiny_id': [('id', 'in', destinos)]}
                if rec.load_type == 'contenedor':
                    origenes = address_obj.search([]).ids
                    destinos = address_obj.search([]).ids
                    domain = {'origin_id': [('id', 'in', origenes)], 'destiny_id': [('id', 'in', destinos)]}

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

rt_service_carga()
