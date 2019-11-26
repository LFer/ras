# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api

class Country(models.Model):
    _inherit = 'res.country'

    codigo_pais = fields.Char(string='Código DNA')


class Fronteras(models.Model):
    _name = "fronteras"
    _description = "Aduanas"

    name = fields.Char(string='Nombre')
    codigo = fields.Char(string='Código')
    codigo_dna = fields.Char(string='Código DNA')
    image = fields.Binary("Image", attachment=True, help="This field holds the image used as avatar for this contact, limited to 1024x1024px", )
    country_id = fields.Many2one('res.country', string='País', ondelete='restrict')
    codigo_pais = fields.Char(string='Código País', related="country_id.codigo_pais")

    @api.multi
    @api.depends('name', 'codigo_dna')
    def name_get(self):
        return [(rec.id, '%s - %s' % (rec.codigo_dna, rec.name)) for rec in self]

    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        recs = self.browse()
        recs = self.search(['|', '|', ('name', operator, name), ('codigo_dna', operator, name), ('country_id', operator,name)] + args, limit=limit)
        return recs.name_get()