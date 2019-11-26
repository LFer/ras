# -*- coding: utf-8 -*-
{
    'name': "move_rate_exchange",

    'summary': """
        Agrega tipo de cambio manual al ingreso de movimientos contables.
        """,

    'description': """
        Con este módulo usted puede agregar el tipo de cambio en forma manual al ingreso de movimientos contables.
    """,

    'author': "Xpartansys",
    'website': "http://www.xpartansys.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'account'],

    # always loaded
    'data': [
        'views/account_move.xml',
    ],
    'installable': True,
}