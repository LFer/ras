# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
from stdnum import iso6346
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning

class ProductImage(models.Model):
    _name = 'product.image'
    _description = 'Product Image'

    name = fields.Char('Name')
    image = fields.Binary('Image', attachment=True)
    product_tmpl_id = fields.Many2one('product.template', 'Related Product', copy=True)

class ProductTemplate(models.Model):
    _inherit = "product.template"

    bse = fields.Boolean('BSE')
    consolidado = fields.Boolean('Consolidado')
    flete = fields.Boolean('Flete')
    is_outgoing = fields.Boolean('¿Es gasto?')
    corresponde_comision = fields.Boolean(string='Corresponde Comisión')
    #Container
    is_container = fields.Boolean(string='Es Contenedor')
    container_type = fields.Many2one(comodel_name='fleet.vehicle', string='Tipo de Contenedor')
    container_number = fields.Char(string=u'Número de contenedor', size=32)
    invalid_cointaner_number_text = fields.Boolean(help='Este booleano es para que se muestre un texto si el número de container no es válido')
    valid_cointaner_number_text = fields.Boolean(help='Este booleano es para que se muestre un texto si el número de container es válido')
    product_image_ids = fields.One2many('product.image', 'product_tmpl_id', string='Images')

    @api.onchange('name')
    def check_container_number(self):
        for rec in self:
            if rec.is_container:
                #Valida existencia
                if rec.name != False:
                    #Valida largo correcto
                    if len(rec.name) != 13:
                        rec.name = False
                        return {'warning': {'title': "Error", 'message': "Se espera un número de 13 cifras ej: BMOU-123456-7"}}
                    #Valida existencia de - para poder realizar split
                    if rec.name.count('-') != 2:
                        rec.name = False
                        return {'warning': {'title': "Error", 'message': "Formato inválido, se espera BMOU-123456-7"}}
                    #letras_c,numeros_c,digitov_c = rec.name.split("-") Si es necesario utlizar para verificar otras cosas
                    string_container,numeros_container,digitov_container = rec.name.split("-")
                    if not string_container.isalpha():
                        rec.name = False
                        return {'warning': {'title': "Error", 'message': "Se espera un número de 13 cifras ej: BMOU-123456-7"}}
                    try:
                        type(int(numeros_container)) == int
                    except ValueError:
                        rec.name = False
                        return {'warning': {'title': "Error", 'message': "Se espera un número de 13 cifras ej: BMOU-123456-7"}}
                    try:
                        type(int(numeros_container)) == int
                    except ValueError:
                        rec.name = False
                        return {
                            'warning': {'title': "Error", 'message': "Se espera un número de 13 cifras ej: BMOU-123456-7"}}
                    try:
                        type(int(digitov_container)) == int
                    except ValueError:
                        rec.name = False
                        return {
                            'warning': {'title': "Error", 'message': "Se espera un número de 13 cifras ej: BMOU-123456-7"}}
                    #validar el numero con el algoritmo iso6346
                    name = rec.name.replace('-', '')
                    if not iso6346.is_valid(name):
                        rec.name = False
                        rec.valid_cointaner_number_text = False
                        rec.invalid_cointaner_number_text = True
                    else:
                        rec.valid_cointaner_number_text = True
                        rec.invalid_cointaner_number_text = False


