# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields

class CodigosContenedores(models.Model):
    _name = "codigos.contenedores"
    _description = "Código de contenedores"

    name = fields.Char(string='Descipcion')
    codigo = fields.Char(string='Código Tamaño')
    image = fields.Binary("Image", attachment=True, help="This field holds the image used as avatar for this contact, limited to 1024x1024px", )
    teu = fields.Float(string='TEU')
