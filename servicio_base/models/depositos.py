# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields

class Depositos(models.Model):
    _name = "depositos"
    _description = "Codificacion de Depositos"

    name = fields.Char(string='Depósito')
    codigo = fields.Char(string='Código')
    documento = fields.Char(string='Documento')
    estado = fields.Selection([('ha', 'HA'),('ce', 'CE'),('su', 'SU')], string='Estado')
    categoria = fields.Selection([('depo', 'DEPO'), ('rec', 'REC'), ('oficial', 'OFICIAL'), ('tli', 'TLI'), ('playa', 'PLAYA'), ('zfrancas', 'ZFRANCAS')], string='Categoría')
    image = fields.Binary("Image", attachment=True, help="This field holds the image used as avatar for this contact, limited to 1024x1024px", )
    country_id = fields.Many2one('res.country', string='País', ondelete='restrict')
    address_ext_ids = fields.One2many('res.partner.address.ext', 'parent_deposito_id', u'Dirección')

