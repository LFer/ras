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

class ReportesProveedorCrudo(models.Model):
    _inherit = 'informe.costos'

    def obtener_factura_po(self, po):
        numero_factura = 'No Factura'
        if po.invoice_ids:
            for factura in po.invoice_ids:
                if factura:
                    if factura.number:
                        if numero_factura == 'No Validada' or numero_factura == 'No Factura':
                            numero_factura = str(factura.number)
                        else:
                            numero_factura += ' - ' + str(factura.number)
                    else:
                        numero_factura = 'No Validada'
                else:
                    numero_factura = 'No Factura'

        return numero_factura

    def obtener_factura_cliente(self, prod):
        lineas = []
        numero_factura = 'No Factura'
        productos_service = self.env['rt.service.productos']
        productos_consolidado = self.env['producto.servicio.camion']
        productos_deposito = self.env['deposito.service.products']
        if prod.__class__ == productos_service.__class__:
            lineas = self.env['account.invoice.line'].search([('rt_service_product_id', '=', prod.id)])
        if prod.__class__ == productos_consolidado.__class__:
            lineas = self.env['account.invoice.line'].search([('consolidado_service_product_id', '=', prod.id)])
        if prod.__class__ == productos_deposito.__class__:
            lineas = self.env['account.invoice.line'].search([('product_deposito_srv_id', '=', prod.id)])

        factura = self.env['account.invoice'].search([('service_marfrig_ids', '=', prod.id)])
        for linea in lineas:
            if linea.invoice_id:
                if linea.invoice_id.fe_Serie:
                    if not numero_factura or numero_factura == 'No Validada' or numero_factura == 'No Factura':
                        numero_factura = str(linea.invoice_id.fe_Serie) + '-' + str(linea.invoice_id.fe_DocNro)
                    else:
                        numero_factura += ' / ' + str(linea.invoice_id.fe_Serie) + '-' + str(linea.invoice_id.fe_DocNro)
                else:
                    numero_factura = 'No Validada'

        if factura:
            if factura.fe_Serie:
                if not numero_factura or numero_factura == 'No Validada' or numero_factura == 'No Factura':
                    numero_factura = str(factura.fe_Serie) + '-' + str(factura.fe_DocNro)
                else:
                    numero_factura += ' / ' + str(factura.fe_Serie) + '-' + str(factura.fe_DocNro)
            else:
                numero_factura = 'No Validada'


        return numero_factura

    def obtener_factura_proveedor(self, prod):
        lineas = []
        numero_factura = 'NO COSTO'
        productos_service = self.env['rt.service.productos']
        productos_consolidado = self.env['producto.servicio.camion']
        productos_deposito = self.env['deposito.service.products']
        productos_marfrig = self.env['marfrig.service.products']
        if prod.__class__ == productos_service.__class__:
            lineas = self.env['rt.service.product.supplier'].search([('rt_service_product_id', '=', prod.id)])
        if prod.__class__ == productos_consolidado.__class__:
            lineas = self.env['rt.service.product.supplier'].search([('rt_consol_product_id', '=', prod.id)])
        if prod.__class__ == productos_deposito.__class__:
            lineas = self.env['rt.service.product.supplier'].search([('rt_deposito_product_id', '=', prod.id)])
        if prod.__class__ == productos_marfrig.__class__:
            lineas = self.env['rt.service.product.supplier'].search([('rt_marfrig_product_id', '=', prod.id)])
        for linea in lineas:
            if linea.invoice_id:
                if linea.invoice_id.number:
                    if numero_factura == 'No Validada' or numero_factura == 'No Factura' or numero_factura == 'NO COSTO':
                        numero_factura = str(linea.invoice_id.number)
                    else:
                        numero_factura += ' - ' + str(linea.invoice_id.number)
                else:
                    numero_factura = 'No Validada'
            else:
                numero_factura = 'No Factura'

        return numero_factura

    def get_proveedores_crudo(self, productos_service, productos_consolidado, productos_marfrig, productos_deposito, purchase_order):
        proveedores_dolares = []
        proveedores_pesos = []
        for prod in productos_service:
            data = []
            data.append(prod.start)
            data.append((prod.rt_service_id.name if prod.rt_service_id else 'N/A SERVICE') + ' - ' + (prod.rt_carga_id.seq if prod.rt_carga_id else 'N/A SERVICE'))
            data.append(prod.name)
            data.append(prod.regimen if prod.regimen else 'N/A')
            data.append(prod.supplier_id.name)
            data.append(prod.valor_compra_currency_id.name)
            data.append(prod.valor_compra)
            if prod.rt_service_id and prod.rt_service_id.state in ['draft', 'confirm']:
                data.append('Carpeta no Facturada')
            else:
                data.append(self.obtener_factura_proveedor(prod))
            data.append(self.obtener_factura_cliente(prod))
            if prod.valor_compra_currency_id.name == 'UYU':
                proveedores_pesos.append(data)
            if prod.valor_compra_currency_id.name == 'USD':
                proveedores_dolares.append(data)

        for prod in productos_marfrig:
            data = []
            data.append(prod.start)
            data.append(prod.mrf_srv_id.name if prod.mrf_srv_id else 'N/A')
            data.append(prod.name)
            data.append('expo_nat')
            data.append(prod.supplier_id.name)
            data.append(prod.valor_compra_currency_id.name)
            data.append(prod.valor_compra)
            data.append(self.obtener_factura_proveedor(prod))
            data.append(self.obtener_factura_cliente(prod))
            if prod.valor_compra_currency_id.name == 'UYU':
                proveedores_pesos.append(data)
            if prod.valor_compra_currency_id.name == 'USD':
                proveedores_dolares.append(data)

        for prod in productos_deposito:
            data = []
            data.append(prod.start)
            data.append(prod.deposito_srv_id.name if prod.deposito_srv_id else 'N/A DEPOSITO')
            data.append(prod.name)
            data.append('N/A')
            data.append(prod.supplier_id.name)
            data.append(prod.valor_compra_currency_id.name)
            data.append(prod.valor_compra)
            data.append(self.obtener_factura_proveedor(prod))
            data.append(self.obtener_factura_cliente(prod))
            if prod.valor_compra_currency_id.name == 'UYU':
                proveedores_pesos.append(data)
            if prod.valor_compra_currency_id.name == 'USD':
                proveedores_dolares.append(data)

        for camion in productos_consolidado:
            for prod in camion.productos_servicios_camion_ids:
                if prod.supplier_id and prod.valor_compra != 0:
                    data = []
                    data.append(camion.start_datetime)
                    data.append(camion.name if camion.name else 'N/A CAMION')
                    data.append(prod.name if prod.name else prod.product_id.name)
                    data.append(camion.regimen if camion.regimen else 'N/A')
                    data.append(prod.supplier_id.name)
                    data.append(prod.valor_compra_currency_id.name)
                    data.append(prod.valor_compra)
                    data.append(self.obtener_factura_proveedor(prod))
                    data.append(self.obtener_factura_cliente(prod))
                    if prod.valor_compra_currency_id.name == 'UYU':
                        proveedores_pesos.append(data)
                    if prod.valor_compra_currency_id.name == 'USD':
                        proveedores_dolares.append(data)
            for carga in camion.cargas_ids:
                for prod in carga.producto_servicio_carga_ids:
                    if prod.supplier_id and prod.valor_compra != 0:
                        data = []
                        data.append(camion.start_datetime)
                        data.append((camion.name if camion.name else 'N/A CAMION') + ' - ' + (carga.name if carga.name else 'N/A CAMION'))
                        data.append(prod.name if prod.name else prod.product_id.name)
                        data.append(carga.regimen if carga.regimen else 'N/A')
                        data.append(prod.supplier_id.name)
                        data.append(prod.valor_compra_currency_id.name)
                        data.append(prod.valor_compra)
                        data.append(self.obtener_factura_proveedor(prod))
                        data.append(self.obtener_factura_cliente(prod))
                        if prod.valor_compra_currency_id.name == 'UYU':
                            proveedores_pesos.append(data)
                        if prod.valor_compra_currency_id.name == 'USD':
                            proveedores_dolares.append(data)

        for po in purchase_order:
            for compra in po.order_line:
                data = []
                data.append(po.date_order)
                data.append(po.name)
                data.append(compra.name)
                data.append('N/A')
                data.append(po.partner_id.name)
                data.append(po.currency_id.name)
                data.append(compra.price_subtotal)
                data.append(self.obtener_factura_po(po))
                data.append('')
                if po.currency_id.name == 'UYU':
                    proveedores_pesos.append(data)
                if po.currency_id.name == 'USD':
                    proveedores_dolares.append(data)

        proveedores_pesos = sorted(proveedores_pesos, key=itemgetter(4, 0))
        proveedores_dolares = sorted(proveedores_dolares, key=itemgetter(4, 0))
        return [proveedores_pesos, proveedores_dolares]

    def get_productos_service_crudo(self, start, stop):
        productos_service = self.env['rt.service.productos']
        productos = productos_service.search([('supplier_id', '!=', False), ('start', '>=', start), ('start', '<=', stop), ('valor_compra', '!=', 0)])
        return productos

    def get_productos_consolidado_crudo(self, start, stop):
        camion = self.env['carpeta.camion'].search([('start_datetime', '>=', start), ('start_datetime', '<=', stop)])
        # carga = self.env['carga.camion'].search([('camion_id', 'in', camion.ids)])
        # productos_consolidado = self.env['producto.servicio.camion']
        # productos = productos_consolidado.search([('supplier_id', '=', True), ('valor_compra', '!=', 0),])
        return camion

    def get_productos_marfrig_crudo(self, start, stop):
        productos_marfrig = self.env['marfrig.service.products']
        productos = productos_marfrig.search([('supplier_id', '!=', False), ('start', '>=', start), ('start', '<=', stop), ('valor_compra', '!=', 0)])
        return productos

    def get_productos_deposito_crudo(self, start, stop):
        productos_deposito = self.env['deposito.service.products']
        productos = productos_deposito.search(
            [('supplier_id', '!=', False), ('start', '>=', start), ('start', '<=', stop), ('valor_compra', '!=', 0)])
        return productos

    def get_purchase_order_crudo(self, start, stop):
        purchase_order = self.env['purchase.order'].search([('date_order', '>=', start), ('date_order', '<=', stop)])

        return purchase_order

    def get_proveedor_crudo(self, start, stop):
        productos_service = self.get_productos_service_crudo(start, stop)
        productos_consolidado = self.get_productos_consolidado_crudo(start, stop)
        productos_marfrig = self.get_productos_marfrig_crudo(start, stop)
        productos_deposito = self.get_productos_deposito_crudo(start, stop)
        purchase_order = self.get_purchase_order_crudo(start, stop)
        lista_proveedores = self.get_proveedores_crudo(productos_service, productos_consolidado, productos_marfrig, productos_deposito, purchase_order)

        return lista_proveedores

    def write_page_all_crudo(self, wb=None, proveedores=None, fechas=None):
        fila = 4
        lineas = easyxf('font: name Calibri; alignment: horizontal left')
        factu = easyxf('font: name Calibri; alignment: horizontal right')
        title = easyxf('font: name Calibri, bold True; alignment: horizontal left')
        total_number = easyxf('font: name Calibri; alignment: horizontal right',
                              num_format_str='#,##0.00;-#,##0.00;')
        title_number = easyxf('font: name Calibri; alignment: horizontal right',
                              num_format_str='#,##0.00;-#,##0.00;')
        moneda = proveedores[0][5]
        ws = wb.add_sheet(moneda, cell_overwrite_ok=True)
        ws.write_merge(fila - 3, fila - 3, 0, 2, fechas, title)
        ws.write_merge(fila, fila, 0, 0, "Fecha", title)
        ws.write_merge(fila, fila, 1, 3, "Carpeta", title)
        ws.write_merge(fila, fila, 4, 6, "Producto", title)
        ws.write_merge(fila, fila, 7, 9, "Proveedor", title)
        ws.write_merge(fila, fila, 10, 11, "Regimen", title)
        ws.write_merge(fila, fila, 12, 12, "Moneda", title)
        ws.write_merge(fila, fila, 13, 15, "Monto Proveedor", title)
        ws.write_merge(fila, fila, 16, 17, "Nº Fac Proveedor", title)
        ws.write_merge(fila, fila, 18, 19, "Nº Fac Cliente", title)
        if proveedores:
            for proveedor in proveedores:
                fila += 1
                ws.write_merge(fila, fila, 0, 0, self.convertir_fecha(proveedor[0]), lineas)
                ws.write_merge(fila, fila, 1, 3, proveedor[1], lineas)
                ws.write_merge(fila, fila, 4, 6, proveedor[2], lineas)
                ws.write_merge(fila, fila, 7, 9, proveedor[4], lineas)
                if proveedor[3] != 'N/A':
                    ws.write_merge(fila, fila, 10, 11, self.map_regimen()[proveedor[3]], lineas)
                else:
                    ws.write_merge(fila, fila, 10, 11, proveedor[3], lineas)
                ws.write_merge(fila, fila, 12, 12, proveedor[5], lineas)
                ws.write_merge(fila, fila, 13, 15, proveedor[6], title_number)
                ws.write_merge(fila, fila, 16, 17, proveedor[7], factu)
                ws.write_merge(fila, fila, 18, 19, proveedor[8], factu)

        fila += 1
        ultima_fila = fila
        ws.write(ultima_fila, 13, "Total", title)
        primer_fila = 4
        ws.write_merge(fila, fila, 14, 15, Formula("SUM(N4 :N%s)" % (ultima_fila)), total_number)

    def informe_proveedor_crudo(self):
        # Creo el 'Libro' y su 'Pagina'
        file_name = 'Informe Proveedores Todo Crudo - %s.xls' % self.get_report_name(start=self.start, stop=self.stop)
        wb = Workbook(encoding='utf-8')
        start, stop = self.convert_date_to_datetime(self.start, self.stop)
        lista_proveedores = self.get_proveedor_crudo(start, stop)
        fechas = str(start)[:10] + ' / ' + str(stop)[:10]
        for proveedores in lista_proveedores:
            self.write_page_all_crudo(wb, proveedores, fechas)

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