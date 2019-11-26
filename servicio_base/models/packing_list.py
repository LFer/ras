# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api

class PackingListCarga(models.Model):
    _name = 'rt.service.packing.list.carga'
    _description = "Packing List Factura"

    rt_carga_id = fields.Many2one(comodel_name='rt.service.carga', string='Carga', ondelete="cascade")
    package = fields.Integer(string='Bultos')
    load_presentation = fields.Many2one(comodel_name='catalogo.tipo.bulto', string=u'Tipo de bultos')
    net_kg = fields.Float(string='Kg Neto')
    raw_kg = fields.Float(string='Kg Bruto')
    volume = fields.Float(string='Volumen')
    attachment = fields.Many2many(comodel_name='ir.attachment', relation='pl_carga_attach_fac', column1='pl_id', column2='att_id', string="Attendees")

    @api.onchange('raw_kg')
    def onchange_raw_kg(self):
        if self.raw_kg:
            self.rt_carga_id.raw_kg += self.raw_kg
