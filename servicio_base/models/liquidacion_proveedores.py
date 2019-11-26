# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api
from xlwt import Workbook,Style, easyxf
from io import StringIO
from ..library import formatters
import base64
import ipdb
from io import BytesIO
import ipdb

#
# class rt_service_product_supplier(models.Model):
#     _inherit = 'rt.service.product.supplier'
#
#     def get_service_date(self):
#         if self.rt_service_id and self.rt_service_id.start_datetime:
#             self.service_date = self.rt_service_id.start_datetime
#         return

class descargar_hojas(models.TransientModel):
    _name = 'descargar.hojas'
    archivo_nombre = fields.Char(string='Nombre del archivo')
    archivo_contenido = fields.Binary(string="Archivo")

class LiquidacionProveedores(models.Model):
    _name = "liquidacion.proveedores"
    _description = "Reporte Liquidación Proveedores"

    name = fields.Char(string='Nombre')
    inicio = fields.Date(string='Desde', required=True)
    fin = fields.Date(string='Hasta', required=True)
    prevista = fields.Html(string='Prevista', readonly=True)
    informe = fields.Binary(string='Informe')
    archivo = fields.Binary(string="placeholder")
    partner_id = fields.Many2one(comodel_name='res.partner', string='Fletero', help='Vacio Trae todos los FLeteros')
    sin_factura = fields.Boolean(string='Sin Facturas')

    def get_fleteros(self, inicio, fin, fletero=False, sin_factura=False):
        if fletero:
            if sin_factura:
                fleteros = self.env['rt.service.product.supplier'].search([('service_date', '>=', inicio), ('service_date', '<=', fin), ('supplier_id', '=', fletero),('invoice_id','=',False)], order='service_date')
            else:
                fleteros = self.env['rt.service.product.supplier'].search([('service_date', '>=', inicio), ('service_date', '<=', fin), ('supplier_id', '=', fletero),], order='service_date')
        if not fletero:
            if sin_factura:
                fleteros = self.env['rt.service.product.supplier'].search([('service_date', '>=', inicio), ('service_date', '<=', fin),('invoice_id','=',False)], order='service_date')
            else:
                fleteros = self.env['rt.service.product.supplier'].search([('service_date', '>=', inicio), ('service_date', '<=', fin)],order='service_date')
        #fleteros = self.env['rt.service.product.supplier'].search([('rt_service_id', '=', 1069)])
        return fleteros


    @api.multi
    def gen_report_xls_ventas_fleteros(self):
        #Primero actualizamos las fechas en los registros
        # self.env['trt.service.product.supplier'].get_service_date()
        # Estilos
        title_big = easyxf('font: name Arial, bold True; alignment: horizontal center;font:height 300;')
        title = easyxf('font: name Calibri, bold True; alignment: horizontal left')
        title_number = easyxf('font: name Calibri, bold True; alignment: horizontal right',
                                num_format_str='#,##0.00;-#,##0.00;')
        lineas = easyxf('font: name Calibri; alignment: horizontal left')
        fecha = easyxf('font: name Calibri; alignment: horizontal center', num_format_str='DD/MM/YYYY')
        numbers = easyxf('font: name Calibri; alignment: horizontal right',
                         num_format_str='#,##0.00;-#,##0.00;')
        # numbers = easyxf('font: name Calibri; alignment: horizontal right')
        bold_number = easyxf('font: name Calibri, bold True;alignment: horizontal right',
                                num_format_str='#,##0.00;-#,##0.00;')
        bold_fecha = easyxf('font: name Calibri, bold True; alignment: horizontal center',
                            num_format_str='DD/MM/YYYY')

        #Creo el 'Libro' y su 'Pagina'
        wb = Workbook(encoding='utf-8')
        ws = wb.add_sheet('Sheet 1', cell_overwrite_ok=True)

        #Titulo del EC si es cliente o proveedor
        nombre_informe = "Liquidación de Fleteros"
        # Datos de la empresa y fecha de emision
        ws.write(0, 0, self.env['res.company'].browse(1).name, title)
        ws.write(0, 5, formatters.date_fmt(fields.Date.today().isoformat()), title)

        # Nombre del informe y cliente
        ws.row(2).height = 2 * 200
        ws.row(3).height = 2 * 200
        ws.write (2, 2, nombre_informe, title_big)

        # Filtros de fecha
        ws.col(1).width = 10 * 367
        ws.col(3).width = 10 * 367
        ws.write(5, 0, "Desde", title)
        ws.write(5, 1, formatters.date_fmt(self.inicio.today().isoformat()), bold_fecha)
        ws.write(5, 2, "Hasta", title)
        ws.write(5, 3, formatters.date_fmt(self.inicio.today().isoformat()), bold_fecha)

        # Variables para el redimencionado de celdas
        maximo_largo_contenido_por_columna = [int(), int(), int(),int(), int(), int(),int(), int(), int(),int(), int(), int(), int(), int(), int(), int(), int()]

        fila = 7

        fleteros = self.get_fleteros(self.inicio, self.fin, fletero=self.partner_id.id, sin_factura=self.sin_factura)
        rt_supplier_object = self.env['rt.service.product.supplier']
        fletero_dolares = ()
        fleteros_pesos = ()


        for flet in fleteros:
            if flet.currency_id.name == 'USD':
                fletero_dolares += flet.id,
            if flet.currency_id.name == 'UYU':
                fleteros_pesos += flet.id,


        #IMPO
        total_importe_impo_pesos = float()
        total_monto_impo_pesos = float()
        total_importe_impo_dolares = float()
        total_monto_impo_dolares = float()

        fleteros_impo_pesos = ()
        fleteros_impo_dolares = ()
        fleteros_expo_pesos = ()
        fleteros_expo_dolares = ()
        fleteros_tto_pesos = ()
        fleteros_tto_dolares = ()
        fleteros_interno_pesos = ()
        fleteros_interno_fisc_dolares = ()
        fleteros_plaza_pesos = ()
        fleteros_plaza_dolares = ()
        fleteros_gravados_pesos = ()
        fleteros_gravados_dolares = ()
        fleteros_no_gravados_pesos = ()
        fleteros_no_gravados_dolares = ()
        fleteros_retiros_pesos = ()
        fleteros_retiros_dolares = ()
        for impo in fleteros:
            #Vamos a seguir separando por regimen
            #Si vamos a preguntar de que lado viene... Servicio Nacional / Internacional Consolidado o Marfrig

            #Servicio Nacional
            if impo.rt_service_id:
                if impo.rt_service_id.regimen == 'impo_nat':
                    if impo.rt_service_id.currency_id.name == 'UYU':
                        fleteros_impo_pesos += impo.id,
                    if impo.rt_service_id.currency_id.name == 'USD':
                        fleteros_impo_dolares += impo.id,





        if fleteros_impo_dolares:
            ws.write(fila, 0, "Moneda", title)
            ws.write(fila, 1, "USD", title)
            fila = fila + 1
            ws.write(fila, 0, "Tipo", title)
            ws.write(fila, 1, "IMPO", title)
            # Cabezales de tabla
            fila += 2
            ws.write(fila, 0, "Proveedor", title)
            ws.write(fila, 1, "Fecha", title)
            ws.write(fila, 2, "Servicio", title)
            ws.write(fila, 3, "Origen", title)
            ws.write(fila, 4, "Destino", title)
            ws.write(fila, 5, "DUA", title)
            ws.write(fila, 6, "Contenedor", title)
            ws.write(fila, 7, "Moneda", title)
            ws.write(fila, 8, "Monto", title_number)
            ws.write(fila, 9, "Importe", title_number)
            ws.write(fila, 10, "Linea", title)
            ws.write(fila, 11, "Fecha Linea", title)
            ws.write(fila, 12, "Producto", title)
            ws.write(fila, 13, "Solicitante del Viaje", title)
            ws.write(fila, 14, "Cliente a facturar", title)

            total_importe_dolares = float()

            fila += 1
            for linea in rt_supplier_object.browse(fleteros_impo_dolares):
                fletero = linea.supplier_id.name
                largo_fletero = len(linea.supplier_id.name)
                maximo_largo_contenido_por_columna[0] = max(maximo_largo_contenido_por_columna[0], largo_fletero)
                # """""""""""*"""""""
                fecha_sp = linea.service_date.strftime("%d/%m/%Y")
                largo_fecha = len(fecha_sp)
                maximo_largo_contenido_por_columna[1] = max(maximo_largo_contenido_por_columna[1], largo_fecha)
                # """""""""""*"""""""
                servicio = linea.rt_service_id.name
                largo_servicio = len(servicio)
                maximo_largo_contenido_por_columna[2] = max(maximo_largo_contenido_por_columna[2], largo_servicio)
                # """""""""""*"""""""
                origen = linea.rt_service_product_id.origin_id.name
                largo_origen = len(str(origen))
                maximo_largo_contenido_por_columna[3] = max(maximo_largo_contenido_por_columna[3], largo_origen)
                # """""""""""*"""""""
                destino = linea.rt_service_product_id.destiny_id.name
                largo_destino = len(str(destino))
                maximo_largo_contenido_por_columna[4] = max(maximo_largo_contenido_por_columna[4], largo_destino)
                # """""""""""*"""""""
                dua = linea.dua
                largo_dua = len(str(dua))
                maximo_largo_contenido_por_columna[5] = max(maximo_largo_contenido_por_columna[5], largo_dua)
                # """""""""""*"""""""
                contenedor = linea.tack_id
                largo_contenedor = len(str(contenedor))
                maximo_largo_contenido_por_columna[6] = max(maximo_largo_contenido_por_columna[6], largo_contenedor)
                # """""""""""*"""""""
                moneda = linea.currency_id.name
                largo_moneda = 10
                maximo_largo_contenido_por_columna[7] = max(maximo_largo_contenido_por_columna[7], largo_moneda)
                # """""""""""*"""""""
                monto = linea.amount
                largo_monto = len(formatters.currency_fmt(monto))
                maximo_largo_contenido_por_columna[8] = max(maximo_largo_contenido_por_columna[8], largo_monto)
                # """""""""""*"""""""
                importe = linea.price_subtotal
                largo_importe = len(formatters.currency_fmt(importe))
                maximo_largo_contenido_por_columna[9] = max(maximo_largo_contenido_por_columna[9], largo_importe)
                # """""""""""*"""""""
                linea_sp = linea.rt_service_product_id.name
                largo_linea_sp = len(linea_sp)
                maximo_largo_contenido_por_columna[10] = max(maximo_largo_contenido_por_columna[10], largo_linea_sp)

                fecha_linea_sp = linea.rt_service_product_id.start.strftime("%d/%m/%Y")
                largo_fecha_linea_sp = len(fecha_linea_sp)
                maximo_largo_contenido_por_columna[11] = max(maximo_largo_contenido_por_columna[11],
                                                             largo_fecha_linea_sp)
                # """""""""""*"""""""
                producto = linea.rt_service_product_id.product_id.name_get()[0][1]
                largo_producto = len(producto)
                maximo_largo_contenido_por_columna[12] = max(maximo_largo_contenido_por_columna[12], largo_producto)
                total_importe_impo_dolares += importe
                total_monto_impo_dolares += monto

                solicitante = linea.rt_service_id.partner_id.name if linea.rt_service_id.partner_id.name else ' '
                largo_solicitante = len(linea.rt_service_id.partner_invoice_id.name)
                maximo_largo_contenido_por_columna[13] = max(maximo_largo_contenido_por_columna[13], largo_solicitante)

                cliente_a_facturar = linea.rt_service_id.partner_invoice_id.name if linea.rt_service_id.partner_invoice_id.name else ' '
                largo_a_facturar = len(linea.rt_service_id.partner_invoice_id.name)
                maximo_largo_contenido_por_columna[13] = max(maximo_largo_contenido_por_columna[14], largo_a_facturar)

                numero_factura = linea.invoice_id.number if linea.invoice_id.number else ' '
                largo_numero_factura = len(linea.rt_service_id.partner_invoice_id.name)
                maximo_largo_contenido_por_columna[13] = max(maximo_largo_contenido_por_columna[15],
                                                             largo_numero_factura)

                ws.write(fila, 0, fletero, lineas)
                ws.write(fila, 1, fecha_sp, fecha)
                ws.write(fila, 2, servicio, lineas)
                ws.write(fila, 3, origen, lineas)
                ws.write(fila, 4, destino, lineas)
                ws.write(fila, 5, dua, lineas)
                ws.write(fila, 6, contenedor, lineas)
                ws.write(fila, 7, moneda, lineas)
                ws.write(fila, 8, formatters.currency_fmt(monto), numbers)
                ws.write(fila, 9, formatters.currency_fmt(importe), numbers)
                ws.write(fila, 10, linea_sp, lineas)
                ws.write(fila, 11, fecha_linea_sp, lineas)
                ws.write(fila, 12, producto, lineas)
                ws.write(fila, 13, solicitante, lineas)
                ws.write(fila, 14, cliente_a_facturar, lineas)
                ws.write(fila, 15, numero_factura, lineas)
                fila += 1

            # Totales
            largo_total_importe_pesos = len(formatters.currency_fmt(total_importe_dolares))
            maximo_largo_contenido_por_columna[12] = max(maximo_largo_contenido_por_columna[12], largo_total_importe_pesos)
            ws.write(fila, 7, "Total", title_number)
            ws.write(fila, 8, total_importe_impo_dolares, title_number)
            ws.write(fila, 9, total_monto_impo_dolares, title_number)
            fila += 2


        # Salvo el contenido
        fp = BytesIO()
        wb.save(fp)
        fp.seek(0)
        data = fp.read()
        fp.close()

        data_to_save = base64.encodebytes(data)
        file_name = 'Liquidacion_Fleteros.xls'
        wiz_id = self.env['descargar.hojas'].create({'archivo_nombre': file_name,
                                                         'archivo_contenido': data_to_save})
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