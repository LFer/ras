# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details

from odoo import api, fields, models
from odoo.addons import decimal_precision as dp
import ipdb

# Proveedores por Product Line
class rt_service_product_supplier(models.Model):
    _inherit = 'rt.service.product.supplier'

    rt_deposito_product_id = fields.Many2one(comodel_name='deposito.service.products', string='Producto Deposito Asociado', ondelete='cascade')
    deposito_id = fields.Many2one(comodel_name='deposito.service.base', string='Carpeta Deposito')
