# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Marfrig',
    'version': '1.0',
    'category': 'Ras Transport Service',
    'author': 'Proyecta',
    'website': '',
    'summary': 'Module for Ras Transport Marfrigt',
    'description': """ Adds the Ras Transport Marfrig """,
    'depends': ['base', 'mail', 'rating', 'portal','servicio_base', 'account'],
    'data': [
        'wizard/create_invoice_wizard.xml',
        'data/operativa_marfrig_sequence.xml',
        'security/marfrig_security.xml',
        'security/ir.model.access.csv',
        'views/operativa_marfig_menu.xml',
        'views/operativa_marfig_view.xml',
        'views/operativa_marfig_template_view.xml',
        'views/tarifario_view.xml',
        'views/res_partner_view.xml',
        'views/account_invoice_view.xml',
        'views/calendario_view.xml',
        'views/marfrig_informes.xml',
        'views/service_product_suppliers_view.xml',

    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}