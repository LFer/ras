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

{
    'name': 'Stock Force Availability Option',
    'version': '1.0',
    'category': 'Stock',
    'summary': """With this functionality you will be able to deliver products more than you have in stock""",
    'description': """
    * This module will bring back the button to force stock availability on pickings existing in the old odoo versions.\n
    * When you install this module a button will show in picking form view "Force Availability" if the state of picking is 'Confirmed'.\n
    * With this functionality you will be able to deliver products more than you have in stock.
""",
    'author' : u'Fennec Solutions',
    'depends': ['stock'],
    'data': ['views/stock_picking_views.xml'
	],
    'images': ['static/description/Banner.png'],
    'installable': True,
    'auto_install': False,
    'price':25,
    'currency': 'EUR',
    'license': 'OPL-1',
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
