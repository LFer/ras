# -*- coding: utf-8 -*-

from odoo import models, fields, api



class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_box = fields.Boolean(string='Es Caja')
    box_id = fields.Many2one(comodel_name='product.template', string='Link caja')
    product_template_box_ids = fields.One2many('product.template', 'box_id', 'Cajas')

    is_pallet = fields.Boolean(string='Es Pallet')

    pallet_id = fields.Many2one(comodel_name='product.template', string='Link Pallet')
    product_template_pallet_ids = fields.One2many('product.template', 'pallet_id', 'Pallets')