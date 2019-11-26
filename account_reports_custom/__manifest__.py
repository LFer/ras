# -*- coding: utf-8 -*-
{
    'name': "Reportes Contables Custom",

    'summary': """
        Se extiende Partenr Ledger y Due""",

    'description': """
        Se agrega numero de dgi (Serie y Numero) a los informes contables
    """,

    'author': "Proyecta",
    'website': "https://proyecta.odoo.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Customizations',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'account', 'electronic_invoice'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        # 'views/views.xml',
 #       'static/src/xml/account_reconciliation.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
