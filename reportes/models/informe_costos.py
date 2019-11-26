# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api
from xlwt import *
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning
import xlwt
from io import StringIO
from ..library import formatters
import base64
import string
from io import BytesIO
import ipdb
import locale
import time
from odoo.tools.misc import DEFAULT_SERVER_DATE_FORMAT
import itertools
from datetime import date, datetime, timedelta
import pytz

class Reportes(models.Model):
    _name = 'informe.costos'

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
    informacion = fields.Selection([('crudo', 'Crudo'), ('modulo', 'Modulo')], string='Tipo de Informacion')
    tipo_informe = fields.Selection([('all', 'Todo'), ('summary', 'Resumen')], string='Tipo de Informe')
    supplier_id = fields.Many2one(comodel_name='res.partner', string='Proveedor', domain=[('supplier', '=', True)])
    regimen = fields.Selection(_get_operation_type, string="Regimen", store=True)
    make_informe_all = fields.Boolean()

    @api.onchange('supplier_id')
    def onchane_supplier_id(self):
        if self.supplier_id:
            self.make_informe_all = True
            self.tipo_informe = 'all'
        else:
            self.make_informe_all = False

    def obtener_nombre_filtrado(self):
        nombre_filtro = ''
        if self.supplier_id:
            nombre_filtro += self.supplier_id.name
        if self.regimen:
            if nombre_filtro:
                nombre_filtro += ' / ' + self.map_regimen()[self.regimen]
            else:
                nombre_filtro = self.map_regimen()[self.regimen]
        return nombre_filtro

    @api.multi
    @api.depends('name', 'start', 'stop')
    def name_get(self):
        return [(rec.id, '%s - %s' % (rec.start, rec.stop)) for rec in self]

    def posicion_total(self, columna_inicio):
        dicofwords = {i: list(string.ascii_uppercase)[i] for i in range(0, len(list(string.ascii_uppercase)))}
        formula_total = "SUM(" + dicofwords[columna_inicio+1] + "%s :" + dicofwords[columna_inicio+1]+ "%s)"

        return formula_total

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

    def obtener_carpetas(self, facturas):
        carpetas = []
        for factura in facturas:
            carpetas.append(factura.rt_service_id.id)

        return carpetas

    def get_pesos(self, objeto, condiciones_busqueda):
        proveedores = self.env['rt.service.product.supplier']
        purchase_order = self.env['purchase.order']
        pesos = self.env['res.currency'].search([('name', '=', 'UYU')]).id
        condiciones_busqueda.append(('currency_id', '=', pesos))
        if objeto == proveedores:
            facturas_pesos = objeto.search(condiciones_busqueda, order='supplier_id , create_date')
        if objeto == purchase_order:
            facturas_pesos = objeto.search(condiciones_busqueda, order='partner_id , date_order')

        return facturas_pesos

    def get_dolares(self, objeto, condiciones_busqueda):
        #Si la lista viene con la condicion de busqueda para pesos, la reemplazamos por dolares
        # condiciones_busqueda.remove(('currency_id', '=', 46))
        proveedores = self.env['rt.service.product.supplier']
        purchase_order = self.env['purchase.order']
        dolares = self.env['res.currency'].search([('name', '=', 'USD')]).id
        condiciones_busqueda = list(map(lambda x: x if x != ('currency_id', '=', 46) else ('currency_id', '=', dolares), condiciones_busqueda))
        if objeto == proveedores:
            facturas_dolares = objeto.search(condiciones_busqueda, order='supplier_id , create_date')
        if objeto == purchase_order:
            facturas_dolares = objeto.search(condiciones_busqueda, order='partner_id , date_order')

        return facturas_dolares

    def get_proveedores_con_factura(self, proveedores, start, stop):
        ids_proveedores = []
        list_proveedores = proveedores.search([('create_date', '>=', start), ('create_date', '<=', stop), ('invoice_id', '!=', False)])
        for proveedor in list_proveedores:
            if proveedor.invoice_id.date_invoice > (stop.date()):
                ids_proveedores.append(proveedor.invoice_id.id)

        return ids_proveedores

    def get_proveedor(self, start, stop):
        productos_service = self.env['rt.service.productos']
        productos_consolidado = self.env['producto.servicio.camion']
        productos_marfrig = self.env['marfrig.service.products']
        proveedores = self.env['rt.service.product.supplier']
        proveedores_factura = self.get_proveedores_con_factura(proveedores, start, stop)
        condiciones_busqueda = [('service_date', '>=', start), ('service_date', '<=', stop), '|', ('invoice_id', '=', False), ('invoice_id', 'in', proveedores_factura)]
        if self.supplier_id:
            condiciones_busqueda.append(('supplier_id', '=', self.supplier_id.id))
        condiciones_busqueda.append(('currency_id', '=', 46))
        proveedores_pesos = self.get_pesos(proveedores, condiciones_busqueda)
        proveedores_dolares = self.get_dolares(proveedores, condiciones_busqueda)
        if self.regimen:
            productos_service = self.get_productos_service(productos_service)
            productos_consolidado = self.get_productos_consolidado(productos_consolidado)
            if self.regimen == 'expo_nat':
                productos_marfrig = self.get_productos_marfrig(productos_marfrig)
            lineas = self.env['rt.service.product.supplier'].search(['|', '|', ('rt_service_product_id', 'in', productos_service.ids),
                                                              ('rt_consol_product_id', 'in', productos_consolidado.ids), ('rt_marfrig_product_id', 'in', productos_marfrig.ids)])
            id_pesos = []
            id_dolares = []
            for filtrado in lineas:
                if filtrado.id in proveedores_pesos.ids:
                    id_pesos.append(filtrado.id)
                if filtrado.id in proveedores_dolares.ids:
                    id_dolares.append(filtrado.id)
            proveedores_pesos = self.env['rt.service.product.supplier'].search([('id', 'in', id_pesos)], order='supplier_id , service_date')
            proveedores_dolares = self.env['rt.service.product.supplier'].search([('id', 'in', id_dolares)], order='supplier_id , service_date')

        return proveedores_pesos, proveedores_dolares

    def get_purchase_order(self, start, stop):
        proveedores_dolares = []
        proveedores_pesos = []
        if not self.regimen:
            purchase_order = self.env['purchase.order']
            condiciones_busqueda = [('date_order', '>=', start), ('date_order', '<=', stop)]
            if self.supplier_id:
                condiciones_busqueda.append(('partner_id', '=', self.supplier_id.id))
            condiciones_busqueda.append(('currency_id', '=', 46))
            proveedores_pesos = self.get_pesos(purchase_order, condiciones_busqueda)
            proveedores_dolares = self.get_dolares(purchase_order, condiciones_busqueda)

        return proveedores_pesos, proveedores_dolares

    def get_productos_service(self, productos):
        if self.regimen:
            condiciones_busqueda = [('regimen', '=', self.regimen)]
        productos = productos.search(condiciones_busqueda)
        return productos

    def get_productos_consolidado(self, productos):
        if self.regimen:
            condiciones_busqueda = [('regimen', '=', self.regimen)]
        productos = productos.search(condiciones_busqueda)
        return productos

    def get_productos_marfrig(self, productos):
        productos = productos.search([])
        return productos


    def agrupar_lineas(self, proveedor):
        if proveedor:
            info = []
            regimen = ''
            name = 'N/A'
            carpeta = 'N/A'
            if proveedor.rt_service_product_id:
                producto = proveedor.rt_service_product_id
                regimen = producto.regimen
                carpeta = (producto.rt_service_id.name if producto.rt_service_id else 'N/A SERVICE') + ' - ' + (producto.rt_carga_id.seq if producto.rt_carga_id else 'N/A SERVICE')
                name = producto.name if producto.name else producto.product_id.name
            if proveedor.rt_consol_product_id:
                producto = proveedor.rt_consol_product_id
                camion = producto.rt_carga_id.camion_id if producto.rt_carga_id.camion_id else producto.camion_id
                carga = producto.rt_carga_id if producto.rt_carga_id else ''
                if producto.regimen:
                    regimen = producto.regimen
                elif producto.camion_id:
                    regimen = producto.camion_id.regimen
                carpeta = (camion.name if camion else 'N/A CAMION') + ' - ' + (carga.name if (carga and carga.name) else 'N/A CAMION' if carga else '')
                name = producto.name if producto.name else producto.product_id.name
            if proveedor.rt_deposito_product_id:
                producto = proveedor.rt_deposito_product_id
                carpeta = producto.deposito_srv_id.name
                name = producto.name if producto.name else producto.product_id.name
            if proveedor.rt_marfrig_product_id:
                producto = proveedor.rt_marfrig_product_id
                regimen = 'expo_nat'
                carpeta = producto.mrf_srv_id.name
                name = producto.name if producto.name else producto.product_id.name

            info.append(carpeta)
            info.append(name)
            if regimen:
                info.append(regimen)
            else:
                info.append('N/A')

        return info

    def obtener_proveedores(self, proveedores, purchase_orders):
        dic_proveedor = {}
        precio = 0
        precio_proveedor = 0
        proveedor_anterior = ''
        if proveedores:
            for proveedor in proveedores:
                precio = proveedor.amount
                proveedor = proveedor.supplier_id.name
                if proveedor == proveedor_anterior:
                    precio_proveedor += precio
                else:
                    if proveedor_anterior:
                        dic_proveedor[proveedor_anterior] = precio_proveedor
                    precio_proveedor = precio
                proveedor_anterior = proveedor

        dic_proveedor[proveedor_anterior] = precio_proveedor
        if purchase_orders:
            for po in purchase_orders:
                precio = po.amount_untaxed
                proveedor = po.partner_id.name
                if proveedor in dic_proveedor:
                    dic_proveedor[proveedor] += precio
                else:
                    dic_proveedor[proveedor] = precio

        dic_proveedor = sorted(dic_proveedor.items(), key=lambda x: x[1], reverse=True)
        return dic_proveedor

    def get_report_name(self, start=None, stop=None):
        report_name = ''
        if start and stop:
            report_name = formatters.date_fmt(start.isoformat()[:10]) + ' - ' + formatters.date_fmt(stop.isoformat()[:10])
        return report_name

    def write_page_all(self, wb=None, proveedores=None, purchase_orders=None, nombre_filtro=None, fechas=None):
        fila = 4
        columna_inicio = 7
        columna_fin = 8
        title = easyxf('font: name Calibri, bold True; alignment: horizontal left')
        total_number = easyxf('font: name Calibri; alignment: horizontal right',
                              num_format_str='#,##0.00;-#,##0.00;')
        moneda = 'Original' + ' ' + proveedores[0].currency_id.name
        ws = wb.add_sheet(moneda, cell_overwrite_ok=True)
        ws.write_merge(fila - 3, fila - 3, 0, 2, fechas, title)
        if nombre_filtro:
            ws.write_merge(fila-2, fila-2, 0, 5, nombre_filtro, title)
        ws.write_merge(fila, fila, 0, 0, "Fecha", title)
        ws.write_merge(fila, fila, 1, 3, "Carpeta", title)
        ws.write_merge(fila, fila, 4, 6, "Producto", title)
        if not self.supplier_id:
            ws.write_merge(fila, fila, columna_inicio, (columna_fin+1), "Proveedor", title)
            columna_fin += 1
            columna_inicio = columna_fin + 1
            columna_fin += 2
        if not self.regimen:
            ws.write_merge(fila, fila, columna_inicio, columna_fin, "Regimen", title)
            columna_inicio += 2
            columna_fin += 2
        ws.write_merge(fila, fila, columna_inicio, columna_inicio, "Moneda", title)
        ws.write_merge(fila, fila, (columna_inicio+1), (columna_fin+2), "Total Sin IVA", title)
        formula_total = self.posicion_total(columna_inicio)
        if proveedores:
            for proveedor in proveedores:
                info = self.agrupar_lineas(proveedor)
                fila += 1
                columna_inicio = 7
                columna_fin = 8

                if not proveedor.invoice_id:
                    lineas = easyxf('font: name Calibri; alignment: horizontal left; pattern: pattern solid, fore_colour red')
                    title_number = easyxf('font: name Calibri; alignment: horizontal right; pattern: pattern solid, fore_colour red',
                                          num_format_str='#,##0.00;-#,##0.00;')
                else:
                    lineas = easyxf('font: name Calibri; alignment: horizontal left')
                    title_number = easyxf('font: name Calibri; alignment: horizontal right',
                                          num_format_str='#,##0.00;-#,##0.00;')
                ws.write_merge(fila, fila, 0, 0, self.convertir_fecha(proveedor.service_date), lineas)
                ws.write_merge(fila, fila, 1, 3, info[0], lineas)
                ws.write_merge(fila, fila, 4, 6, info[1], lineas)
                if not self.supplier_id:
                    ws.write_merge(fila, fila, columna_inicio, (columna_fin+1), proveedor.supplier_id.name, lineas)
                    columna_fin += 1
                    columna_inicio = columna_fin + 1
                    columna_fin += 2
                if not self.regimen:
                    if info[2] != 'N/A':
                        ws.write_merge(fila, fila, columna_inicio, columna_fin, self.map_regimen()[info[2]], lineas)
                    else:
                        ws.write_merge(fila, fila, columna_inicio, columna_fin, 'N/A', lineas)
                    columna_inicio += 2
                    columna_fin += 2
                ws.write_merge(fila, fila, columna_inicio, columna_inicio, proveedor.currency_id.name, title_number)
                ws.write_merge(fila, fila, (columna_inicio + 1), (columna_fin + 2), proveedor.amount, title_number)

        if purchase_orders:
            for po in purchase_orders:
                for line in po.order_line:
                    fila += 1
                    columna_inicio = 7
                    columna_fin = 8
                    lineas = easyxf('font: name Calibri; alignment: horizontal left')
                    title_number = easyxf('font: name Calibri; alignment: horizontal right',
                                          num_format_str='#,##0.00;-#,##0.00;')
                    ws.write_merge(fila, fila, 0, 0, self.convertir_fecha(po.date_order), lineas)
                    ws.write_merge(fila, fila, 1, 3, po.name, lineas)
                    ws.write_merge(fila, fila, 4, 6, line.name if line.name else line.product_id.name, lineas)
                    if not self.supplier_id:
                        ws.write_merge(fila, fila, columna_inicio, (columna_fin + 1), po.partner_id.name, lineas)
                        columna_fin += 1
                        columna_inicio = columna_fin + 1
                        columna_fin += 2
                    if not self.regimen:
                        ws.write_merge(fila, fila, columna_inicio, columna_fin, 'N/A', lineas)
                        columna_inicio += 2
                        columna_fin += 2
                    ws.write_merge(fila, fila, columna_inicio, columna_inicio, po.currency_id.name, title_number)
                    ws.write_merge(fila, fila, (columna_inicio + 1), (columna_fin + 2), line.price_subtotal, title_number)

        fila += 1
        ultima_fila = fila
        ws.write(ultima_fila, (columna_inicio+1), "Total", title)
        primer_fila = 4
        ws.write_merge(fila, fila, (columna_fin + 1), (columna_fin + 2), Formula(formula_total % (primer_fila, ultima_fila)), total_number)

    def write_page_per_supplier(self, wb=None, proveedores=None, purchase_orders=None, nombre_filtro=None, fechas=None):
        columna_inicio = 3
        columna_fin = 4
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
        moneda = 'Proveedor Original' + ' ' + proveedores[0].currency_id.name
        title_moneda = proveedores[0].currency_id.name
        ws = wb.add_sheet(moneda, cell_overwrite_ok=True)
        ws.write_merge(0, 0, 0, 8, fechas, color)
        ws.write_merge(0, 0, 9, 11, '', color)
        if nombre_filtro:
            ws.write_merge(1, 2, 0, 8, nombre_filtro, title)
        else:
            ws.write_merge(1, 2, 0, 8, '', color)
        ws.write_merge(columna_inicio, columna_fin, 0, 0, "#", title_hashtag)
        ws.write_merge(columna_inicio, columna_fin, 1, 8, "Proveedor", title)
        ws.write_merge(1, 2, 9, 11, title_moneda, title_factu)
        ws.write_merge(columna_inicio, columna_fin, 9, 11, "Facturado (Sin Impuesto)", title_factu)
        proveedor = self.obtener_proveedores(proveedores, purchase_orders)
        if proveedor:
            for info in proveedor:
                columna_fin += 1
                ws.write_merge(columna_fin, columna_fin, 0, 0, numero, color)
                ws.write_merge(columna_fin, columna_fin, 1, 8, info[0], lineas)
                ws.write_merge(columna_fin, columna_fin, 9, 11, info[1], title_number)
                numero += 1

            ultima_fila = columna_fin + 1
            primer_fila = 4
            ws.write_merge(ultima_fila, ultima_fila, 10, 11, Formula("SUM(J%s :J%s)" % (primer_fila, (columna_fin+1))), title_number)
            ws.write_merge(ultima_fila, ultima_fila, 0, 8, '', fin)
            ws.write(ultima_fila, 9, "Total", total_precio)

    def informe_costos(self):
        # Creo el 'Libro' y su 'Pagina'
        wb = Workbook(encoding='utf-8')
        start, stop = self.convert_date_to_datetime(self.start, self.stop)
        proveedores_pesos, proveedores_dolares = self.get_proveedor(start, stop)
        purchase_order_pesos, purchase_order_dolares = self.get_purchase_order(start, stop)
        lista_proveedores = [(proveedores_pesos, purchase_order_pesos), (proveedores_dolares, purchase_order_dolares)]
        fechas = str(start)[:10] + ' / ' + str(stop)[:10]
        nombre_filtro = self.obtener_nombre_filtrado()
        for proveedores in lista_proveedores:
            if proveedores[0] or proveedores[1]:
                if self.tipo_informe == 'all':
                    file_name = 'Informe Costos Todo - %s.xls' % self.get_report_name(start=self.start, stop=self.stop)
                    self.write_page_all(wb, proveedores[0], proveedores[1], nombre_filtro, fechas)
                if self.tipo_informe == 'summary':
                    file_name = 'Informe Costos Resumen - %s.xls' % self.get_report_name(start=self.start, stop=self.stop)
                    self.write_page_per_supplier(wb, proveedores[0], proveedores[1], nombre_filtro, fechas)

        if lista_proveedores == [([], []), ([], [])]:
            if self.supplier_id or self.regimen:
                raise Warning('No se encontraron lineas con esos filtros')
            else:
                raise Warning('No se encontraron lineas')

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
