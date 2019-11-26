# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Lojas Rener',
    'version': '1.0',
    'category': 'Ras Transport Service',
    'author': 'Proyecta',
    'website': '',
    'summary': 'Module for Lojas Renner',
    'description': """ Adds the Ras Transport Marfrig """,
    'depends': ['base', 'mail', 'rating', 'portal','stock'],
    'data': [
        'wizard/RennerGenerarSalidaWizard.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}