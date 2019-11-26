# -*- coding: utf-8 -*-
{
    'name': "Jerarquia de Productos",

    'summary': """
        Jerarquia de productos
        """,

    'description': """
        Genera una jerarquia de productos en Pallets y Cajas
    """,

    'author': "Proyecta",
    'website': "http://www.proyectasoft.odoo.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'stock', 'product'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/pallet_view.xml',
        'views/views.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}