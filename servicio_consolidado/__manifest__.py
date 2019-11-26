# -*- coding: utf-8 -*-
{
    'name': "Consolidados",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "My Company",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': [
        'servicio_base',
        'web',
        'rating',
        'portal',
        'base',
        'mail',

    ],

    # always loaded
    'data': [
        'views/consolidado_menu_view.xml',
        'wizard/create_invoice_wizard.xml',
        'views/consolidado_camion_view.xml',
        'security/consolidado_security.xml',
        'views/asociados_carpeta_view.xml',
        'views/account_invoice_view.xml',
        'views/consolidado_carga_view.xml',
        'views/consolidado_carga_kanban_view.xml',
        'views/consolidado_servicios.xml',
        'views/consolidado_search_views.xml',
        'views/product_view.xml',
        'views/service_product_suppliers_view.xml',
        # 'security/ir.model.access.csv',
    ],
    # only loaded in demonstration mode
    'demo': [
        # 'demo/demo.xml',
    ],
}