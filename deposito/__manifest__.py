# -*- coding: utf-8 -*-
{
    'name': "deposito",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "My Company",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'mail', 'rating', 'portal', 'servicio_base', 'account', 'stock'],

    # always loaded
    'data': [
        'data/depo_sequence.xml',
        'security/deposito_security.xml',
        'views/deposito_servicios.xml',
        'views/deposito_service_base_view.xml',
        'views/deposito_service_base_menu.xml',
        'views/service_product_suppliers_view.xml',

        # 'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}