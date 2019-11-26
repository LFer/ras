# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = "product.template"

    is_bolivian_consol = fields.Boolean(string='Por defecto para Bolivia', help='Marque esta opcion si este producto es por defecto para las cargas de Bolivia')

