# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class DefaultExpenses(models.Model):
    _name = "default.expenses"
    _description = "Default expenses"
    _rec_name = 'product_id'

    product_id = fields.Many2one('product.product', 'Producto', ondelete="cascade")
    product_qty = fields.Float('Cantidad', default=1)
    partner_parent_id = fields.Many2one('res.partner', 'Empresa', ondelete="cascade")
    product_parent_id = fields.Many2one('product.template', 'Producto Padre', ondelete="cascade")
    vehicle_parent_id = fields.Many2one('fleet.vehicle', 'Vehículo', ondelete="cascade")
    is_outgoing = fields.Boolean(u'¿Es gasto?')
    pricelist_item_parent_id = fields.Many2one(comodel_name='product.pricelist.item', string='Linea Tarifario', ondelete='cascade')
    pricelist_parent_id = fields.Many2one(comodel_name='product.pricelist', string='Linea Tarifario', ondelete='cascade')
    sale_price = fields.Float(string='Precio de Venta')
    cost_price = fields.Float(string='Precio de Compra')
    currency_id = fields.Many2one(comodel_name='res.currency', string='Moneda')
    invoiceable = fields.Boolean(u'¿Es Facturable?')
    action_type_id = fields.Many2one('tipo.accion', string="Tipo de Acción")
    comision = fields.Float(string='Comisión')

    _sql_constraints = [
        ('check_product_qty', 'CHECK(product_qty > 0)', "¡Cantidad de producto debe ser mayor que cero!!")]
