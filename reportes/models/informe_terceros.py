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

class InformeTerceros(models.Model):
    _name = 'informe.terceros'

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

    name = fields.Char()
    start = fields.Datetime(string='Fecha Inicio', required=True, index=True, copy=False)
    stop = fields.Datetime(string='Fecha Fin', required=True, index=True, copy=False)
    tipo_informe = fields.Selection([('all', 'Todo'), ('summary', 'Resumen')], string='Tipo de Informe')
    supplier_id = fields.Many2one(comodel_name='res.partner', string='Proveedor', domain=[('supplier', '=', True)], track_visibility='always')
    make_informe_all = fields.Boolean()

    @api.multi
    @api.depends('name', 'start', 'stop')
    def name_get(self):
        return [(rec.id, '%s - %s' % (rec.start, rec.stop)) for rec in self]

    @api.onchange('supplier_id')
    def onchane_supplier_id(self):
        if self.supplier_id:
            self.make_informe_all = True
            self.tipo_informe = 'all'
        else:
            self.make_informe_all = False

    def convert_date_to_datetime(self, start, stop):
        if start and stop:
            start_datetime = datetime.combine(start, datetime.min.time()) + timedelta(hours=3)
            stop_datetime = datetime.combine(stop, datetime.min.time()) + timedelta(days=1)
            user_tz = self.env.user.tz or pytz.utc
            local = pytz.timezone(user_tz)
            # start_datetime_normalised = datetime.strftime(pytz.utc.localize(start_datetime).astimezone(local), '%Y-%m-%d %H:%M:%S')
            # stop_datetime_normalised = datetime.strftime(pytz.utc.localize(stop_datetime).astimezone(local), '%Y-%m-%d %H:%M:%S')

        return start_datetime, stop_datetime

    def get_pesos(self, condiciones_busqueda):
        facturas = self.env['account.invoice']
        pesos = self.env['res.currency'].search([('name', '=', 'UYU')]).id
        condiciones_busqueda.append(('currency_id', '=', pesos))
        facturas_pesos = facturas.search(condiciones_busqueda, order='partner_id , date_invoice')
        proveedores_pesos = self.get_informacion(facturas_pesos)

        return proveedores_pesos

    def get_dolares(self, condiciones_busqueda):
        #Si la lista viene con la condicion de busqueda para pesos, la reemplazamos por dolares
        # condiciones_busqueda.remove(('currency_id', '=', 46))
        facturas = self.env['account.invoice']
        dolares = self.env['res.currency'].search([('name', '=', 'USD')]).id
        condiciones_busqueda = list(map(lambda x: x if x != ('currency_id', '=', 46) else ('currency_id', '=', dolares), condiciones_busqueda))
        facturas_dolares = facturas.search(condiciones_busqueda, order='partner_id , date_invoice')
        proveedores_dolares = self.get_informacion(facturas_dolares)

        return proveedores_dolares

    def get_proveedor(self, start, stop):
        condiciones_busqueda = []
        condiciones_busqueda = [('date_invoice', '>=', start), ('date_invoice', '<=', stop), ('state', 'in', ('open', 'paid')), ('type', 'in', ('out_invoice', 'out_refund'))]
        facturas = self.env['account.invoice'].search(condiciones_busqueda,  order='date_invoice')
        proveedores_pesos = self.get_pesos(condiciones_busqueda)
        proveedores_dolares = self.get_dolares(condiciones_busqueda)
        proveedores = self.get_informacion(facturas)

        return proveedores, proveedores_pesos, proveedores_dolares

    def convertir_fecha(self, fecha):
        string = ''
        if fecha:
            string = fecha.strftime("%d/%m/%Y")

        return string

    def obtener_cambio(self, moneda, precio, fecha):
        tipo_cambio = self.env['res.currency.rate'].search([('name', '<=', fecha), ('currency_id', '=', 2)], limit=1)
        cambio = 0
        if moneda == 'UYU':
            cambio = precio/(tipo_cambio.rate)
        if moneda == 'USD':
            cambio = precio*(tipo_cambio.rate)

        return cambio

    def get_informacion(self, facturas):
        lineas_proveedores = []
        for factura in facturas:
            for linea_factura in factura.invoice_line_ids:
                existe = False
                info = []
                vehiculo = ''
                #Servicio Nacional/Internacional
                if linea_factura.rt_service_product_id:
                    producto = linea_factura.rt_service_product_id
                    if producto.matricula_fletero:
                        vehiculo = producto.matricula_fletero.license_plate
                        info.append(producto.operation_type)
                        info.append((producto.rt_service_id.name if producto.rt_service_id else 'N/A SERVICE') + ' - ' + (producto.rt_carga_id.seq if producto.rt_carga_id else 'N/A SERVICE'))
                        info.append(producto.name if producto.name else producto.product_id.name)
                        info.append(producto.origin_id.name if producto.origin_id else 'N/A')
                        info.append(producto.destiny_id.name if producto.destiny_id else 'N/A')
                        info.append(producto.supplier_id.name if producto.supplier_id else 'N/A')
                        info.append(producto.regimen)
                        if producto.operation_type == 'national':
                            info.append('Nacional')
                            info.append('Uruguay')
                        else:
                            if linea_factura.tramo_facturado == 'national' or 'Nacional' in linea_factura.account_id.name:
                                info.append('Tramo Nacional')
                            if linea_factura.tramo_facturado == 'international' or 'Inter' in linea_factura.account_id.name:
                                info.append('Tramo Internacional')
                            if producto.regimen in ['impo_inter', 'transit_inter_in']:
                                info.append(producto.origin_id.country_id.name if producto.origin_id else 'N/A')
                            if producto.regimen in ['expo_inter', 'transit_inter_out']:
                                info.append(producto.destiny_id.country_id.name if producto.destiny_id else 'N/A')
                #Consolidado
                if linea_factura.consolidado_service_product_id:
                    producto = linea_factura.consolidado_service_product_id
                    carga = producto.rt_carga_id if producto.rt_carga_id else ''
                    camion = producto.camion_id if producto.camion_id else producto.rt_carga_id.camion_id
                    if camion.matricula_fletero and producto.product_type == 'terceros':
                        vehiculo = camion.matricula_fletero.license_plate
                        info.append('international')
                        info.append((camion.name if camion else 'N/A CAMION') + ' - ' + (carga.name if carga.name else 'Sin nombre Carga' if carga else ''))
                        info.append(producto.name if producto.name else producto.product_id.name)
                        info.append(producto.origin_id.name if producto.origin_id else camion.aduana_origen_id.name if camion.aduana_origen_id else 'N/A')
                        info.append(producto.destiny_id.name if producto.destiny_id else camion.aduana_destino_id.name if camion.aduana_destino_id else 'N/A')
                        info.append(producto.supplier_id.name if producto.supplier_id else 'N/A')
                        info.append(producto.regimen if producto.regimen else producto.rt_carga_id.regimen if producto.rt_carga_id else camion.regimen)
                        info.append('Tramo Nacional' if linea_factura.tramo_facturado == 'national' or 'Nacional' in linea_factura.account_id.name else 'Tramo Internacional')
                        if producto.regimen in ['impo_inter', 'transit_inter_in']:
                            info.append(producto.origin_id.country_id.name if producto.origin_id else camion.aduana_origen_id.country_id.name if camion.aduana_origen_id else 'N/A')
                        if producto.regimen in ['expo_inter', 'transit_inter_out']:
                            info.append(producto.destiny_id.country_id.name if producto.destiny_id else camion.aduana_destino_id.country_id.name if camion.aduana_destino_id else 'N/A')
                #Deposito
                if linea_factura.product_deposito_srv_id:
                    producto = linea_factura.product_deposito_srv_id
                    if producto.matricula_fletero:
                        vehiculo = producto.matricula_fletero.license_plate
                        info.append('national')
                        info.append(producto.deposito_srv_id.name)
                        info.append(producto.name if producto.name else producto.product_id.name)
                        info.append(producto.origin_id.name if producto.origin_id else 'N/A')
                        info.append(producto.destiny_id.name if producto.destiny_id else 'N/A')
                        info.append(producto.supplier_id.name if producto.supplier_id else 'N/A')
                        info.append('N/A')
                        info.append('Nacional')
                        info.append('Uruguay')
                #Marfrig
                if factura.marfrig_operation_id:
                    for linea_marfrig in factura.marfrig_operation_id.mrf_srv_ids:
                        if linea_marfrig.product_id.name == linea_factura.product_id.name and linea_marfrig.is_invoiced and linea_marfrig.planta_id == factura.partner_id:
                            producto = linea_marfrig
                    if producto.matricula_fletero:
                        vehiculo = producto.matricula_fletero.license_plate
                        info.append('national')
                        info.append(producto.mrf_srv_id.name)
                        info.append(producto.name if producto.name else producto.product_id.name)
                        info.append(producto.origin_id.name if producto.origin_id else 'N/A')
                        info.append(producto.destiny_id.name if producto.destiny_id else 'N/A')
                        info.append(producto.supplier_id.name if producto.supplier_id else 'N/A')
                        info.append('expo_nat')
                        info.append('Nacional')
                        info.append('Uruguay')
                if (self.supplier_id and vehiculo and self.supplier_id.name == producto.supplier_id.name ) or (not self.supplier_id and vehiculo):
                    info.append(vehiculo)
                    info.append(factura.currency_id.name)
                    info.append((linea_factura.price_subtotal * -1) if factura.type == 'out_refund' else linea_factura.price_subtotal)
                    info.append(factura.date_invoice)
                    info.append(factura.partner_id.name)
                    info.append(str(factura.fe_DocNro) if factura.type == 'out_invoice' else 0)
                    info.append(str(factura.fe_DocNro) if factura.type == 'out_refund' else 0)
                    lineas_proveedores.append(info)

        lineas_proveedores.sort(key=lambda x: (x[5], x[8], x[7]))
        return lineas_proveedores

    def obtener_proveedor(self, proveedores):
        list_proveedores = []
        if proveedores:
            for linea_proveedor in proveedores:
                existe = False
                precio = linea_proveedor[11]
                proveedor = linea_proveedor[5]
                if list_proveedores:
                    for li in list_proveedores:
                        if li[0] == proveedor:
                            existe = True
                            li[1] += precio
                if not list_proveedores or not existe:
                    list_proveedores.append([proveedor, precio])

        list_proveedores.sort(key=lambda x: x[1], reverse=True)
        return list_proveedores

    def get_report_name(self, start=None, stop=None):
        report_name = ''
        if start and stop:
            report_name = formatters.date_fmt(start.isoformat()[:10]) + ' - ' + formatters.date_fmt(stop.isoformat()[:10])
        return report_name

    def write_page_all(self, wb=None, proveedores=None, total=None, dolares=None, fechas=None):
        fila = 4
        title = easyxf('font: name Calibri, bold True; alignment: horizontal left')
        title_number = easyxf('font: name Calibri; alignment: horizontal right',
                              num_format_str='#,##0.00;-#,##0.00;')
        lineas = easyxf('font: name Calibri; alignment: horizontal left')
        sheet_name = 'Original' + ' ' + proveedores[0][10]
        if total:
            if dolares:
                sheet_name = 'USD'
            else:
                sheet_name = 'UYU'
        ws = wb.add_sheet(sheet_name, cell_overwrite_ok=True)
        ws.write_merge(fila - 3, fila - 3, 0, 2, fechas, title)
        ws.write(fila, 0, "Fecha", title)
        ws.write_merge(fila, fila, 1, 3, "Carpeta", title)
        ws.write_merge(fila, fila, 4, 6, "Producto", title)
        ws.write_merge(fila, fila, 7, 9, "Proveedor", title)
        ws.write(fila, 10, "Matricula", title)
        ws.write_merge(fila, fila, 11, 13, "Cliente", title)
        ws.write_merge(fila, fila, 14, 15, "Regimen", title)
        ws.write_merge(fila, fila, 16, 17, "Tramo", title)
        ws.write(fila, 18, "Pais", title)
        ws.write_merge(fila, fila, 19, 21, "Origen", title)
        ws.write_merge(fila, fila, 22, 24, "Destino", title)
        ws.write(fila, 25, "Moneda", title)
        ws.write_merge(fila, fila, 26, 28, "Facturado Sin IVA", title)
        ws.write_merge(fila, fila, 29, 31, "Nº Factura", title)
        ws.write_merge(fila, fila, 32, 33, "Nota de Credito", title)
        for linea_proveedor in proveedores:
            fila += 1
            ws.write(fila, 0, self.convertir_fecha(linea_proveedor[12]), lineas)
            ws.write_merge(fila, fila, 1, 3, linea_proveedor[1], lineas)
            ws.write_merge(fila, fila, 4, 6, linea_proveedor[2], lineas)
            ws.write_merge(fila, fila, 7, 9, linea_proveedor[5], lineas)
            ws.write(fila, 10, linea_proveedor[9], lineas)
            ws.write_merge(fila, fila, 11, 13, linea_proveedor[13], lineas)
            ws.write_merge(fila, fila, 14, 15,  self.map_regimen()[linea_proveedor[6]], lineas)
            ws.write_merge(fila, fila, 16, 17, linea_proveedor[7], lineas)
            ws.write(fila, 18, linea_proveedor[8], lineas)
            ws.write_merge(fila, fila, 19, 21, linea_proveedor[3], lineas)
            ws.write_merge(fila, fila, 22, 24, linea_proveedor[4], lineas)
            ws.write(fila, 25, linea_proveedor[10], lineas)
            ws.write_merge(fila, fila, 26, 28, linea_proveedor[11], title_number)
            ws.write_merge(fila, fila, 29, 31, linea_proveedor[14], title_number)
            ws.write_merge(fila, fila, 32, 33, linea_proveedor[15], title_number)

        fila += 1
        ultima_fila = fila
        primer_fila = 6
        ws.write(ultima_fila, 26, "Total", title)
        ws.write_merge(fila, fila, 27, 28, Formula("SUM(AA%s :AA%s)" % (primer_fila, ultima_fila)), title_number)

    def write_page_per_license_plate(self, wb=None, proveedores=None, total=None, dolares=None, fechas=None):
        fila_inicio = 3
        fila_fin = 4
        numero = 1
        color = easyxf('font: name Calibri, colour white; alignment: horizontal center, vertical center; pattern: pattern solid,'
                       ' fore_colour black; borders: top_color black, bottom_color black, right_color black, left_color black,\
                              left thin, right thin, top thin, bottom thin;')
        title = easyxf('font: name Calibri, bold True, height 320, colour white; alignment: horizontal center; pattern: pattern solid,'
                       ' fore_colour black; borders: top_color black, bottom_color black, right_color black, left_color black,\
                              left thin, right thin, top thin, bottom thin;')
        title_factu = easyxf('font: name Calibri, bold True, height 240, colour white ; alignment: horizontal center; pattern: pattern solid,'
                       ' fore_colour black; borders: top_color black, bottom_color black, right_color black, left_color black,\
                              left thin, right thin, top thin, bottom thin;')
        title_hashtag = easyxf('font: name Calibri, bold True, colour orange; alignment: horizontal center; pattern: pattern solid,'
                       ' fore_colour black; borders: top_color black, bottom_color black, right_color black, left_color black,\
                              left thin, right thin, top thin, bottom thin;')
        title_number = easyxf('font: name Calibri; alignment: horizontal right; pattern: pattern solid,'
                       ' fore_colour pale_blue; borders: right_color black, top_color black, bottom_color black,\
                              right thin, top thin, bottom thin;',
                              num_format_str='#,##0.00;-#,##0.00;')
        lineas = easyxf('font: name Calibri; alignment: horizontal left; borders: right_color black, left_color black, bottom_color white,\
                              left thin, right thin, bottom thin;')
        total_precio = easyxf('font: name Calibri, bold True ; alignment: horizontal left; pattern: pattern solid,'
                       ' fore_colour pale_blue; borders: left_color black, top_color black, bottom_color black,\
                              left thin, top thin, bottom thin;')
        fin = easyxf('borders: top_color black, top thin, left thin, right thin;')
        sheet_name = 'Original' + ' ' + proveedores[0][10]
        if total:
            if dolares:
                sheet_name = 'USD'
            else:
                sheet_name = 'UYU'
        ws = wb.add_sheet(sheet_name, cell_overwrite_ok=True)
        ws.write_merge(0, 0, 0, 8, fechas, color)
        ws.write_merge(0, 0, 9, 11, '', color)
        ws.write_merge(1, 2, 0, 8, '', color)
        ws.write_merge(fila_inicio, fila_fin, 0, 0, "#", title_hashtag)
        ws.write_merge(fila_inicio, fila_fin, 1, 8, "Proveedores", title)
        if total:
            if dolares:
                ws.write_merge(1, 2, 9, 11, 'USD', title_factu)
            else:
                ws.write_merge(1, 2, 9, 11, 'UYU', title_factu)
        else:
            ws.write_merge(1, 2, 9, 11, proveedores[0][10], title_factu)
        ws.write_merge(fila_inicio, fila_fin, 9, 11, "Facturado (Sin Impuesto)", title_factu)
        proveedor = self.obtener_proveedor(proveedores)
        if proveedor:
            for info in proveedor:
                fila_fin += 1
                ws.write_merge(fila_fin, fila_fin, 0, 0, numero, color)
                ws.write_merge(fila_fin, fila_fin, 1, 8, info[0], lineas)
                ws.write_merge(fila_fin, fila_fin, 9, 11, info[1], title_number)
                numero += 1

            ultima_fila = fila_fin + 1
            primer_fila = 4
            ws.write_merge(ultima_fila, ultima_fila, 10, 11, Formula("SUM(J%s :J%s)" % (primer_fila, (fila_fin+1))), title_number)
            ws.write_merge(ultima_fila, ultima_fila, 0, 8, '', fin)
            ws.write(ultima_fila, 9, "Total", total_precio)

    def informe_terceros(self):
        # Creo el 'Libro' y su 'Pagina'
        wb = Workbook(encoding='utf-8')
        dolares = False
        total = False
        start, stop = self.convert_date_to_datetime(self.start, self.stop)
        proveedores_total, proveedores_pesos, proveedores_dolares = self.get_proveedor(start, stop)
        list_proveedores = [proveedores_pesos, proveedores_dolares, proveedores_total, proveedores_total]
        fechas = str(start)[:10] + ' / ' + str(stop)[:10]
        for proveedores in list_proveedores:
            if proveedores == proveedores_total:
                total = True
            if self.tipo_informe == 'all':
                file_name = 'Informe Terceros Todos - %s.xls' % self.get_report_name(start=self.start, stop=self.stop)
                self.write_page_all(wb, proveedores, total, dolares, fechas)
            if self.tipo_informe == 'summary':
                file_name = 'Informe Terceros Resumen - %s.xls' % self.get_report_name(start=self.start, stop=self.stop)
                self.write_page_per_license_plate(wb, proveedores, total, dolares, fechas)
            if total:
                dolares = True

        if not proveedores_total:
            if self.supplier_id:
                raise Warning('No se encontraron datos de ese Proveedor')
            else:
                raise Warning('No se encontraron Proveedores en esa Fecha')

        fp = BytesIO()
        wb.save(fp)
        fp.seek(0)
        data = fp.read()
        fp.close()

        data_to_save = base64.encodebytes(data)
        wiz_id = self.env['descargar.hojas'].create({'archivo_nombre': file_name, 'archivo_contenido': data_to_save})
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
