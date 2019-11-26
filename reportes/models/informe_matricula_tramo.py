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

class ReportesMatriculaTramo(models.Model):
    _name = 'informe.matricula.tramo'

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
    vehicle_id = fields.Many2one(comodel_name='fleet.vehicle', string=u'Matrícula', domain=[('is_ras_property', '=', True)])
    make_informe_all = fields.Boolean()

    @api.multi
    @api.depends('name', 'start', 'stop')
    def name_get(self):
        return [(rec.id, '%s - %s' % (rec.start, rec.stop)) for rec in self]

    @api.onchange('vehicle_id')
    def onchane_vehicle_id(self):
        if self.vehicle_id:
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

    def get_matriculas(self, facturas):
        matriculas = []
        for factura in facturas:
            for linea_factura in factura.invoice_line_ids:
                existe = False
                info = []
                info_nat = []
                info_inter = []
                vehiculo = ''
                #Servicio Nacional/Internacional
                if linea_factura.rt_service_product_id:
                    producto = linea_factura.rt_service_product_id
                    if producto.vehicle_id:
                        vehiculo = producto.vehicle_id.license_plate
                        info.append(producto.operation_type)
                        info.append((producto.rt_service_id.name if producto.rt_service_id else 'N/A SERVICE') + ' - ' + (producto.rt_carga_id.seq if producto.rt_carga_id else 'N/A CARGA'))
                        info.append(producto.name if producto.name else producto.product_id.name)
                        info.append(producto.origin_id.name if producto.origin_id else 'N/A')
                        info.append(producto.destiny_id.name if producto.destiny_id else 'N/A')
                        info.append(producto.regimen)
                        if producto.operation_type == 'national' or linea_factura.tramo_facturado == 'national' or 'Nacional' in linea_factura.account_id.name:
                            info.append('Tramo Nacional')
                        if linea_factura.tramo_facturado == 'international' or 'Inter' in linea_factura.account_id.name:
                            info.append('Tramo Internacional')
                        if producto.operation_type == 'international':
                            if producto.regimen in ['impo_inter', 'transit_inter_in']:
                                info.append(producto.origin_id.country_id.name if producto.origin_id else 'N/A')
                            if producto.regimen in ['expo_inter', 'transit_inter_out']:
                                info.append(producto.destiny_id.country_id.name if producto.destiny_id else 'N/A')
                #Consolidado
                if linea_factura.consolidado_service_product_id:
                    producto = linea_factura.consolidado_service_product_id
                    carga = producto.rt_carga_id if producto.rt_carga_id else ''
                    camion = producto.camion_id if producto.camion_id else producto.rt_carga_id.camion_id
                    if camion.vehicle_id:
                        vehiculo = camion.vehicle_id.license_plate
                        info.append('international')
                        info.append((camion.name if camion else 'N/A CAMION') + ' - ' + (carga.name if carga.name else 'Sin nombre Carga' if carga else ''))
                        info.append(producto.name if producto.name else producto.product_id.name)
                        info.append(producto.origin_id.name if producto.origin_id else camion.aduana_origen_id.name if camion.aduana_origen_id else 'N/A')
                        info.append(producto.destiny_id.name if producto.destiny_id else camion.aduana_destino_id.name if camion.aduana_destino_id else 'N/A')
                        info.append(producto.regimen if producto.regimen else producto.rt_carga_id.regimen if producto.rt_carga_id else camion.regimen)
                        info.append('Tramo Nacional' if linea_factura.tramo_facturado == 'national' or 'Nacional' in linea_factura.account_id.name else 'Tramo Internacional')
                        if producto.regimen in ['impo_inter', 'transit_inter_in']:
                            info.append(producto.origin_id.country_id.name if producto.origin_id else camion.aduana_origen_id.country_id.name if camion.aduana_origen_id else 'N/A')
                        if producto.regimen in ['expo_inter', 'transit_inter_out']:
                            info.append(producto.destiny_id.country_id.name if producto.destiny_id else camion.aduana_destino_id.country_id.name if camion.aduana_destino_id else 'N/A')
                #Deposito
                if linea_factura.product_deposito_srv_id:
                    producto = linea_factura.product_deposito_srv_id
                    if producto.vehicle_id:
                        vehiculo = producto.vehicle_id.license_plate
                        info.append('national')
                        info.append(producto.deposito_srv_id.name)
                        info.append(producto.name if producto.name else producto.product_id.name)
                        info.append(producto.origin_id.name if producto.origin_id else 'N/A')
                        info.append(producto.destiny_id.name if producto.destiny_id else 'N/A')
                        info.append('N/A')
                        info.append('Tramo Nacional')
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
                        info.append('expo_nat')
                        info.append('Tramo Nacional')
                if (self.vehicle_id and self.vehicle_id.license_plate == vehiculo) or (not self.vehicle_id and vehiculo):
                    info.append(factura.currency_id.name)
                    info.append((linea_factura.price_subtotal * -1) if factura.type == 'out_refund' else linea_factura.price_subtotal)
                    info.append(factura.date_invoice)
                    info.append(factura.partner_id.name)
                    info.append(str(factura.fe_DocNro) if factura.type == 'out_invoice' else 0)
                    info.append(str(factura.fe_DocNro) if factura.type == 'out_refund' else 0)
                    if info[0] == 'national':
                        info_nat = info
                    if info[0] == 'international':
                        info_inter = info
                    if matriculas:
                        for matricula in matriculas:
                            if matricula[0] == vehiculo:
                                existe = True
                                if info_nat:
                                    matricula[1].append(info_nat)
                                if info_inter:
                                    matricula[2].append(info_inter)
                    if not matriculas or not existe:
                        if info_nat:
                            matriculas.append([vehiculo, [info_nat], []])
                        if info_inter:
                            matriculas.append([vehiculo, [], [info_inter]])
                    #AGREGAR MATRICULA DIC? CON SU INFO SUMARLA SI NO TIENE Y SINO CREARLE PREGUNTARLE A ELE CASO TTO TTI EN PAISES

        return matriculas

    def obtener_license_plate(self, list_matriculas):
        list_license_plate = [[], [], [], []]
        if list_matriculas:
            for matricula in list_matriculas:
                ori_pesos = 0
                ori_dolares = 0
                bool_pesos = False
                bool_dolares = False
                pesos = 0
                dolares = 0
                for matricula_nat in matricula[1]:
                    if matricula_nat[7] == 'UYU':
                        bool_pesos = True
                        ori_pesos += matricula_nat[8]
                        pesos += matricula_nat[8]
                        dolares += self.obtener_cambio(matricula_nat[7], matricula_nat[8], matricula_nat[9])
                    if matricula_nat[7] == 'USD':
                        bool_dolares = True
                        ori_dolares += matricula_nat[8]
                        pesos += self.obtener_cambio(matricula_nat[7], matricula_nat[8], matricula_nat[9])
                        dolares += matricula_nat[8]

                for matricula_inter in matricula[2]:
                    if matricula_inter[8] == 'UYU':
                        bool_pesos = True
                        ori_pesos += matricula_inter[9]
                        pesos += matricula_inter[9]
                        dolares += self.obtener_cambio(matricula_inter[8], matricula_inter[9], matricula_inter[10])
                    if matricula_inter[8] == 'USD':
                        bool_dolares = True
                        ori_dolares += matricula_inter[9]
                        pesos += self.obtener_cambio(matricula_inter[8], matricula_inter[9], matricula_inter[10])
                        dolares += matricula_inter[9]
                if bool_pesos:
                    list_license_plate[0].append([matricula[0], ori_pesos, 'ORIGINAL UYU'])
                if bool_dolares:
                    list_license_plate[1].append([matricula[0], ori_dolares, 'ORIGINAL USD'])
                list_license_plate[2].append([matricula[0], pesos, 'UYU'])
                list_license_plate[3].append([matricula[0], dolares, 'USD'])

        for lista in list_license_plate:
            lista.sort(key=lambda x: x[1], reverse=True)
        return list_license_plate

    def get_report_name(self, start=None, stop=None):
        report_name = ''
        if start and stop:
            report_name = formatters.date_fmt(start.isoformat()[:10]) + ' - ' + formatters.date_fmt(stop.isoformat()[:10])
        return report_name

    def write_page_all(self, wb=None, matricula=None, fechas=None):
        fila = 4
        if matricula[1]:
            matricula[1].sort(key=lambda x: x[7], reverse=True)
            style = easyxf('pattern: fore_colour light_blue;')
        if matricula[2]:
            matricula[2].sort(key=lambda x: x[7])
        if matricula[1] and matricula[2]:
            total = fila + len(matricula[1]) + len(matricula[2]) + 9
        else:
            total = fila + len(matricula[1]) + len(matricula[2]) + 5
        primer_total = total
        title = easyxf('font: name Calibri, bold True; alignment: horizontal left')
        title_number = easyxf('font: name Calibri; alignment: horizontal right',
                              num_format_str='#,##0.00;-#,##0.00;')
        lineas = easyxf('font: name Calibri; alignment: horizontal left')
        ws = wb.add_sheet(matricula[0], cell_overwrite_ok=True)
        ws.write_merge(fila - 3, fila - 3, 0, 2, fechas, title)
        #COLUMNAS TOTAL
        ws.write_merge(total - 1, total - 1, 0, 1, 'Total', title)
        ws.write(total, 0, "Fecha", title)
        ws.write_merge(total, total, 1, 3, "Carpeta", title)
        ws.write_merge(total, total, 4, 6, "Producto", title)
        ws.write_merge(total, total, 7, 9, "Cliente", title)
        ws.write_merge(total, total, 10, 11, "Regimen", title)
        ws.write_merge(total, total, 12, 13, "Tramo", title)
        ws.write(total, 14, "Pais", title)
        ws.write_merge(total, total, 15, 17, "Origen", title)
        ws.write_merge(total, total, 18, 20, "Destino", title)
        ws.write(total, 21, "UYU", title)
        ws.write_merge(total, total, 22, 24, "Original UYU Sin IVA", title)
        ws.write(total, 25, "USD", title)
        ws.write_merge(total, total, 26, 28, "Original USD Sin IVA", title)
        ws.write(total, 29, "UYU", title)
        ws.write_merge(total, total, 30, 32, "UYU Sin IVA", title)
        ws.write(total, 33, "USD", title)
        ws.write_merge(total, total, 34, 36, "USD Sin IVA", title)
        ws.write_merge(total, total, 37, 38, "Nº Factura", title)
        ws.write_merge(total, total, 39, 40, "Nº Nota de Credito", title)
        if matricula[1]:
            #COLUMNAS NACIONAL
            ws.write_merge(fila-1, fila-1, 0, 1, 'Nacional', title)
            ws.write(fila, 0, "Fecha", title)
            ws.write_merge(fila, fila, 1, 3, "Carpeta", title)
            ws.write_merge(fila, fila, 4, 6, "Producto", title)
            ws.write_merge(fila, fila, 7, 9, "Cliente", title)
            ws.write_merge(fila, fila, 10, 11, "Regimen", title)
            ws.write_merge(fila, fila, 12, 14, "Origen", title)
            ws.write_merge(fila, fila, 15, 17, "Destino", title)
            ws.write(fila, 18, "UYU", title)
            ws.write_merge(fila, fila, 19, 21, "UYU Sin IVA", title)
            ws.write(fila, 22, "USD", title)
            ws.write_merge(fila, fila, 23, 25, "USD Sin IVA", title)
            ws.write_merge(fila, fila, 26, 27, "Nº Factura", title)
            ws.write_merge(fila, fila, 28, 29, "Nº Nota de Credito", title)
            for linea_nat in matricula[1]:
                fila += 1
                #CAMPOS NACIONAL
                ws.write(fila, 0, self.convertir_fecha(linea_nat[9]), lineas)
                ws.write_merge(fila, fila, 1, 3, linea_nat[1], lineas)
                ws.write_merge(fila, fila, 4, 6, linea_nat[2], lineas)
                ws.write_merge(fila, fila, 7, 9, linea_nat[10], lineas)
                ws.write_merge(fila, fila, 10, 11,  self.map_regimen()[linea_nat[5]], lineas)
                ws.write_merge(fila, fila, 12, 14, linea_nat[3], lineas)
                ws.write_merge(fila, fila, 15, 17, linea_nat[4], lineas)
                if linea_nat[7] == 'UYU':
                    ws.write(fila, 18, linea_nat[7], lineas)
                    ws.write_merge(fila, fila, 19, 21, linea_nat[8], title_number)
                    ws.write(fila, 22, '', lineas)
                    ws.write_merge(fila, fila, 23, 25, '', title_number)
                if linea_nat[7] == 'USD':
                    ws.write(fila, 18, '', lineas)
                    ws.write_merge(fila, fila, 19, 21, '', title_number)
                    ws.write(fila, 22, linea_nat[7], lineas)
                    ws.write_merge(fila, fila, 23, 25, linea_nat[8], title_number)
                ws.write_merge(fila, fila, 26, 27, linea_nat[11], title_number)
                ws.write_merge(fila, fila, 28, 29, linea_nat[12], title_number)

                #CAMPOS TOTAL
                total += 1
                ws.write(total, 0, self.convertir_fecha(linea_nat[9]), lineas)
                ws.write_merge(total, total, 1, 3, linea_nat[1], lineas)
                ws.write_merge(total, total, 4, 6, linea_nat[2], lineas)
                ws.write_merge(total, total, 7, 9, linea_nat[10], lineas)
                ws.write_merge(total, total, 10, 11,  self.map_regimen()[linea_nat[5]], lineas)
                ws.write_merge(total, total, 12, 13, 'Nacional', lineas)
                ws.write(total, 14, 'Uruguay', lineas)
                ws.write_merge(total, total, 15, 17, linea_nat[3], lineas)
                ws.write_merge(total, total, 18, 20, linea_nat[4], lineas)
                if linea_nat[7] == 'UYU':
                    ws.write(total, 21, linea_nat[7], lineas)
                    ws.write_merge(total, total, 22, 24, linea_nat[8], title_number)
                    ws.write(total, 25, '', lineas)
                    ws.write_merge(total, total, 26, 28, '', title_number)
                    ws.write(total, 29, linea_nat[7], lineas)
                    ws.write_merge(total, total, 30, 32, linea_nat[8], title_number)
                    ws.write(total, 33, 'USD', lineas)
                    ws.write_merge(total, total, 34, 36, self.obtener_cambio(linea_nat[7], linea_nat[8], linea_nat[9]), title_number)
                if linea_nat[7] == 'USD':
                    ws.write(total, 21, '', lineas)
                    ws.write_merge(total, total, 22, 24, '', title_number)
                    ws.write(total, 25, linea_nat[7], lineas)
                    ws.write_merge(total, total, 26, 28, linea_nat[8], title_number)
                    ws.write(total, 29, 'UYU', lineas)
                    ws.write_merge(total, total, 30, 32, self.obtener_cambio(linea_nat[7], linea_nat[8], linea_nat[9]), title_number)
                    ws.write(total, 33, linea_nat[7], lineas)
                    ws.write_merge(total, total, 34, 36, linea_nat[8], title_number)
                ws.write_merge(total, total, 37, 38, linea_nat[11], title_number)
                ws.write_merge(total, total, 39, 40, linea_nat[12], title_number)

            fila += 1
            ultima_fila = fila
            primer_fila = 6
            ws.write(ultima_fila, 19, "Total UYU", title)
            ws.write_merge(fila, fila, 20, 21, Formula("SUM(T%s :T%s)" % (primer_fila, ultima_fila)), title_number)
            ws.write(ultima_fila, 23, "Total USD", title)
            ws.write_merge(fila, fila, 24, 25, Formula("SUM(X%s :X%s)" % (primer_fila, ultima_fila)), title_number)
            fila += 4

        if matricula[2]:
            #COLUMNAS INTERNACIONAL
            ws.write_merge(fila - 1, fila - 1, 0, 1, 'Internacional', title)
            ws.write(fila, 0, "Fecha", title)
            ws.write_merge(fila, fila, 1, 3, "Carpeta", title)
            ws.write_merge(fila, fila, 4, 6, "Producto", title)
            ws.write_merge(fila, fila, 7, 9, "Cliente", title)
            ws.write_merge(fila, fila, 10, 11, "Regimen", title)
            ws.write_merge(fila, fila, 12, 13, "Tramo", title)
            ws.write(fila, 14, "Pais", title)
            ws.write_merge(fila, fila, 15, 17, "Origen", title)
            ws.write_merge(fila, fila, 18, 20, "Destino", title)
            ws.write(fila, 21, "UYU", title)
            ws.write_merge(fila, fila, 22, 24, "UYU Sin IVA", title)
            ws.write(fila, 25, "USD", title)
            ws.write_merge(fila, fila, 26, 28, "USD Sin IVA", title)
            ws.write_merge(fila, fila, 29, 30, "Nº Factura", title)
            ws.write_merge(fila, fila, 31, 32, "Nº Nota de Credito", title)
            #CAMPOS INTERNACIONAL
            for linea_inter in matricula[2]:
                fila += 1
                ws.write(fila, 0, self.convertir_fecha(linea_inter[10]), lineas)
                ws.write_merge(fila, fila, 1, 3, linea_inter[1], lineas)
                ws.write_merge(fila, fila, 4, 6, linea_inter[2], lineas)
                ws.write_merge(fila, fila, 7, 9, linea_inter[11], lineas)
                ws.write_merge(fila, fila, 10, 11,  self.map_regimen()[linea_inter[5]], lineas)
                ws.write_merge(fila, fila, 12, 13, linea_inter[6], lineas)
                ws.write(fila, 14, linea_inter[7], lineas)
                ws.write_merge(fila, fila, 15, 17, linea_inter[3], lineas)
                ws.write_merge(fila, fila, 18, 20, linea_inter[4], lineas)
                if linea_inter[8] == 'UYU':
                    ws.write(fila, 21, linea_inter[8], lineas)
                    ws.write_merge(fila, fila, 22, 24, linea_inter[9], title_number)
                    ws.write(fila, 25, '', lineas)
                    ws.write_merge(fila, fila, 26, 28, '', title_number)
                if linea_inter[8] == 'USD':
                    ws.write(fila, 21, '', lineas)
                    ws.write_merge(fila, fila, 22, 24, '', title_number)
                    ws.write(fila, 25, linea_inter[8], lineas)
                    ws.write_merge(fila, fila, 26, 28, linea_inter[9], title_number)
                ws.write_merge(fila, fila, 29, 30, linea_inter[12], title_number)
                ws.write_merge(fila, fila, 31, 32, linea_inter[13], title_number)

                #CAMPOS TOTAL
                total += 1
                ws.write(total, 0, self.convertir_fecha(linea_inter[10]), lineas)
                ws.write_merge(total, total, 1, 3, linea_inter[1], lineas)
                ws.write_merge(total, total, 4, 6, linea_inter[2], lineas)
                ws.write_merge(total, total, 7, 9, linea_inter[11], lineas)
                ws.write_merge(total, total, 10, 11,  self.map_regimen()[linea_inter[5]], lineas)
                ws.write_merge(total, total, 12, 13, linea_inter[6], lineas)
                ws.write(total, 14, linea_inter[7], lineas)
                ws.write_merge(total, total, 15, 17, linea_inter[3], lineas)
                ws.write_merge(total, total, 18, 20, linea_inter[4], lineas)
                if linea_inter[8] == 'UYU':
                    ws.write(total, 21, linea_inter[8], lineas)
                    ws.write_merge(total, total, 22, 24, linea_inter[9], title_number)
                    ws.write(total, 25, '', lineas)
                    ws.write_merge(total, total, 26, 28, '', title_number)
                    ws.write(total, 29, linea_inter[8], lineas)
                    ws.write_merge(total, total, 30, 32, linea_inter[9], title_number)
                    ws.write(total, 33, 'USD', lineas)
                    ws.write_merge(total, total, 34, 36, self.obtener_cambio(linea_inter[8], linea_inter[9], linea_inter[10]),
                                   title_number)
                if linea_inter[8] == 'USD':
                    ws.write(total, 21, '', lineas)
                    ws.write_merge(total, total, 22, 24, '', title_number)
                    ws.write(total, 25, linea_inter[8], lineas)
                    ws.write_merge(total, total, 26, 28, linea_inter[9], title_number)
                    ws.write(total, 29, 'UYU', lineas)
                    ws.write_merge(total, total, 30, 32, self.obtener_cambio(linea_inter[8], linea_inter[9], linea_inter[10]),
                                   title_number)
                    ws.write(total, 33, linea_inter[8], lineas)
                    ws.write_merge(total, total, 34, 36, linea_inter[9], title_number)
                ws.write_merge(total, total, 37, 38, linea_inter[12], title_number)
                ws.write_merge(total, total, 39, 40, linea_inter[13], title_number)

            fila += 1
            ultima_fila = fila
            primer_fila = 6
            ws.write(ultima_fila, 21, "Total UYU", title)
            ws.write_merge(fila, fila, 22, 24, Formula("SUM(W%s :W%s)" % (primer_fila, ultima_fila)), title_number)
            ws.write(ultima_fila, 25, "Total USD", title)
            ws.write_merge(fila, fila, 26, 28, Formula("SUM(AA%s :AA%s)" % (primer_fila, ultima_fila)), title_number)

        ultima_total = total + 1
        ws.write(ultima_total, 22, "O.Tot UYU", title)
        ws.write_merge(ultima_total, ultima_total, 23, 24, Formula("SUM(W%s :W%s)" % (primer_total, ultima_total)), title_number)
        ws.write(ultima_total, 26, "O.Tot USD", title)
        ws.write_merge(ultima_total, ultima_total, 27, 28, Formula("SUM(AA%s :AA%s)" % (primer_total, ultima_total)), title_number)
        ws.write(ultima_total, 30, "Total UYU", title)
        ws.write_merge(ultima_total, ultima_total, 31, 32, Formula("SUM(AE%s :AE%s)" % (primer_total, ultima_total)), title_number)
        ws.write(ultima_total, 34, "Total USD", title)
        ws.write_merge(ultima_total, ultima_total, 35, 36, Formula("SUM(AI%s :AI%s)" % (primer_total, ultima_total)), title_number)

    def write_page_per_license_plate(self, wb=None, moneda=None, fechas=None):
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
        ws = wb.add_sheet(moneda[0][2], cell_overwrite_ok=True)
        ws.write_merge(0, 0, 0, 8, fechas, color)
        ws.write_merge(0, 0, 9, 11, '', color)
        ws.write_merge(1, 2, 0, 8, '', color)
        ws.write_merge(fila_inicio, fila_fin, 0, 0, "#", title_hashtag)
        ws.write_merge(fila_inicio, fila_fin, 1, 8, "Matricula", title)
        ws.write_merge(1, 2, 9, 11, moneda[0][2], title_factu)
        ws.write_merge(fila_inicio, fila_fin, 9, 11, "Facturado (Sin Impuesto)", title_factu)
        if moneda:
            for info in moneda:
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

    def informe_tramo_matricula(self):
        # Creo el 'Libro' y su 'Pagina'
        wb = Workbook(encoding='utf-8')
        start, stop = self.convert_date_to_datetime(self.start, self.stop)
        facturas = self.env['account.invoice'].search([('date_invoice', '>=', start), ('date_invoice', '<=', stop), ('state', 'in', ('open', 'paid')), ('type', 'in', ('out_invoice', 'out_refund'))], order='date_invoice')
        list_matriculas = self.get_matriculas(facturas)
        fechas = str(start)[:10] + ' / ' + str(stop)[:10]
        if self.tipo_informe == 'summary':
            file_name = 'Informe Tramo Matriculas Resumen - %s.xls' % self.get_report_name(start=self.start, stop=self.stop)
            matriculas_all = self.obtener_license_plate(list_matriculas)
            for moneda in matriculas_all:
                self.write_page_per_license_plate(wb, moneda, fechas)
        if self.tipo_informe == 'all':
            file_name = 'Informe Tramo Matriculas Todo - %s.xls' % self.get_report_name(start=self.start, stop=self.stop)
            list_matriculas.sort(key=lambda x: x[0])
            for matriculas in list_matriculas:
                self.write_page_all(wb, matriculas, fechas)

        if not list_matriculas:
            if self.vehicle_id:
                raise Warning('No se encontraron datos de esa Matricula')
            else:
                raise Warning('No se encontraron Matriculas en esa Fecha')

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
