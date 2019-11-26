# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api

class PackingListCarga(models.Model):
    _name = 'consolidado.packing.list.carga'
    _description = "Packing List Factura"

    rt_carga_id = fields.Many2one('carga.camion', string='Carga')
    package = fields.Integer(string='Bultos')
    load_presentation = fields.Many2one(comodel_name='catalogo.tipo.bulto', string=u'Tipo de bultos')
    net_kg = fields.Float(string='Kg Neto')
    raw_kg = fields.Float(string='Kg Bruto')
    volume = fields.Float(string='Volumen')
    attachment = fields.Many2many('ir.attachment')