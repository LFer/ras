# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Ras Transport MIC Report',
    'version': '1.0',
    'category': 'Ras Transport Service',
    'author': 'Feposoft',
    'website': '',
    'summary': 'Module for Ras Transport MIC Report',
    'description': """ Adds the Ras Transport MIC Report """,
    'depends': ['base', 'servicio_base'],
    'data': [
        'views/service_view.xml',
        'report/mic_report.xml',
        'report/mic_report_templates.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}