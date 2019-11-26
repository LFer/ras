# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Servicio Base',
    'version': '1.1',
    'category': u'Logística',
    'sequence': 75,
    'summary': u'Módulo base',
    'description': """
Módulo base para operativa
==========================

Esta aplicación le permite trabajar con operativas de logistica


Extiende:
---------
* Empleados y Jerarquias
* Clientes y Proveedores
    """,
    'website': 'https://www.odoo.com/page/employees',
    'images': [
    ],
    'depends': [
        'base',
        'calendar',
        'rating',
        'portal',
        'web',
        'hr',
        'account',
        'account_cancel',
        'payment',
        'mail',
        'stock',
        'fleet',
        'mail',
        'contacts',
        'digest',
    ],
    'data': [
        'security/servicio_security.xml',
        'security/ir.model.access.csv',
        'wizard/create_invoice_wizard.xml',
        'wizard/supplier_invoice_wzd.xml',
        'wizard/supplier_updatae_wzd.xml',
        'views/service_base_view.xml',
        'views/service_menu.xml',
        'data/service_sequence.xml',
        'data/service_base_cron.xml',
        'data/data_template.xml',
        'views/carga_revision_view.xml',
        'views/res_partner_view.xml',
        'views/service_base_products_2_view.xml',
        'views/service_base_products_view.xml',
        'views/account_invoice_view.xml',
        'views/account_move_view.xml',
        'views/account_tax_view.xml',
        'views/vehiculo_view.xml',
        'views/asociados_carpeta_view.xml',
        'views/filter_view.xml',
        'views/tarifario_view.xml',
        'views/search_views.xml',
        'views/flota_fleteros_view.xml',
        'views/service_product_suppliers_view.xml',
        'views/product_service_view.xml',
        'views/service_calendar_menu_view.xml',
        'views/fronteras_view.xml',
        'views/depositos_view.xml',
        'views/catalogos_bultos.xml',
        'views/codigos_contenedores_view.xml',
        'views/service_calendar_inter_menu_view.xml',
        'views/hr_employee_view.xml',
        'views/carga_view.xml',
        'views/fleet_vehicle_cost_view.xml',
        'views/comision_choferes_view.xml',
        'views/comision_vendedores_view.xml',
        'views/action_type_view.xml',
        'views/account_supplier_invoice_view.xml',
        'views/account_invoice_product_supplier.xml',
        'views/service_product_commission_view.xml',
        'views/setuptools_view.xml',
        'views/templates.xml',
        'views/service_base_template.xml',
        'views/digest_views.xml',
        'views/service_product_cost_review_view.xml',
        'views/service_corrections.xml',



    ],
    'demo': [
    ],
    'external_dependencies': {
        'python': ['openpyxl', 'qrcode']
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'qweb': ['static/src/xml/qweb.xml'],
}
