# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api
from xlwt import *
import base64
from io import BytesIO
import ipdb
from odoo.exceptions import Warning
from ..library import formatters

class Reportes(models.Model):
    _name = 'reportes'
    _description = 'Modelo para la creacion de reportes'

    name = fields.Char()
    start = fields.Datetime(string='Fecha Inicio', required=True, index=True, copy=False)
    stop = fields.Datetime('Fecha Fin', required=True, index=True, copy=False)

    @api.multi
    @api.depends('name', 'start', 'stop')
    def name_get(self):
        return [(rec.id, '%s - %s' % (rec.start, rec.stop)) for rec in self]

    def get_report_name(self, start=None, stop=None):
        report_mame = ''
        if start and stop:
            report_mame = formatters.date_fmt(start.isoformat()[:10]) + ' - ' + formatters.date_fmt(start.isoformat()[:10])
        return report_mame


    def convertir_fecha(self, fecha):
        string = ''
        if fecha:
            string = fecha.strftime("%d - %B")

        return string

    def obtener_numero_carpeta(self, carpeta):
        string = ''
        string = 'C ' + carpeta.name[22:]

        return string

    def obtener_info_producto(self, carga):
        start = ''
        stop = ''
        remito = ''
        driver = ''
        comision = 0

        for producto in carga.producto_servicio_ids:
            start = self.convertir_fecha(producto.start)
            stop = self.convertir_fecha(producto.stop)
            if producto.remito:
                if remito:
                    remito += ' / ' + producto.remito
                else:
                    remito = producto.remito
            if producto.driver_id or producto.chofer:
                driver = producto.driver_id.name if producto.driver_id else producto.chofer
            comision += producto.driver_commission
        list_producto = [start, stop, remito, driver, comision]

        return list_producto

    def write_carpeta_mes_vestas(self, carpetas_mes, wb):

        fila = 1
        carga_anterior = self.env["rt.service.carga"]
        carga_comision = self.env["rt.service.carga"]
        carga_importe = self.env["rt.service.carga"]
        producto_anterior = [0, 0, 0, 0]
        fila_destino = 0
        title = easyxf('font: name Calibri, bold True, height 220; alignment: horizontal center, vertical center; pattern: pattern solid,'
                       ' fore_colour blue; borders: top_color black, bottom_color black, right_color black, left_color black,\
                              left thin, right thin, top thin, bottom thin;')
        title_small = easyxf(
            'font: name Calibri, bold True, height 200; alignment: horizontal center, vertical center; pattern: pattern solid,'
            ' fore_colour blue; borders: top_color black, bottom_color black, right_color black, left_color black,\
                              left thin, right thin, top thin, bottom thin;')
        datos = easyxf('font: height 180; alignment: horizontal center, vertical center; borders: top_color black, bottom_color black, right_color black, left_color black,\
                              left thin, right thin, top thin, bottom thin;')
        datos_importe = easyxf('font: height 180; alignment: horizontal center, vertical center; borders: top_color black, bottom_color black, right_color black, left_color black,\
                                      left thin, right thin, top thin, bottom thin;', num_format_str='#,##0.00;-#,##0.00;')
        moneda = easyxf(
            'font: name Calibri, bold True, height 220; alignment: horizontal right, vertical center; borders: top_color black, bottom_color black,left_color black,\
                              left thin, top thin, bottom thin;')
        total = easyxf(
            'font: name Calibri, bold True, height 220; alignment: horizontal left, vertical center; borders: left_color white, top_color black, bottom_color black, right_color black,\
                              left thin, right thin, top thin, bottom thin;', num_format_str='#,##0.00;-#,##0.00;')
        fecha = carpetas_mes[0].start_datetime.strftime("%B %Y")
        ws = wb.add_sheet(fecha, cell_overwrite_ok=True)
        ws.write_merge(0, 1, 0, 1, "Shipment", title)
        ws.write_merge(0, 1, 2, 3, "Packing List", title)
        ws.write_merge(0, 1, 4, 5, "Pieces", title)
        ws.write_merge(0, 1, 6, 7, "Weight", title)
        ws.write_merge(0, 1, 8, 9, "From", title)
        ws.write_merge(0, 1, 10, 11, "To", title)
        ws.write_merge(0, 1, 12, 13, "ATD", title)
        ws.write_merge(0, 1, 14, 15, "ATA", title)
        ws.write_merge(0, 1, 16, 17, "Received by", title)
        ws.write_merge(0, 1, 18, 19, "Remito Nº", title)
        ws.write_merge(0, 1, 20, 21, "PO", title)
        ws.write_merge(0, 1, 22, 23, "Servicio", title)
        ws.write_merge(0, 1, 24, 26, "Rate in U$D (not included tax 22%)", title_small)
        ws.write_merge(0, 1, 27, 29, "Chofer", title)
        ws.write_merge(0, 1, 30, 31, "Comision", title)

        for carpeta in carpetas_mes:
            carpeta_numero = self.obtener_numero_carpeta(carpeta)
            cargas_ordenadas = carpeta.carga_ids.sorted(key='id')
            for carga in cargas_ordenadas:
                fila += 1
                producto = self.obtener_info_producto(carga)
                ws.write_merge(fila, fila, 0, 1, '', datos)
                ws.write_merge(fila, fila, 2, 3, carga.name if carga.name else 'N/A', datos)
                ws.write_merge(fila, fila, 4, 5, carga.package, datos)
                ws.write_merge(fila, fila, 6, 7, carga.raw_kg, datos)
                if carga.importe_total_carga != 0 or carga.destiny_id != carga_anterior.destiny_id:
                    if fila != 2:
                        ws.write_merge(fila_destino, (fila-1), 8, 9, carga_destino.origin_id.name[7:] if carga_destino.origin_id else "", datos)
                        ws.write_merge(fila_destino, (fila-1), 10, 11, carga_destino.destiny_id.name[7:] if carga_destino.destiny_id else "", datos)
                    carga_destino = carga
                    fila_destino = fila
                if carga.importe_total_carga != 0 or producto[0] != producto_anterior[0] or carga.destiny_id != carga_anterior.destiny_id:
                    if fila != 2:
                        producto_inicio = self.obtener_info_producto(carga_inicio)
                        ws.write_merge(fila_inicio, (fila-1), 12, 13, producto_inicio[0], datos)
                    carga_inicio = carga
                    fila_inicio = fila
                if carga.importe_total_carga != 0 or producto[1] != producto_anterior[1]:
                    if fila != 2:
                        producto_final = self.obtener_info_producto(carga_final)
                        ws.write_merge(fila_final, (fila-1), 14, 15, producto_final[1], datos)
                    carga_final = carga
                    fila_final = fila
                if carga.importe_total_carga != 0 or carga.received_by != carga_anterior.received_by or carga.destiny_id != carga_anterior.destiny_id:
                    if fila != 2:
                        ws.write_merge(fila_recibido, (fila-1), 16, 17, carga_recibido.received_by, datos)
                    carga_recibido = carga
                    fila_recibido = fila
                if carga.importe_total_carga != 0:
                    if fila != 2:
                        producto_importe = self.obtener_info_producto(carga_importe)
                        ws.write_merge(fila_importe, (fila-1), 18, 19, producto_importe[2], datos)
                        ws.write_merge(fila_importe, (fila-1), 20, 21, carga_importe.purchase_order if carga_importe.purchase_order else "", datos)
                        ws.write_merge(fila_importe, (fila-1), 22, 23, carpeta_numero, datos)
                        ws.write_merge(fila_importe, (fila-1), 24, 26, carga_importe.importe_total_carga, datos_importe)
                    carga_importe = carga
                    fila_importe = fila
                if producto[4] != 0 or producto_anterior[3] != producto[3]:
                    if fila != 2:
                        producto_comision = self.obtener_info_producto(carga_comision)
                        ws.write_merge(fila_comision, (fila-1), 27, 29, producto_comision[3], datos)
                        ws.write_merge(fila_comision, (fila-1), 30, 31, producto_comision[4], datos_importe)
                    carga_comision = carga
                    fila_comision = fila
                carga_anterior = carga
                producto_anterior = producto

            ws.write_merge(fila_destino, fila, 8, 9,
                           carga_destino.origin_id.name[7:] if carga_destino.origin_id else "", datos)
            ws.write_merge(fila_destino, fila, 10, 11,
                           carga_destino.destiny_id.name[7:] if carga_destino.destiny_id else "", datos)
            ws.write_merge(fila_inicio, fila, 12, 13, producto_inicio[0], datos)
            ws.write_merge(fila_final, fila, 14, 15, producto_final[1], datos)
            ws.write_merge(fila_recibido, fila, 16, 17, carga_recibido.received_by, datos)
            ws.write_merge(fila_importe, fila, 18, 19, producto_importe[2], datos)
            ws.write_merge(fila_importe, fila, 20, 21, carga_importe.purchase_order if carga_importe.purchase_order else "", datos)
            ws.write_merge(fila_importe, fila, 22, 23, carpeta_numero, datos)
            ws.write_merge(fila_importe, fila, 24, 26, carga_importe.importe_total_carga, datos_importe)
            producto_comision = self.obtener_info_producto(carga_comision)
            ws.write_merge(fila_comision, fila, 27, 29, producto_comision[3], datos)
            ws.write_merge(fila_comision, fila, 30, 31, producto_comision[4], datos_importe)
            fila += 1
            ws.write_merge(fila, fila+1, 24, 24, 'USD ', moneda)
            ws.write_merge(fila, fila+1, 25, 26, Formula("SUM(Y%s :Y%s)" % (3, fila)), total)

    def excel_vestas(self):
        carpeta_obj = self.env["rt.service"]
        carpetas_vestas = carpeta_obj.search([('start_datetime', '>=', self.start), ('stop_datetime', '<=', self.stop), ('partner_invoice_id', '=', 42), ('reference', 'ilike', 'vestas')], order='start_datetime')
        wb = Workbook()
        if not carpetas_vestas:
            raise Warning('No se encontaron Carpetas para el periodo seleccionado')
        for carpeta_mes in carpetas_vestas:
            self.write_carpeta_mes_vestas(carpeta_mes, wb)

        fp = BytesIO()
        wb.save(fp)
        fp.seek(0)
        data = fp.read()
        fp.close()

        data_to_save = base64.encodebytes(data)
        file_name = 'Reporte Vestas - %s.xls' % self.get_report_name(start=self.start, stop=self.stop,)
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

