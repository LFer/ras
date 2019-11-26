# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api
from odoo.http import request
from lxml import etree
from odoo.osv.orm import setup_modifiers

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_tire = fields.Boolean(string='Is Tire')
    state = fields.Selection([('draft','No Asignada'),('in_use', 'En uso'), ('in_repair', 'En reparación'), ('retired', 'Retirada')], string='Estado', index=True, track_visibility='always', copy=False, default='draft')
    tire_condition = fields.Selection([('new', 'Nueva'), ('reparada','Reparada'), ('recauchutada', 'Recauchutada')], required=True, string='Condición', track_visibility='always', default='new')

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        result = super(ProductTemplate, self).fields_view_get(view_id, view_type, toolbar=toolbar, submenu=submenu)
        doc = etree.XML(result['arch'])
        if 'is_tire' in self._context:
            if doc.xpath("//field[@name='sale_ok']"):
                node = doc.xpath("//field[@name='sale_ok']")[0]
                node1 = doc.xpath("//label[@for='sale_ok']")[0]
                node1.set('invisible', '1')
                node.set('invisible', '1')
                setup_modifiers(node, result['fields']['sale_ok'])
                setup_modifiers(node1, result['fields']['sale_ok'])

            if doc.xpath("//field[@name='list_price']"):
                node4 = doc.xpath("//field[@name='list_price']")[0]
                node4.set('invisible', '1')
                setup_modifiers(node4, result['fields']['list_price'])

            if doc.xpath("//field[@name='taxes_id']"):
                node4 = doc.xpath("//field[@name='taxes_id']")[0]
                node4.set('invisible', '1')
                setup_modifiers(node4, result['fields']['taxes_id'])



            if doc.xpath("//field[@name='purchase_ok']"):
                node = doc.xpath("//field[@name='purchase_ok']")[0]
                node1 = doc.xpath("//label[@for='purchase_ok']")[0]
                node1.set('invisible', '1')
                node.set('invisible', '1')
                setup_modifiers(node, result['fields']['sale_ok'])
                setup_modifiers(node1, result['fields']['sale_ok'])

            if doc.xpath("//page[@name='sales']"):
                node2 = doc.xpath("//page[@name='sales']")[0]
                node2.attrib['readonly'] = '1'
                node2.attrib['invisible'] = '1'
                setup_modifiers(node2, {})

            if doc.xpath("//button[@name='action_view_sales']"):
                node3 = doc.xpath("//button[@name='action_view_sales']")[0]
                node3.attrib['readonly'] = '1'
                node3.attrib['invisible'] = '1'
                setup_modifiers(node3, {})

            result['arch'] = etree.tostring(doc, encoding='unicode')
        else:
            return result

        return result
