# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api

class FleetVehicle(models.Model):
    _inherit = 'fleet.vehicle'

    tires = fields.Integer('Cubiertas', size=2)
    axles_id = fields.Many2one(comodel_name='fleet.axle', string='Ejes')

    f_r_tire = fields.Many2one('product.product', 'Cubierta Derecha')
    f_l_tire = fields.Many2one('product.product', 'Cubierta Izquierda')
    r_r_tire1 = fields.Many2one('product.product', 'Cubierta Deracha')
    r_l_tire1 = fields.Many2one('product.product', 'Cubierta Izquierda')
    r_r_tire2 = fields.Many2one('product.product', 'Cubierta Derecha (Interna)')
    r_l_tire2 = fields.Many2one('product.product', 'Cubierta Izquierda (Interna)')
    m_r_tire1 = fields.Many2one('product.product', 'Cubierta Derecha')
    m_l_tire1 = fields.Many2one('product.product', 'Cubierta Izquierda')
    m_r_tire2 = fields.Many2one('product.product', 'Cubierta Derecha (Interna)')
    m_l_tire2 = fields.Many2one('product.product', 'Cubierta Izquierda (Interna)')

