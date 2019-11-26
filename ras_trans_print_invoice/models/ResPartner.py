# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
from odoo.osv import expression
import ipdb
from odoo.osv.expression import get_unaccent_wrapper
import re

class ResPartner(models.Model):
    _inherit = 'res.partner'

    print_output_reference = fields.Boolean('Referencia Carpeta', help="ID: referencia_de_salida")
    print_origin_destiny_grouped = fields.Boolean('Agrupar Origen y Destino', help="ID: origen_destino_agrup")
    print_cont_grouped = fields.Boolean('Containers Groups', help="ID: contenedores_agrup")
    print_product_grouped = fields.Boolean('Agrupar por Productos', help="ID: product_agrup")
    print_invoice_load = fields.Boolean('Referencia Carga', help="ID: referencia")
    print_invoice_product = fields.Boolean('Referencia Producto', help="ID: referencia")
    print_date_start = fields.Boolean('Travel Date', help="ID: fecha_viaje")
    print_ms_in_out = fields.Boolean('Nº MS', help="ID: ms_entrada and ms_salida", default=True)
    print_mic = fields.Boolean('Nº MIC', help="ID: mic")
    print_crt = fields.Boolean('Nº CRT', help="ID: crt")
    print_consignee = fields.Boolean('Consignatario', help="ID: consignatario")
    print_purchase_order = fields.Boolean('Orden de Compra', help="ID: purchase order", default=True)
    print_delivery_order = fields.Boolean('Delivery Order', help='ID: delivery_order')
    print_origin_destiny = fields.Boolean('Origen y Destino', help="ID: origen and destino", default=True)
    print_container_number = fields.Boolean('Nº de Contenedor', help="ID: numero_contenedor", default=True)
    print_container_size = fields.Boolean('Tamaño Contenedor', help="ID: tamano_contenedor", default=True)
    print_booking = fields.Boolean('Nº Booking', help="ID: booking", default=True)
    print_gex = fields.Boolean('Nº GEX', help="ID: gex", default=True)
    print_sender = fields.Boolean('Remito', help="ID: remito")
    print_dua = fields.Boolean('DUA', help="ID: dua", default=True)
    print_packages = fields.Boolean('Bultos', help="ID: bultos", default=True)
    print_kg = fields.Boolean('Kilogramos', help="ID: kg", default=True)
    print_volume = fields.Boolean('Volumen', help="ID: volumen", default=True)
    print_all_info = fields.Boolean('Imprimir 0')
    print_extra_info = fields.Boolean('Agregar Info', help="Others informations that the user need include in the invoice report.")
    show_extra_info = fields.Boolean('Preview', help="Preview Code")
    qweb_extra_info = fields.Html('Others Informations')
    doct_type = fields.Char(string='Tipo de documento', compute="get_doc_type")
    DgiParam = fields.Char(string=u'Resolución DGI')