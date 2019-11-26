# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Ras Transport CRT Report',
    'version': '1.0',
    'category': 'Ras Transport Service',
    'author': 'Feposoft',
    'website': '',
    'summary': 'Module for Ras Transport CRT Report',
    'description': """ Adds the Ras Transport CRT Report """,
    'depends': ['base', 'servicio_base'],
    'data': [
        'views/service_view.xml',
        'views/res_company_view.xml',
        'report/crt_report.xml',
        'report/crt_report_templates.xml',
        # 'wizard/crt_consol_wzd_view.xml'
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}