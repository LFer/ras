# -*- encoding: utf-8 -*-
##############################################################################
#                                                                            #
#  OpenERP, Open Source Management Solution.                                 #
#                                                                            #
#  @author @author Daikhi Oualid <daikhioualid@gmail.com>                    #
#                                                                            #
#  This program is free software: you can redistribute it and/or modify      #
#  it under the terms of the GNU Affero General Public License as            #
#  published by the Free Software Foundation, either version 3 of the        #
#  License, or (at your option) any later version.                           #
#                                                                            #
#  This program is distributed in the hope that it will be useful,           #
#  but WITHOUT ANY WARRANTY; without even the implied warranty of            #
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the              #
#  GNU Affero General Public License for more details.                       #
#                                                                            #
#  You should have received a copy of the GNU Affero General Public License  #
#  along with this program. If not, see <http://www.gnu.org/licenses/>.      #
#                                                                            #
##############################################################################

from odoo import models, api, fields, _
from itertools import groupby
from operator import itemgetter
from odoo.exceptions import UserError
import odoo.addons.decimal_precision as dp

class StockMove(models.Model):
    _inherit = "stock.move"


    product_uom_qty = fields.Float(
        'Initial Demand',
        digits=dp.get_precision('Product Unit of Measure'),
        default=1, required=True, states={'done': [('readonly', True)]},
        help="This is the quantity of products from an inventory "
             "point of view. For moves in the state 'done', this is the "
             "quantity of products that were actually moved. For other "
             "moves, this is the quantity of product that is planned to "
             "be moved. Lowering this quantity does not generate a "
             "backorder. Changing this quantity on assigned moves affects "
             "the product reservation, and should be done with care.")

    @api.multi
    def _extra_force_assign(self):
        """ Reserve stock moves by creating their stock move lines. A stock move is
                considered reserved once the sum of `product_qty` for all its move lines is
                equal to its `product_qty`. If it is less, the stock move is considered
                partially available.
                """
        assigned_moves = self.env['stock.move']
        #partially_available_moves = self.env['stock.move']
        for move in self.filtered(lambda m: m.state in ['confirmed', 'waiting', 'partially_available']):
            if move.location_id.usage in ('supplier', 'inventory', 'production', 'customer') \
                    or move.product_id.type == 'consu':
                # create the move line(s) but do not impact quants
                if move.product_id.tracking == 'serial' and (
                        move.picking_type_id.use_create_lots or move.picking_type_id.use_existing_lots):
                    for i in range(0, int(move.product_qty - move.reserved_availability)):
                        self.env['stock.move.line'].create(move._prepare_move_line_vals(quantity=1))
                else:
                    to_update = move.move_line_ids.filtered(lambda ml: ml.product_uom_id == move.product_uom and
                                                                       ml.location_id == move.location_id and
                                                                       ml.location_dest_id == move.location_dest_id and
                                                                       ml.picking_id == move.picking_id and
                                                                       not ml.lot_id and
                                                                       not ml.package_id and
                                                                       not ml.owner_id)
                    if to_update:
                        to_update[0].product_uom_qty += move.product_qty - move.reserved_availability
                    else:
                        self.env['stock.move.line'].create(
                            move._prepare_move_line_vals(quantity=move.product_qty - move.reserved_availability))
                assigned_moves |= move
            else:
                if not move.move_orig_ids:
                    #if move.procure_method == 'make_to_order':
                    #    continue

                    need = move.product_qty - move.reserved_availability
                    taken_quantity = move.force_update_reserved_quantity(need, need, move.location_id,
                                                                    strict=False)
                    if need == taken_quantity:
                        assigned_moves |= move

        assigned_moves.write({'state': 'assigned'})
        self.mapped('picking_id')._check_entire_pack()



    def force_update_reserved_quantity(self, need, available_quantity, location_id, lot_id=None, package_id=None, owner_id=None, strict=True):
        """ Create or update move lines.
        """
        self.ensure_one()

        if not lot_id:
            lot_id = self.env['stock.production.lot']
        if not package_id:
            package_id = self.env['stock.quant.package']
        if not owner_id:
            owner_id = self.env['res.partner']

        taken_quantity = min(available_quantity, need)

        quants = []
        try:
            quants = self.env['stock.quant'].force_update_reserved_quantity(
                self.product_id, location_id, taken_quantity, lot_id=lot_id,
                package_id=package_id, owner_id=owner_id, strict=strict
            )
        except UserError:
            # If it raises here, it means that the `available_quantity` brought by a done move line
            # is not available on the quants itself. This could be the result of an inventory
            # adjustment that removed totally of partially `available_quantity`. When this happens, we
            # chose to do nothing. This situation could not happen on MTS move, because in this case
            # `available_quantity` is directly the quantity on the quants themselves.
            taken_quantity = 0

        # Find a candidate move line to update or create a new one.
        for reserved_quant, quantity in quants:
            to_update = self.move_line_ids.filtered(lambda m: m.location_id.id == reserved_quant.location_id.id and m.lot_id.id == reserved_quant.lot_id.id and m.package_id.id == reserved_quant.package_id.id and m.owner_id.id == reserved_quant.owner_id.id)
            if to_update:
                to_update[0].with_context(bypass_reservation_update=True).product_uom_qty += self.product_id.uom_id._compute_quantity(quantity, self.product_uom, rounding_method='HALF-UP')
            else:
                if self.product_id.tracking == 'serial':
                    for i in range(0, int(quantity)):
                        self.env['stock.move.line'].create(self._prepare_move_line_vals(quantity=1, reserved_quant=reserved_quant))
                else:
                    self.env['stock.move.line'].create(self._prepare_move_line_vals(quantity=quantity, reserved_quant=reserved_quant))
        return taken_quantity
