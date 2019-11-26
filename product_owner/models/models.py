# -*- coding: utf-8 -*-

from odoo import models, fields, api

class ProductTemplate(models.Model):
    _inherit = "product.template"

    partner_owner_id = fields.Many2one(comodel_name='res.partner', string='Propietario')