import datetime

from odoo import api, fields, models
import ipdb

class ComisionVenedores(models.Model):
    _inherit = 'rt.service.productos'
    _description = 'Comision de Choferes'

    comision_paga = fields.Selection([('pago', 'Pago'),('no_pago', 'No Pago')], string='Estado', default='no_pago')
