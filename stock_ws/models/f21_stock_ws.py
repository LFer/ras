# -*- encoding: utf-8 -*-

from odoo import models, fields, api, _

from lxml import etree
from suds.client import Client
from suds.plugin import MessagePlugin
from odoo.exceptions import ValidationError
import datetime
import suds
import logging
import ipdb

_logger = logging.getLogger(__name__)


class LogPlugin(MessagePlugin):
    def sending(self, context):
        root = etree.fromstring(context.envelope)
        _logger.info(etree.tostring(root, pretty_print=True).decode())

    def received(self, context):
        root = etree.fromstring(context.reply)
        _logger.info(etree.tostring(root, pretty_print=True).decode())


class f21_deposito(models.Model):
    _name = 'f21.deposito'

    name = fields.Char(string=u'Descripción')
    codigo = fields.Integer(string=u'Código')
    tipo = fields.Selection(selection=[('origen','Origen'),('destino','Destino')],string=u'Tipo',default='destino')


class f21_wizard_ws_crear_remito(models.TransientModel):
    _name = 'f21.wizard.ws.crear.remito'

    picking_id = fields.Many2one(comodel_name='stock.picking',string='Remito')
    origen_id = fields.Many2one(comodel_name='f21.deposito',string='Origen')
    destino_id = fields.Many2one(comodel_name='f21.deposito',string='Destino')

    def _compute_observaciones(self):
        observacion = ''
        if self.picking_id.origin and self.picking_id.note:
            observacion = self.picking_id.origin + '\n' + self.picking_id.note

        if self.picking_id.origin and not self.picking_id.note:
            observacion = self.picking_id.origin

        if not self.picking_id.origin and self.picking_id.note:
            observacion = self.picking_id.note

        if not self.picking_id.origin and not self.picking_id.note:
            observacion = ' '

        return observacion

    def parse_fault(self, fault=None):
        error = ''
        if fault:
            if fault.fault.faultstring:
                error = fault.fault.faultstring

        return error

    def f21_ws_crear_remito(self):
        # Obtenemos la URL de los parámetros del sistema
        sys_cfg = self.env['ir.config_parameter']
        if sys_cfg.get_param('url_ws_f21'):
            url = sys_cfg.get_param('url_ws_f21')
        else:
            raise ValidationError('Es necesario configurar la url_ws_f21 en los parámetros del sistema')

        # Creamos el cliente
        client = Client(url, plugins=[LogPlugin()])

        # Datos a enviar
        empresa = 1
        cliente = "F21"
        tipo_doc = 102

        # Remito
        remito = client.factory.create('RemitoWS')
        # remito.Fecha = datetime.datetime.now()
        remito.Fecha = self.picking_id.scheduled_date
        remito.DepoOrigenID = self.origen_id.codigo
        remito.DepoDestinoID = self.destino_id.codigo
        # remito.Serie = '/'.join(self.picking_id.name.split('/')[:3])
        remito.Serie = self.picking_id.name[:11]
        remito.Numero = int(self.picking_id.name.split('/')[3:][0])
        remito.Observaciones = self._compute_observaciones()
        for linea in self.picking_id.move_ids_without_package:
            producto = linea.product_id.barcode
            cantidad = linea.quantity_done
            linea_remito = client.factory.create('LineaRemito')
            linea_remito.Articulo = producto
            linea_remito.Cantidad = cantidad
            remito.LineasRemito.LineaRemito.append(linea_remito)

        # Consumir el webservice
        try:
            result = client.service.CrearRemito(cliente, empresa, remito, tipo_doc)
        except suds.WebFault as fault:
            _logger.error(fault)
            error = self.parse_fault(fault=fault)
            raise ValidationError(error)
            # raise ValidationError('Error al enviar el Remito a Forever 21')

        # Registramos en el picking la fecha y el nro. de remito F21 cecibido
        self.picking_id.fecha_enviado = fields.Datetime.now()
        self.picking_id.nro_remito_f21 = result


class stock_picking_f21(models.Model):
    _inherit = 'stock.picking'

    def compute_es_f21(self):
        self.es_f21 = 'F21' in self.name

    fecha_enviado = fields.Datetime(string='Fecha enviado', track_visibility='onchange')
    nro_remito_f21 = fields.Integer(string='Nro. remito Forever 21')
    es_f21 = fields.Boolean(compute='compute_es_f21', store=False)

    @api.multi
    def f21_wizard_ws_crear_remito(self):
        origen_id = self.env['f21.deposito'].search([('codigo', '=', 4)]).id
        destino_id = self.env['f21.deposito'].search([('codigo', '=', 1)]).id
        wizard = self.env['f21.wizard.ws.crear.remito'].create({'picking_id': self.id, 'origen_id': origen_id, 'destino_id': destino_id})

        return {
            'type': 'ir.actions.act_window',
            'name': 'Crear Remito para Forever 21',
            'view_mode': 'form',
            'res_model': 'f21.wizard.ws.crear.remito',
            'target': 'new',
            'res_id': wizard.id,
        }
