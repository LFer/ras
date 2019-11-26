# -*- coding: utf-8 -*-
{
    'name': "ras_trans_print_invoice",

    'summary': """
            Invoice reports customization for Ras Transport""",
    'description': """
            Invoice reports customization for Ras Transport""",
    'author': "Proyecta",
    'website': "http://www.proyectasoft.com",

    # Categories can be used to filter modules in modules listing
    # for the full list
    'category': 'custom',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['web_enterprise', 'electronic_invoice', 'account', 'base'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/AccountInvoice_view.xml',
        # 'views/ResPartner_view.xml',
        'templates/report_invoice.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        # 'data/demo.xml',
    ],
    'license': 'OPL-1',
}
