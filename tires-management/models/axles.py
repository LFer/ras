# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api

class FleetAxle(models.Model):
    _name = 'fleet.axle'
    _description = 'Ejes'

    name = fields.Char(string='Nombre')
    cantidad = fields.Integer(string='Cantidad')

#FIXME REMOVER ESTA CLASE. ESTA CREADA PARA QUE NO DE ERROR DE KEY ERROR
class consol(models.Model):
    _name = 'rt.consolidado'
    _description = 'FIX'

    name = fields.Char(string='Nombre')
