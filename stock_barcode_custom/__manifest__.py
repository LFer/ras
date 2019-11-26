# -*- coding: utf-8 -*-
{
    'name': "stock_barcode_custom",

    'summary': """
        Adds custom behaviour to barcode picking operations"""
,


    'description': """
        Long description of module's purpose
    """,

    'author': "Proyecta",
    'website': "http://www.proyectasoft.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Inventory',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'stock', 'stock_barcode'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/views.xml',
        # 'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        # 'demo/demo.xml',
    ],
}