# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details

from odoo import api, fields, models

class TiposAccion(models.Model):
    _name = 'tipo.accion'
    _description = 'Tipos de Accion'

    name = fields.Char(string='Tipo de Accion', required=True)
    codigo = fields.Integer('Codigo')
    internacional = fields.Boolean()
    contenedores = fields.Boolean()
    nacional = fields.Boolean()
    carga_suelta = fields.Boolean()
    corresponde_comision = fields.Boolean(string='Corresponde Comisión')

    _sql_constraints = [
        ('unique_name', 'unique (name)', 'Ya existe un registro con ese nombre!')
    ]