# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api
from xlwt import *
import xlwt
from io import StringIO
from ..library import formatters
import base64
from io import BytesIO
import ipdb
import locale
import time
from odoo.tools.misc import DEFAULT_SERVER_DATE_FORMAT
import itertools
from datetime import date, datetime, timedelta
import pytz

class ListadoVendedores(models.Model):
    _inherit = 'informe.comision.vendedores'

    def _get_operation_type(self):
        res = []
        operation_national = [('transit_nat', '80 - Transito Nacional'),
                              ('impo_nat', '10 - IMPO Nacional'),
                              ('expo_nat', '40 - EXPO Nacional'),
                              ('interno_plaza_nat', 'Interno Plaza Nacional'),
                              ('interno_fiscal_nat', 'Interno Fiscal Nacional')
                              ]
        operation_international = [('transit_inter_in', '80 - Transito Internacional Ingreso'),
                                   ('transit_inter_out', '80 - Transito Internacional Salida'),
                                   ('impo_inter', '10 - IMPO Internacional'),
                                   ('expo_inter', '40 - EXPO Internacional')]
        both = operation_national + operation_international
        context = self._context
        if 'default_operation_type' in context:
            if context['default_operation_type'] == 'national':
                res = operation_national
            if context['default_operation_type'] == 'international':
                res = operation_international
        else:
            return both
        return res

    def map_regimen(self):
        return dict(regimen for regimen in self._get_operation_type())

    @api.multi
    @api.depends('name', 'start', 'stop')
    def name_get(self):
        return [(rec.id, '%s - %s' % (rec.start, rec.stop)) for rec in self]

    def get_proveedor(self):
        proveedores = []
        sellers = self.env['res.partner'].search([('seller', '=', True)])
        for seller in sellers:
            clientes = self.env['res.partner'].search([('user_id', '=', seller.id)])
            list_clientes = []
            for cliente in clientes:
                lineas_tarifa = []
                tarifas = self.env['product.pricelist'].search([('partner_id', '=', cliente.id)])
                if tarifas:
                    for tarifa in tarifas:
                        for linea_tarifa in tarifa.item_ids:
                            lineas_tarifa.append((linea_tarifa.name, linea_tarifa.regimen, linea_tarifa.load_type, linea_tarifa.comision_vendedor_currency_id.name, linea_tarifa.comision_vendedor))
                else:
                    if cliente.property_product_pricelist:
                        for linea_tarifa in cliente.property_product_pricelist.item_ids:
                            lineas_tarifa.append((linea_tarifa.name, linea_tarifa.regimen, linea_tarifa.load_type, linea_tarifa.comision_vendedor_currency_id.name, linea_tarifa.comision_vendedor))
                list_clientes.append((cliente.name, lineas_tarifa))
            proveedores.append((seller.name, list_clientes))

        return proveedores

    def listado_vendedores(self):
        # Creo el 'Libro' y su 'Pagina'
        wb = Workbook(encoding='utf-8')
        info = self.get_proveedor()
        lineas = easyxf('font: name Calibri; alignment: horizontal left')
        title = easyxf('font: name Calibri, bold True; alignment: horizontal left')
        for list_proveedor in info:
            fila = 0
            ws = wb.add_sheet(list_proveedor[0], cell_overwrite_ok=True)
            ws.write_merge(fila, fila, 0, 2, 'Clientes', title)
            ws.write_merge(fila, fila, 3, 5, 'Nombre', title)
            ws.write_merge(fila, fila, 6, 7, 'Regimen', title)
            ws.write(fila, 8, 'Carga', title)
            ws.write(fila, 9, 'Moneda', title)
            ws.write_merge(fila, fila, 10, 11, 'Comision', title)
            for cliente in list_proveedor[1]:
                for linea_tarifa in cliente[1]:
                    ws.write_merge(fila, fila, 0, 2, cliente[0], lineas)
                    ws.write_merge(fila, fila, 3, 5, linea_tarifa[0], lineas)
                    ws.write_merge(fila, fila, 6, 7, self.map_regimen()[linea_tarifa[1]] if linea_tarifa[1] else 'N/A', lineas)
                    ws.write(fila, 8, linea_tarifa[2], lineas)
                    ws.write(fila, 9, linea_tarifa[3], lineas)
                    ws.write_merge(fila, fila, 10, 11, linea_tarifa[4], lineas)
                    fila += 1

        fp = BytesIO()
        wb.save(fp)
        fp.seek(0)
        data = fp.read()
        fp.close()

        data_to_save = base64.encodebytes(data)
        wiz_id = self.env['descargar.hojas'].create({'archivo_nombre': 'Listado Proveedores-Clientes.xls', 'archivo_contenido': data_to_save})
        return {
            'name': "Descargar Archivo",
            'type': 'ir.actions.act_window',
            'res_model': 'descargar.hojas',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': wiz_id.id,
            'views': [(False, 'form')],
            'target': 'new',
        }