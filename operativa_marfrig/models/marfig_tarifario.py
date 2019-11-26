# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details

from odoo import api, fields, models

class ProductPricelist(models.Model):
     _inherit = "product.pricelist"

     es_marfrig = fields.Boolean(related='partner_id.es_marfrig')

class ProductPricelistItem(models.Model):
     _inherit = "product.pricelist.item"

     planta_id = fields.Many2one(comodel_name='res.partner', string='Planta')
     es_marfrig = fields.Boolean(related='partner_id.es_marfrig')


