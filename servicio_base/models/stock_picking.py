# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models
import ipdb
from odoo import api, fields, models, _, SUPERUSER_ID
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
from odoo.exceptions import UserError
from odoo.tools import float_utils, float_compare
_logger = logging.getLogger(__name__)

class Picking(models.Model):
    _inherit = "stock.picking"


    rt_service_product_id = fields.Many2one('rt.service.productos', string='Servicio Asociado')
    rt_service_id = fields.Many2one('rt.service', string='Carpeta Asociada')

    @api.multi
    def action_done(self):
        """Changes picking state to done by processing the Stock Moves of the Picking

        Normally that happens when the button "Done" is pressed on a Picking view.
        @return: True
        """

        # TDE FIXME: remove decorator when migration the remaining
        todo_moves = self.mapped('move_lines').filtered(lambda self: self.state in ['draft', 'waiting', 'partially_available', 'assigned', 'confirmed'])
        # Check if there are ops not linked to moves yet
        for pick in self:
            date = pick.scheduled_date
            for ops in pick.move_line_ids.filtered(lambda x: not x.move_id):
                # Search move with this product
                moves = pick.move_lines.filtered(lambda x: x.product_id == ops.product_id)
                moves = sorted(moves, key=lambda m: m.quantity_done < m.product_qty, reverse=True)
                if moves:
                    ops.move_id = moves[0].id
                else:
                    new_move = self.env['stock.move'].create({
                                                    'name': _('New Move:') + ops.product_id.display_name,
                                                    'product_id': ops.product_id.id,
                                                    'product_uom_qty': ops.qty_done,
                                                    'product_uom': ops.product_uom_id.id,
                                                    'location_id': pick.location_id.id,
                                                    'location_dest_id': pick.location_dest_id.id,
                                                    'picking_id': pick.id,
                                                    'picking_type_id': pick.picking_type_id.id,
                                                   })
                    ops.move_id = new_move.id
                    new_move._action_confirm()
                    todo_moves |= new_move
                    #'qty_done': ops.qty_done})
        todo_moves._action_done()
        self.write({'date_done': date})
        return True

