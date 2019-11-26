# -*- coding: utf-8 -*-
{
    'name': "stock_ws",

    'summary': """
        Interfaz con WS de Forever 21""",

    'description': """
        Creación de remito Forever 21 a partir de partir de órdenes de entrega.
    """,

    'author': "Xpartansys",
    'website': "http://www.xpartansys.com",
    'category': 'Integraciones',
    'version': '1.0',
    'depends': ['base', 'stock'],
    'data': [
        'data/data.xml',
        'security/ir.model.access.csv',
        'views/f21_stock_ws_view.xml',
    ],
}