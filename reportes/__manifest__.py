# -*- coding: utf-8 -*-
{
    'name': "Reportes Operativos",

    'summary': """
        Reportes Operativos""",

    'description': """
        Reporte para Vestas
        Reporte de Ingresos por Matricula
        Reporte de Ingresos por Cliente
    """,

    'author': "Proyecta",
    'website': "https://proyecta.odoo.com/",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Reportes',
    'version': '1.0',

    # any module necessary for this one to work correctly
    'depends': ['base', 'rating', 'portal', 'servicio_base'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/reportes_base_view.xml',
        'views/reportes_menu.xml',

        # 'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}