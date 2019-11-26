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
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.exceptions import UserError


class StockQuant(models.Model):
    _inherit = "stock.quant"


    @api.model
    def force_update_reserved_quantity(self, product_id, location_id, quantity, lot_id=None, package_id=None, owner_id=None, strict=False):
        self = self.sudo()
        rounding = product_id.uom_id.rounding
        quants = self._gather(product_id, location_id, lot_id=lot_id, package_id=package_id, owner_id=owner_id, strict=strict)
        available_quantity = self._get_available_quantity(product_id, location_id, lot_id=lot_id, package_id=package_id, owner_id=owner_id, strict=strict)
        if float_compare(quantity, 0, precision_rounding=rounding) < 0 and float_compare(abs(quantity), sum(quants.mapped('reserved_quantity')), precision_rounding=rounding) > 0:
            raise UserError(_('It is not possible to unreserve more products of %s than you have in stock.') % (', '.join(quants.mapped('product_id').mapped('display_name'))))

        reserved_quants = []
        for quant in quants:
            if float_compare(quantity, 0, precision_rounding=rounding) > 0:
                #max_quantity_on_quant = quant.quantity - quant.reserved_quantity
                #if float_compare(max_quantity_on_quant, 0, precision_rounding=rounding) <= 0:
                max_quantity_on_quant = quantity
                max_quantity_on_quant = min(max_quantity_on_quant, quantity)
                quant.reserved_quantity += max_quantity_on_quant
                reserved_quants.append((quant, max_quantity_on_quant))
                quantity -= max_quantity_on_quant
                available_quantity -= max_quantity_on_quant
            else:
                max_quantity_on_quant = min(quant.reserved_quantity, abs(quantity))
                quant.reserved_quantity -= max_quantity_on_quant
                reserved_quants.append((quant, -max_quantity_on_quant))
                quantity += max_quantity_on_quant
                available_quantity += max_quantity_on_quant

            if float_is_zero(quantity, precision_rounding=rounding) or float_is_zero(available_quantity, precision_rounding=rounding):
                break
        return reserved_quants
