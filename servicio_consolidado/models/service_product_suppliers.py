# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details

from odoo import api, fields, models
from odoo.addons import decimal_precision as dp
import ipdb

# Proveedores por Product Line
class rt_service_product_supplier(models.Model):
    _inherit = 'rt.service.product.supplier'

    rt_consol_product_id = fields.Many2one(comodel_name='producto.servicio.camion', string='Producto Consolidado Asociado', ondelete='cascade')
    consol_id = fields.Many2one(comodel_name='carpeta.camion', string='Consolidado Asociado', ondelete='cascade')
