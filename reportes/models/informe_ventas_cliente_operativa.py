# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api
import string
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning
import xlsxwriter
from xlwt import *
from operator import itemgetter, attrgetter
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

class Reportes(models.Model):
    _inherit = 'informe.ventas.cliente'

    def get_importe_marfrig(self, prod):
        factura = self.env['account.invoice'].search([('service_marfrig_ids', 'in', prod.id)])
        importe = 0
        currency = ''
        if factura:
            for lineas in factura.invoice_line_ids:
                if lineas.product_id == prod.product_id:
                    importe = lineas.price_subtotal
                    currency = lineas.currency_id.name

        return currency, importe

    def get_facturas_operativa(self, start, stop):
        condiciones_busqueda = []
        productos_service = self.get_productos_service_operativa(start, stop)
        productos_consolidado = self.get_productos_consolidado_operativa(start, stop)
        productos_deposito = self.get_productos_deposito_operativa(start, stop)
        productos_marfrig = self.get_productos_marfrig_operativa(start, stop)
        productos_pesos, productos_dolares = self.get_productos_operativa(productos_service, productos_consolidado, productos_marfrig, productos_deposito)

        return productos_pesos, productos_dolares

    def get_productos_service_operativa(self, start, stop):
        productos = self.env['rt.service.productos']
        condiciones_busqueda = [('invoiced', '=', True), ('start', '>=', start), ('start', '<=', stop)]
        if self.partner_invoice_id:
            condiciones_busqueda.append(('partner_invoice_id', '=', self.partner_invoice_id.id))
        if self.regimen:
            condiciones_busqueda.append(('regimen', '=', self.regimen))
        if self.origin_id:
            condiciones_busqueda.append(('origin_id', '=', self.origin_id.id))
        if self.destiny_id:
            condiciones_busqueda.append(('destiny_id', '=', self.destiny_id.id))
        productos = productos.search(condiciones_busqueda)
        return productos

    def get_productos_deposito_operativa(self, start, stop):
        productos = self.env['deposito.service.products']
        condiciones_busqueda = [('invoiced', '=', True), ('start', '>=', start), ('start', '<=', stop)]
        if self.partner_invoice_id:
            condiciones_busqueda.append(('partner_invoice_id', '=', self.partner_invoice_id.id))
        if self.origin_id:
            condiciones_busqueda.append(('origin_id', '=', self.origin_id.id))
        if self.destiny_id:
            condiciones_busqueda.append(('destiny_id', '=', self.destiny_id.id))
        productos = productos.search(condiciones_busqueda)
        return productos

    def get_productos_consolidado_operativa(self, start, stop):
        camiones = self.env['carpeta.camion']
        productos = self.env['producto.servicio.camion']
        condiciones_busqueda = [('start_datetime', '>=', start), ('start_datetime', '<=', stop)]
        if self.regimen:
            condiciones_busqueda.append(('regimen', '=', self.regimen))
        condiciones_busqueda_productos = []
        if self.partner_invoice_id:
            condiciones_busqueda_productos.append(('partner_invoice_id', '=', self.partner_invoice_id.id))
        if self.origin_id:
            return productos
        if self.destiny_id:
            return productos
        condiciones_busqueda_productos.append('|')
        camiones = camiones.search(condiciones_busqueda)
        condiciones_busqueda_productos.append(('camion_id', 'in', camiones.ids))
        cargas = self.env['carga.camion'].search([('camion_id', 'in', camiones.ids)])
        condiciones_busqueda_productos.append(('rt_carga_id', 'in', cargas.ids))
        productos = productos.search(condiciones_busqueda_productos)
        return productos

    def get_productos_marfrig_operativa(self, start, stop):
        productos = self.env['marfrig.service.products']
        condiciones_busqueda = [('invoiced', '=', True), ('start', '>=', start), ('start', '<=', stop)]
        if self.partner_invoice_id:
            condiciones_busqueda.append(('planta_id', '=', self.partner_invoice_id.id))
        if self.origin_id:
            condiciones_busqueda.append(('origin_id', '=', self.origin_id.id))
        if self.destiny_id:
            condiciones_busqueda.append(('destiny_id', '=', self.destiny_id.id))
        if self.regimen and self.regimen != 'expo_nat':
            return productos
        productos = productos.search(condiciones_busqueda)
        return productos

    def obtener_clientes_operativa(self, productos):
        dic_cliente = {}
        precio = 0
        precio_cliente = 0
        cliente_anterior = ''
        if productos:
            for producto in productos:
                precio = producto[7]
                cliente = producto[1]
                if cliente == cliente_anterior:
                    precio_cliente += precio
                else:
                    if cliente_anterior:
                        dic_cliente[cliente_anterior] = precio_cliente
                    precio_cliente = precio
                cliente_anterior = cliente

        dic_cliente[cliente_anterior] = precio_cliente
        dic_cliente = sorted(dic_cliente.items(), key=lambda x: x[1], reverse=True)
        return dic_cliente

    def get_productos_operativa(self, productos_service, productos_consolidado, productos_marfrig, productos_deposito):
        productos_pesos = []
        productos_dolares = []
        for prod in productos_service:
            datos = []
            datos.append(prod.start)
            datos.append(prod.partner_invoice_id.name if prod.partner_invoice_id else 'N/A')
            datos.append(prod.partner_id.name)
            datos.append(prod.regimen if prod.regimen else 'N/A')
            datos.append(prod.origin_id.name if prod.origin_id else 'N/A')
            datos.append(prod.destiny_id.name if prod.destiny_id else 'N/A')
            datos.append(prod.currency_id.name)
            datos.append(prod.importe)
            if prod.currency_id.name == 'UYU':
                productos_pesos.append(datos)
            if prod.currency_id.name == 'USD':
                productos_dolares.append(datos)
            datos.append((prod.rt_service_id.name if prod.rt_service_id else 'N/A SERVICE') + ' - ' + (prod.rt_carga_id.seq if prod.rt_carga_id else 'N/A SERVICE'))
            datos.append(prod.product_id.name)

        for prod in productos_consolidado:
            camion = prod.rt_carga_id.camion_id if prod.rt_carga_id.camion_id else prod.camion_id
            carga = prod.rt_carga_id if prod.rt_carga_id else ''
            datos = []
            datos.append(camion.start_datetime)
            datos.append(prod.partner_invoice_id.name if prod.partner_invoice_id.name else 'N/A')
            datos.append(prod.partner_invoice_id.name)
            datos.append(prod.regimen if prod.regimen else 'N/A')
            datos.append(prod.origin_id.name if prod.origin_id else camion.aduana_origen_id.name if camion.aduana_origen_id else 'N/A')
            datos.append(prod.destiny_id.name if prod.destiny_id else camion.aduana_destino_id.name if camion.aduana_destino_id else 'N/A')
            datos.append(prod.currency_id.name)
            datos.append(prod.importe)
            if prod.currency_id.name == 'UYU':
                productos_pesos.append(datos)
            if prod.currency_id.name == 'USD':
                productos_dolares.append(datos)
            datos.append((camion.name if camion else 'N/A CAMION') + ' - ' + (carga.name if (carga and carga.name) else 'N/A CAMION' if carga else ''))
            datos.append(prod.product_id.name)

        for prod in productos_marfrig:
            datos = []
            datos.append(prod.start)
            datos.append(prod.planta_id.name if prod.planta_id else 'N/A')
            datos.append(prod.planta_id.name)
            datos.append('expo_nat')
            datos.append(prod.origin_id.name if prod.origin_id else 'N/A')
            datos.append(prod.destiny_id.name if prod.destiny_id else 'N/A')
            currency, importe = self.get_importe_marfrig(prod)
            datos.append(currency)
            datos.append(importe)
            if currency == 'UYU':
                productos_pesos.append(datos)
            if currency == 'USD':
                productos_dolares.append(datos)
            datos.append(prod.mrf_srv_id.name)
            datos.append(prod.product_id.name)

        for prod in productos_deposito:
            datos = []
            datos.append(prod.start)
            datos.append(prod.partner_invoice_id.name if prod.partner_invoice_id else 'N/A')
            datos.append(prod.partner_invoice_id.name)
            datos.append('N/A')
            datos.append(prod.origin_id.name if prod.origin_id else 'N/A')
            datos.append(prod.destiny_id.name if prod.destiny_id else 'N/A')
            datos.append(prod.currency_id.name)
            datos.append(prod.importe)
            if prod.currency_id.name == 'UYU':
                productos_pesos.append(datos)
            if prod.currency_id.name == 'USD':
                productos_dolares.append(datos)
            datos.append(prod.deposito_srv_id.name)
            datos.append(prod.product_id.name)

        productos_pesos = sorted(productos_pesos, key=itemgetter(1, 0))
        productos_dolares = sorted(productos_dolares, key=itemgetter(1, 0))

        return productos_pesos, productos_dolares

    def write_page_all_operativa(self, wb=None, currency=None, productos=None, nombre_filtro=None, fechas=None):
        fila = 4
        columna_inicio = 3
        columna_fin = 5
        title = easyxf('font: name Calibri, bold True; alignment: horizontal left')
        total = easyxf('font: name Calibri, bold True; alignment: horizontal right')
        title_number = easyxf('font: name Calibri; alignment: horizontal right',
                              num_format_str='#,##0.00;-#,##0.00;')
        lineas = easyxf('font: name Calibri; alignment: horizontal left')
        ws = wb.add_sheet(currency, cell_overwrite_ok=True)
        ws.write_merge(fila - 3, fila - 3, 0, 2, fechas, title)
        if nombre_filtro:
            ws.write_merge(fila - 2, fila - 2, 0, 5, nombre_filtro, title)
        ws.write_merge(fila, fila, 0, 0, "Fecha", title)
        ws.write_merge(fila, fila, 1, 2, "Nombre", title)
        if not self.product_id:
            ws.write_merge(fila, fila, columna_inicio, (columna_fin - 1), "Producto", title)
            columna_inicio += 2
            columna_fin += 2
        ws.write_merge(fila, fila, columna_inicio, columna_fin, "Cliente a Facturar", title)
        columna_inicio = columna_fin + 1
        columna_fin = columna_fin + 2
        if not self.partner_invoice_id:
            ws.write_merge(fila, fila, columna_inicio, (columna_fin + 1), "Dueño de la Mercaderia", title)
            columna_fin += 1
            columna_inicio = columna_fin + 1
            columna_fin += 2
        if not self.regimen:
            ws.write_merge(fila, fila, columna_inicio, columna_fin, "Regimen", title)
            columna_inicio += 2
            columna_fin += 2
        if not self.origin_id:
            ws.write_merge(fila, fila, columna_inicio, (columna_fin + 1), "Origen", title)
            columna_fin += 1
            columna_inicio = columna_fin + 1
            columna_fin += 2
        if not self.destiny_id:
            ws.write_merge(fila, fila, columna_inicio, (columna_fin + 1), "Destino", title)
            columna_fin += 1
            columna_inicio = columna_fin + 1
            columna_fin += 2
        ws.write_merge(fila, fila, columna_inicio, columna_inicio, "Moneda", title)
        ws.write_merge(fila, fila, (columna_inicio + 1), (columna_inicio + 2), "Importe", title)
        formula_total = self.posicion_total(columna_inicio)
        if productos:
            for producto in productos:
                fila += 1
                columna_inicio = 3
                columna_fin = 5
                ws.write_merge(fila, fila, 0, 0, self.convertir_fecha(producto[0]), lineas)
                ws.write_merge(fila, fila, 1, 2, producto[8], lineas)
                if not self.product_id:
                    ws.write_merge(fila, fila, columna_inicio, (columna_fin - 1), producto[9], lineas)
                    columna_inicio += 2
                    columna_fin += 2
                ws.write_merge(fila, fila, columna_inicio, columna_fin, producto[1], lineas)
                columna_inicio = columna_fin + 1
                columna_fin = columna_fin + 2
                if not self.partner_invoice_id:
                    ws.write_merge(fila, fila, columna_inicio, (columna_fin + 1), producto[2], lineas)
                    columna_fin += 1
                    columna_inicio = columna_fin + 1
                    columna_fin += 2
                if not self.regimen:
                    if producto[3] != 'N/A':
                        ws.write_merge(fila, fila, columna_inicio, columna_fin, self.map_regimen()[producto[3]],
                                       lineas)
                    else:
                        ws.write_merge(fila, fila, columna_inicio, columna_fin, 'N/A', lineas)
                    columna_inicio += 2
                    columna_fin += 2
                if not self.origin_id:
                    ws.write_merge(fila, fila, columna_inicio, (columna_fin + 1), producto[4], lineas)
                    columna_fin += 1
                    columna_inicio = columna_fin + 1
                    columna_fin += 2
                if not self.destiny_id:
                    ws.write_merge(fila, fila, columna_inicio, (columna_fin + 1), producto[5], lineas)
                    columna_fin += 1
                    columna_inicio = columna_fin + 1
                    columna_fin += 2
                ws.write_merge(fila, fila, columna_inicio, columna_inicio, producto[6], title_number)
                ws.write_merge(fila, fila, (columna_inicio + 1), (columna_inicio + 2), producto[7], title_number)

            fila += 1
            ultima_fila = fila
            ws.write(ultima_fila, (columna_fin - 1), "Total:", total)
            primer_fila = 4
            ws.write_merge(fila, fila, columna_fin, columna_fin + 1,
                           Formula(formula_total % (primer_fila, ultima_fila)), title_number)

    def write_page_per_client_operativa(self, wb=None, currency=None, productos=None, nombre_filtro=None, fechas=None):
        columna_fin = 5
        numero = 1
        title = wb.add_format({
            'font_size': 16,
            'bold': 1,
            'border': 1,
            'align': 'center',
            'fg_color': 'black',
            'font_color': 'white'})
        color_bold = wb.add_format({
            'bold': 1,
            'font_size': 10,
            'border': 1,
            'align': 'center',
            'fg_color': 'black',
            'font_color': 'white'})
        color = wb.add_format({
            'font_size': 10,
            'border': 1,
            'align': 'center',
            'fg_color': 'black',
            'font_color': 'white'})
        color_bold_right = wb.add_format({
            'bold': 1,
            'font_size': 10,
            'border': 1,
            'num_format': '##0.00',
            'align': 'right',
            'fg_color': 'black',
            'font_color': 'white'})
        title_hashtag = wb.add_format({
            'bold': 1,
            'font_size': 10,
            'border': 1,
            'align': 'center',
            'fg_color': 'black',
            'font_color': 'orange'})
        number = wb.add_format({
            'border': 1,
            'font_size': 10,
            'num_format': '##0.00',
            'align': 'right',
            'fg_color': '#6495ED',
            'border_color': 'black',
            'font_color': 'black'})
        lineas = wb.add_format({
            'align': 'left',
            'font_size': 10,
            'fg_color': 'white',
            'font_color': 'black'})
        lineas_percent = wb.add_format({
            'align': 'right',
            'right': 1,
            'num_format': '0.00%',
            'font_size': 10,
            'fg_color': 'white',
            'font_color': 'black'})
        fin = wb.add_format({
            'top': 1,
            'top_color': 'black'})
        total_number = wb.add_format({
            'right': 1,
            'bottom': 1,
            'font_size': 10,
            'num_format': '##0.00',
            'align': 'right',
            'fg_color': '#6495ED',
            'font_color': 'black'})
        total_title = wb.add_format({
            'bold': 1,
            'left': 1,
            'bottom': 1,
            'font_size': 10,
            'align': 'left',
            'fg_color': '#6495ED',
            'font_color': 'black'})
        moneda = 'Cliente ' + currency
        ws = wb.add_worksheet(currency)
        ws.merge_range('B1:I1', fechas, color_bold)
        ws.merge_range('M1:N3', '', color_bold)
        ws.write(0, 0, '', color_bold)
        ws.merge_range('J1:L1', '', color_bold)
        ws.write(3, 0, '', color_bold)
        if nombre_filtro:
            ws.merge_range('A2:I3', nombre_filtro, title)
        else:
            ws.merge_range('A2:I3', '', title)
        ws.write(4, 0, "#", title_hashtag)
        ws.merge_range('B4:I5', "Cliente", title)
        ws.merge_range('J2:L3', currency, title)
        ws.merge_range('J4:L5', "Facturado (Sin Impuesto)", color_bold)
        clientes = self.obtener_clientes_operativa(productos)
        if clientes:
            for info in clientes:
                columna_fin += 1
                formula = "{=J" + str(columna_fin) + "/M5}"
                ws.write(columna_fin - 1, 0, numero, color)
                ws.merge_range('B%s:I%s' % (columna_fin, columna_fin), info[0], lineas)
                ws.merge_range('J%s:L%s' % (columna_fin, columna_fin), info[1], number)
                ws.merge_range('M%s:N%s' % (columna_fin, columna_fin), formula, lineas_percent)
                numero += 1

            # ultima_fila = columna_fin + 1
            formula = "{=SUM(J4:J" + str(columna_fin) + ")}"
            ws.merge_range('K%s:L%s' % (columna_fin + 1, columna_fin + 1), formula, total_number)
            ws.merge_range('B%s:I%s' % (columna_fin + 1, columna_fin + 1), '', fin)
            ws.merge_range('M%s:N%s' % (columna_fin + 1, columna_fin + 1), '', fin)
            ws.write(columna_fin, 9, "Total", total_title)

        ws.merge_range('M4:N4', '100%', color_bold)
        ws.merge_range('M5:N5', formula, color_bold_right)


        top10 = wb.add_chart({'type': 'pie'})
        top10.add_series({
            'name': 'TOP 10',
            'categories': [moneda, 5, 1, 14, 1],
            'values': [moneda, 5, 9, 14, 9],

        })

        ws.insert_chart('P6', top10, {'x_scale': 1.2, 'y_scale': 1.2})

    def informe_ventas_cliente_operativa(self):
        # Creo el 'Libro' y su 'Pagina'
        file_name = 'Informe Ventas Clientes Operativa - %s.xls' % self.get_report_name(start=self.start, stop=self.stop)
        fp = BytesIO()
        if self.tipo_informe == 'all':
            wb = Workbook(encoding='utf-8')
        if self.tipo_informe == 'summary':
            wb = xlsxwriter.Workbook(fp)
        start, stop = self.convert_date_to_datetime(self.start, self.stop)
        productos_pesos, productos_dolares = self.get_facturas_operativa(start, stop)
        list_productos = [productos_pesos, productos_dolares]
        fechas = str(start)[:10] + ' / ' + str(stop)[:10]
        nombre_filtro = self.obtener_nombre_filtrado()
        if not productos_pesos and not productos_dolares:
            if self.partner_invoice_id or self.regimen or self.origin_id or self.destiny_id:
                raise Warning('No se encontraron lineas con esos filtros')
            else:
                raise Warning('No se encontraron lineas')

        for productos in list_productos:
            if productos:
                if productos == productos_pesos:
                    currency = 'UYU'
                else:
                    currency = 'USD'
                if self.tipo_informe == 'all':
                    self.write_page_all_operativa(wb, currency, productos, nombre_filtro, fechas)
                if self.tipo_informe == 'summary':
                    self.write_page_per_client_operativa(wb, currency, productos, nombre_filtro, fechas)

        if self.tipo_informe == 'all':
            wb.save(fp)
            fp.seek(0)
            data = fp.read()
            fp.close()
        if self.tipo_informe == 'summary':
            wb.close()
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