class StockMove(models.Model):
    _inherit = "stock.move"


    @api.onchange('product_id')
    def cambia_prod(self):
        if self.product_id:
            if self.product_id.barcode:
                self.x_studio_sku = self.product_id.barcode

    def _prepare_move_line_vals(self, quantity=None, reserved_quant=None):
        date = self.date
        self.ensure_one()
        # apply putaway
        location_dest_id = self.location_dest_id.get_putaway_strategy(self.product_id).id or self.location_dest_id.id
        vals = {
            'move_id': self.id,
            'product_id': self.product_id.id,
            'product_uom_id': self.product_uom.id,
            'location_id': self.location_id.id,
            'location_dest_id': location_dest_id,
            'picking_id': self.picking_id.id,
            'date': date,
        }
        if quantity:
            uom_quantity = self.product_id.uom_id._compute_quantity(quantity, self.product_uom, rounding_method='HALF-UP')
            uom_quantity_back_to_product_uom = self.product_uom._compute_quantity(uom_quantity, self.product_id.uom_id, rounding_method='HALF-UP')
            rounding = self.env['decimal.precision'].precision_get('Product Unit of Measure')
            if float_compare(quantity, uom_quantity_back_to_product_uom, precision_digits=rounding) == 0:
                vals = dict(vals, product_uom_qty=uom_quantity, date=date)
            else:
                vals = dict(vals, product_uom_qty=quantity, product_uom_id=self.product_id.uom_id.id, date=date)
        if reserved_quant:
            vals = dict(
                vals,
                location_id=reserved_quant.location_id.id,
                lot_id=reserved_quant.lot_id.id or False,
                package_id=reserved_quant.package_id.id or False,
                owner_id=reserved_quant.owner_id.id or False,
                date=date,
            )
        # vals[date] = date
        return vals

    def _action_done(self):
        if self.ids:
            if self[0].picking_id:
                if self[0].picking_id[0]:
                    date = self[0].picking_id[0].scheduled_date
        self.filtered(lambda move: move.state == 'draft')._action_confirm()  # MRP allows scrapping draft moves
        moves = self.exists().filtered(lambda x: x.state not in ('done', 'cancel'))
        moves_todo = self.env['stock.move']
        date = fields.Datetime.now()
        # Cancel moves where necessary ; we should do it before creating the extra moves because
        # this operation could trigger a merge of moves.
        for move in moves:
            date = move.picking_id[0].scheduled_date if self[0].picking_id else fields.Datetime.now()
            if move.quantity_done <= 0:
                if float_compare(move.product_uom_qty, 0.0, precision_rounding=move.product_uom.rounding) == 0:
                    move._action_cancel()

        # Create extra moves where necessary
        for move in moves:
            if move.state == 'cancel' or move.quantity_done <= 0:
                continue
            # extra move will not be merged in mrp
            if not move.picking_id:
                moves_todo |= move
            moves_todo |= move._create_extra_move()

        # Split moves where necessary and move quants
        for move in moves_todo:
            # To know whether we need to create a backorder or not, round to the general product's
            # decimal precision and not the product's UOM.
            rounding = self.env['decimal.precision'].precision_get('Product Unit of Measure')
            if float_compare(move.quantity_done, move.product_uom_qty, precision_digits=rounding) < 0:
                # Need to do some kind of conversion here
                qty_split = move.product_uom._compute_quantity(move.product_uom_qty - move.quantity_done, move.product_id.uom_id, rounding_method='HALF-UP')
                new_move = move._split(qty_split)
                for move_line in move.move_line_ids:
                    if move_line.product_qty and move_line.qty_done:
                        # FIXME: there will be an issue if the move was partially available
                        # By decreasing `product_qty`, we free the reservation.
                        # FIXME: if qty_done > product_qty, this could raise if nothing is in stock
                        try:
                            move_line.write({'product_uom_qty': move_line.qty_done})
                        except UserError:
                            pass
                move._unreserve_initial_demand(new_move)
        
        for mo in moves_todo.mapped('move_line_ids'):
            mo._action_done()
        # Check the consistency of the result packages; there should be an unique location across
        # the contained quants.
        for result_package in moves_todo\
                .mapped('move_line_ids.result_package_id')\
                .filtered(lambda p: p.quant_ids and len(p.quant_ids) > 1):
            if len(result_package.quant_ids.mapped('location_id')) > 1:
                raise UserError(_('You cannot move the same package content more than once in the same transfer or split the same package into two location.'))
        picking = moves_todo.mapped('picking_id')
        # moves_todo.write({'state': 'done', 'date': fields.Datetime.now()})
        moves_todo.write({'state': 'done', 'date': date})
        moves_todo.mapped('move_dest_ids')._action_assign()

        # We don't want to create back order for scrap moves
        # Replace by a kwarg in master
        if self.env.context.get('is_scrap'):
            return moves_todo

        if picking:
            for pick in picking:
                pick._create_backorder()
        return moves_todo



class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    date = fields.Datetime('Date', required=True)

    def write(self, values):
        for rec in self:
            if rec:
                if rec.picking_id:
                    values['date'] = rec[0].picking_id[0].scheduled_date

            # res = super(StockMoveLine, self).write(values)
        res = super(StockMoveLine, self).write(values)
        return res

    @api.model
    def create(self, values):
        import datetime
        datetime_str = '08/01/19 00:00:00'
        datetime_object = datetime.datetime.strptime(datetime_str, '%m/%d/%y %H:%M:%S')

        values['date'] = datetime_object
        """ We don't want the creator of the repo to be have needaction when a message_post is done. """
        return super(StockMoveLine, self.with_context(mail_create_nosubscribe=True)).create(values)
