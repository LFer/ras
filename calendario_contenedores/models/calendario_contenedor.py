# -*- coding: utf-8 -*-

from odoo import models, fields, api

class ServicioCalendario(models.Model):
    _inherit = "servicio.calendario"

    load_type = fields.Selection([('bulk', 'Bulk-Carga Suelta'), ('contenedor', 'Contenedor'), ('liquido_granel', u'Granel Líquido'),('solido_granel', u'Granel Solido')], string='Tipo de Carga')
