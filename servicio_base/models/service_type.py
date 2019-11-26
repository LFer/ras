# -*- coding: utf-8 -*-
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

class rt_service_line(models.Model):
    _name = "rt.service.line"
    _description = 'Servicios Asociados a la Carpeta'

    rt_service_id = fields.Many2one(comodel_name='rt.service', string='Carpeta Relacionada')
    vehicle_id = fields.Many2one(comodel_name='fleet.vehicle', string='Modelo', ondelete="cascade")
    qty = fields.Float(string='Cantidad')
    load_type = fields.Selection([('bulk', 'Bulk'), ('contenedor', 'Contenedor'), ('liquido_granel', u'Granel Líquido'),('solido_granel', u'Granel Solido')], string='Tipo de Carga')




