# -*- coding: utf-8 -*-
import logging

from odoo import api, exceptions, fields, models, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning
import ipdb

_logger = logging.getLogger(__name__)

class RennerGenerarSalida(models.TransientModel):
    _name = "renner.generar.salida"
    _description = "Generar Salida de Renner"

    name = fields.Char()
    scheduled_date = fields.Datetime(string='Fecha Salida')


    def prueba(self):
        return False
    @api.multi
    def GenerarSalida(self):
        inv_obj = self.env['account.invoice']
        if not self._context.get('active_ids'):
            return {'type': 'ir.actions.act_window_close'}
        products = self.env['stock.move'].browse(self._context.get('active_ids'))
        p1 = products[0]
        #ipdb.set_trace()
        picking_obj = self.env['stock.picking']
        partner_renner = self.env['res.partner'].search([('name', '=', 'Lojas Renner Uruguay')])
        picking_type = self.sudo().env['stock.picking.type'].search([('code', '=', 'outgoing'), ('name', '=', 'Órdenes de entrega')]).id
        if not picking_type:
            picking_type = 2
        cabezal_location_id = p1.location_dest_id
        cabezal_location_dest_id = self.env['stock.location'].search([('name', '=', 'Customers'), ('usage', '=', 'customer')])


        stock_move_lines = []
        for prod in products:
            lines = {}
            lines['name'] = '/'
            lines['location_id'] = prod.location_dest_id.id
            lines['location_dest_id'] = cabezal_location_dest_id.id
            lines['date'] = prod.date
            lines['product_id'] = prod.product_id.id
            lines['product_uom_qty'] = prod.product_uom_qty
            lines['product_uom'] = prod.product_uom.id
            lines['x_studio_po'] = prod.x_studio_po
            lines['x_studio_embarque'] = prod.x_studio_embarque
            lines['x_studio_mic'] = prod.x_studio_mic
            lines['x_studio_crt'] = prod.x_studio_crt
            stock_move_lines.append((0, 0, lines))

        pick = picking_obj.create({
            'partner_id': partner_renner.id,
            'picking_type_id': picking_type,
            'location_id': cabezal_location_id.id,
            'location_dest_id': cabezal_location_dest_id.id,
            'scheduled_date': self.scheduled_date,
            'move_ids_without_package': stock_move_lines,


        })
        if self._context['view_picking']:
            return {
                'domain': [('id', 'in', pick.ids)],
                'name': 'Ordenes de Entrega',
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'stock.picking',
                'view_id': False,
                'views': [(self.env.ref('stock.vpicktree').id, 'tree'), (self.env.ref('stock.view_picking_form').id, 'form')],
                #'context': "{'search_default_picking_type_id': [active_id],'default_picking_type_id': active_id,'contact_display': 'partner_address','search_default_available': 1,}",
                'type': 'ir.actions.act_window'
            }
        else:
            return {'type': 'ir.actions.act_window_close'}


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    po = fields.Char(string='PO')
    embarque = fields.Char(string='Embarque')

    @api.multi
    def load_po(self):
        self = self.sudo()
        all_quants = self.env['stock.quant'].search([])
        product_id = []

        for quant in all_quants:
            if quant.product_id.default_code:
                quant.po = quant.product_id.default_code

        moves_embarque_519 = self.env['stock.move'].search([('x_studio_embarque', '=', '519')])
        for move in moves_embarque_519:
            product_id.append(move.product_id.default_code)
        for quant in all_quants:
            if quant.product_id.default_code in product_id:
                quant.embarque = "519"


        product_id = []
        moves_embarque_520 = self.env['stock.move'].search([('x_studio_embarque', '=', '520')])
        for move in moves_embarque_520:
            product_id.append(move.product_id.default_code)
        for quant in all_quants:
            if quant.product_id.default_code in product_id:
                quant.embarque = "520"

        product_id = []
        moves_embarque_521 = self.env['stock.move'].search([('x_studio_embarque', '=', '521')])
        for move in moves_embarque_521:
            product_id.append(move.product_id.default_code)
        for quant in all_quants:
            if quant.product_id.default_code in product_id:
                quant.embarque = "521"

        product_id = []
        moves_embarque_522 = self.env['stock.move'].search([('x_studio_embarque', '=', '522')])
        for move in moves_embarque_522:
            product_id.append(move.product_id.default_code)
        for quant in all_quants:
            if quant.product_id.default_code in product_id:
                quant.embarque = "522"

        product_id = []
        moves_embarque_523 = self.env['stock.move'].search([('x_studio_embarque', '=', '523')])
        for move in moves_embarque_523:
            product_id.append(move.product_id.default_code)
        for quant in all_quants:
            if quant.product_id.default_code in product_id:
                quant.embarque = "523"






    @api.model
    def create(self, vals):
        stock_move = self.env['stock.move'].search([('product_id','=', vals.get('product_id')), ('state', '=', 'assigned')], limit=1)
        if stock_move:
            vals['embarque'] = stock_move.x_studio_embarque
            vals['po'] = stock_move.x_studio_po
        return super(StockQuant, self).create(vals)

class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    po = fields.Char(string='PO')
    embarque = fields.Char(string='Embarque')
    mic = fields.Char('MIC')
    crt = fields.Char('CRT')


    @api.model
    def create(self,vals):
        stock_move = self.env['stock.move'].search([('product_id','=', vals.get('product_id')), ('state', '=', 'confirmed')], limit=1)
        if stock_move:
            vals['embarque'] = stock_move.x_studio_embarque
            vals['po'] = stock_move.x_studio_po
            vals['mic'] = stock_move.x_studio_crt
            vals['crt'] = stock_move.x_studio_mic

        return super(StockMoveLine, self).create(vals)
