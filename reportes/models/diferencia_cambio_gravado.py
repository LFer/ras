from odoo import models, fields, api
import string
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning
import xlsxwriter
import ast
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
    _name = 'diferencia.cambio.gravado'

    def convertir_fecha(self, fecha):
        string = ''
        if fecha:
            string = fecha.strftime("%d/%m/%Y")

        return string

    def obtener_tipo_cambio(self, fecha):
        tipo_cambio = self.env['res.currency.rate'].search([('name', '<=', fecha), ('currency_id', '=', 2)], limit=1)
        return tipo_cambio.rate

    def str_to_date(self, fecha):
        date = datetime.strptime(fecha, '%Y-%m-%d')
        string = self.convertir_fecha(date)

        return string

    def get_month_name(self, contador):
        months = ["Unknown",
                  "Enero",
                  "Febrero",
                  "Marzo",
                  "Abril",
                  "Mayo",
                  "Junio",
                  "Julio",
                  "Agosto",
                  "Septiembre",
                  "Octubre",
                  "Noviembre",
                  "Diciembre"]

        return months[contador]

    def obtener_numero_recibo(self, factura):
        recipe_number = ''
        if factura.payment_ids:
            for recibo in factura.payment_ids:
                if recipe_number:
                    recipe_number += ' / ' + recibo.communication
                else:
                    recipe_number = recibo.communication
        elif factura.payment_move_line_ids:
            for recibo in factura.payment_move_line_ids:
                if recipe_number:
                    recipe_number += ' / ' + recibo.ref
                else:
                    recipe_number = recibo.ref

        return recipe_number

    def info_factura(self, factura, pago):
        pago_date = ''
        ref = ''
        recibo = self.env['account.payment']
        move_line = self.env['account.move.line']
        if pago.__class__ == recibo.__class__:
            pago_date = pago.payment_date
            ref = pago.communication
        if pago.__class__ == move_line.__class__:
            pago_date = pago.date
            ref = pago.ref
        data = []
        data.append(factura.partner_id.name)
        data.append(self.str_to_date(factura.fe_FechaHoraFirma[:10]) if factura.fe_FechaHoraFirma else 'NO FECHA')
        data.append(factura.fe_DocNro)
        data.append(factura.amount_total)
        data.append(factura.amount_untaxed)
        data.append(self.convertir_fecha(pago_date))
        data.append(ref)
        data.append(self.obtener_tipo_cambio(factura.date_invoice))
        data.append(self.obtener_tipo_cambio(pago_date))

        return data

    def get_facturas_ordenados_por_mes(self):
        tax_gravado = self.env['account.tax'].search([('amount', '=', 22)])
        lineas_factura = self.env['account.invoice.line'].search([('invoice_line_tax_ids', 'in', tax_gravado.ids)])
        facturas = self.env['account.invoice'].search([('state', '=', 'paid'), ('currency_id', '=', 2), ('invoice_line_ids', 'in', lineas_factura.ids), ('type', 'in', ['out_invoice', 'out_refund'])], order='fe_FechaHoraFirma')
        facturas_ordenados_por_mes = []
        facturas_enero = []
        facturas_febrero = []
        facturas_marzo = []
        facturas_abril = []
        facturas_mayo = []
        facturas_junio = []
        facturas_julio = []
        facturas_agosto = []
        facturas_setiembre = []
        facturas_octubre = []
        facturas_noviembre = []
        facturas_diciembre = []
        sin_factura = []
        # datetime(year, month, day, hour, minute, second, microsecond)
        inicio_enero = date(2019, 1, 1)
        fin_enero = date(2019, 1, 31)

        inicio_febrero = date(2019, 2, 1)
        fin_febrero = date(2019, 2, 28)

        inicio_marzo = date(2019, 3, 1)
        fin_marzo = date(2019, 3, 31)

        inicio_abril = date(2019, 4, 1)
        fin_abril = date(2019, 4, 30)

        inicio_mayo = date(2019, 5, 1)
        fin_mayo = date(2019, 5, 31)

        inicio_junio = date(2019, 6, 1)
        fin_junio = date(2019, 6, 30)

        inicio_julio = date(2019, 7, 1)
        fin_julio = date(2019, 7, 31)

        inicio_agosto = date(2019, 8, 1)
        fin_agosto = date(2019, 8, 31)

        inicio_setiembre = date(2019, 9, 1)
        fin_setiembre = date(2019, 9, 30)

        inicio_octubre = date(2019, 10, 1)
        fin_octubre = date(2019, 10, 31)

        inicio_noviembre = date(2019, 11, 1)
        fin_noviembre = date(2019, 11, 30)

        inicio_diciembre = date(2019, 12, 1)
        fin_diciembre = date(2019, 12, 31)

        for factura in facturas:
            if factura.payment_ids:
                for pago in factura.payment_ids:
                    if pago.payment_date:
                        fecha = pago.payment_date
                        if fecha >= inicio_enero and fecha <= fin_enero:
                            info_factura = self.info_factura(factura, pago)
                            facturas_enero.append(info_factura)

                        if fecha >= inicio_febrero and fecha <= fin_febrero:
                            info_factura = self.info_factura(factura, pago)
                            facturas_febrero.append(info_factura)

                        if fecha >= inicio_marzo and fecha <= fin_marzo:
                            info_factura = self.info_factura(factura, pago)
                            facturas_marzo.append(info_factura)

                        if fecha >= inicio_abril and fecha <= fin_abril:
                            info_factura = self.info_factura(factura, pago)
                            facturas_abril.append(info_factura)

                        if fecha >= inicio_mayo and fecha <= fin_mayo:
                            info_factura = self.info_factura(factura, pago)
                            facturas_mayo.append(info_factura)

                        if fecha >= inicio_junio and fecha <= fin_junio:
                            info_factura = self.info_factura(factura, pago)
                            facturas_junio.append(info_factura)

                        if fecha >= inicio_julio and fecha <= fin_julio:
                            info_factura = self.info_factura(factura, pago)
                            facturas_julio.append(info_factura)

                        if fecha >= inicio_agosto and fecha <= fin_agosto:
                            info_factura = self.info_factura(factura, pago)
                            facturas_agosto.append(info_factura)

                        if fecha >= inicio_setiembre and fecha <= fin_setiembre:
                            info_factura = self.info_factura(factura, pago)
                            facturas_setiembre.append(info_factura)

                        if fecha >= inicio_octubre and fecha <= fin_octubre:
                            info_factura = self.info_factura(factura, pago)
                            facturas_octubre.append(info_factura)

                        if fecha >= inicio_noviembre and fecha <= fin_noviembre:
                            info_factura = self.info_factura(factura, pago)
                            facturas_noviembre.append(info_factura)

                        if fecha >= inicio_diciembre and fecha <= fin_diciembre:
                            info_factura = self.info_factura(factura, pago)
                            facturas_diciembre.append(info_factura)

            elif factura.payment_move_line_ids:
                for recibo in factura.payment_move_line_ids:
                    if recibo.date:
                        if not recibo.payment_id:
                            fecha = recibo.date
                            pago = recibo
                        else:
                            pago = recibo.payment_id
                            fecha = pago.payment_date

                        if fecha >= inicio_enero and fecha <= fin_enero:
                            info_factura = self.info_factura(factura, pago)
                            facturas_enero.append(info_factura)

                        if fecha >= inicio_febrero and fecha <= fin_febrero:
                            info_factura = self.info_factura(factura, pago)
                            facturas_febrero.append(info_factura)

                        if fecha >= inicio_marzo and fecha <= fin_marzo:
                            info_factura = self.info_factura(factura, pago)
                            facturas_marzo.append(info_factura)

                        if fecha >= inicio_abril and fecha <= fin_abril:
                            info_factura = self.info_factura(factura, pago)
                            facturas_abril.append(info_factura)

                        if fecha >= inicio_mayo and fecha <= fin_mayo:
                            info_factura = self.info_factura(factura, pago)
                            facturas_mayo.append(info_factura)

                        if fecha >= inicio_junio and fecha <= fin_junio:
                            info_factura = self.info_factura(factura, pago)
                            facturas_junio.append(info_factura)

                        if fecha >= inicio_julio and fecha <= fin_julio:
                            info_factura = self.info_factura(factura, pago)
                            facturas_julio.append(info_factura)

                        if fecha >= inicio_agosto and fecha <= fin_agosto:
                            info_factura = self.info_factura(factura, pago)
                            facturas_agosto.append(info_factura)

                        if fecha >= inicio_setiembre and fecha <= fin_setiembre:
                            info_factura = self.info_factura(factura, pago)
                            facturas_setiembre.append(info_factura)

                        if fecha >= inicio_octubre and fecha <= fin_octubre:
                            info_factura = self.info_factura(factura, pago)
                            facturas_octubre.append(info_factura)

                        if fecha >= inicio_noviembre and fecha <= fin_noviembre:
                            info_factura = self.info_factura(factura, pago)
                            facturas_noviembre.append(info_factura)

                        if fecha >= inicio_diciembre and fecha <= fin_diciembre:
                            info_factura = self.info_factura(factura, pago)
                            facturas_diciembre.append(info_factura)

        facturas_ordenados_por_mes.append(sorted(facturas_enero, key=itemgetter(0, 5)))
        facturas_ordenados_por_mes.append(sorted(facturas_febrero, key=itemgetter(0, 5)))
        facturas_ordenados_por_mes.append(sorted(facturas_marzo, key=itemgetter(0, 5)))
        facturas_ordenados_por_mes.append(sorted(facturas_abril, key=itemgetter(0, 5)))
        facturas_ordenados_por_mes.append(sorted(facturas_mayo, key=itemgetter(0, 5)))
        facturas_ordenados_por_mes.append(sorted(facturas_junio, key=itemgetter(0, 5)))
        facturas_ordenados_por_mes.append(sorted(facturas_julio, key=itemgetter(0, 5)))
        facturas_ordenados_por_mes.append(sorted(facturas_agosto, key=itemgetter(0, 5)))
        facturas_ordenados_por_mes.append(sorted(facturas_setiembre, key=itemgetter(0, 5)))
        facturas_ordenados_por_mes.append(sorted(facturas_octubre, key=itemgetter(0, 5)))
        facturas_ordenados_por_mes.append(sorted(facturas_noviembre, key=itemgetter(0, 5)))
        facturas_ordenados_por_mes.append(sorted(facturas_diciembre, key=itemgetter(0, 5)))
        return facturas_ordenados_por_mes

    def write_page_all(self, wb=None, facturas=None, contador=None):
        fila = 0
        month = self.get_month_name(contador)
        title = easyxf('font: name Calibri, bold True; alignment: horizontal left')
        title_number = easyxf('font: name Calibri; alignment: horizontal right',
                              num_format_str='#,##0.00;-#,##0.00;')
        lineas = easyxf('font: name Calibri; alignment: horizontal left')
        moneda = month + ' ' + facturas[0][5][6:]
        ws = wb.add_sheet(moneda, cell_overwrite_ok=True)
        ws.write_merge(0, fila, 0, 3, "Cliente a Facturar", title)
        ws.write_merge(0, fila, 4, 4, "Fecha", title)
        ws.write_merge(0, fila, 5, 5, "Nº", title)
        ws.write_merge(0, fila, 6, 7, "Monto USD  c/iva", title)
        ws.write_merge(0, fila, 8, 9, "Monto USD  s/iva", title)
        ws.write_merge(0, fila, 10, 10, "Fecha de Cobro", title)
        ws.write_merge(0, fila, 11, 11, "Nº Recibo", title)
        ws.write_merge(0, fila, 12, 12, "TC VTA", title)
        ws.write_merge(0, fila, 13, 13, "TC Cob", title)
        ws.write_merge(0, fila, 14, 14, "Variacion", title)
        ws.write_merge(0, fila, 15, 15, "L*F", title)
        if facturas:
            for info in facturas:
               fila += 1
               ws.write_merge(fila, fila, 0, 3, info[0], lineas)
               ws.write_merge(fila, fila, 4, 4, info[1], lineas)
               ws.write_merge(fila, fila, 5, 5, info[2], lineas)
               ws.write_merge(fila, fila, 6, 7, info[3], title_number)
               ws.write_merge(fila, fila, 8, 9, info[4], title_number)
               ws.write_merge(fila, fila, 10, 10, info[5], lineas)
               ws.write_merge(fila, fila, 11, 11, info[6], lineas)
               ws.write_merge(fila, fila, 12, 12, info[7], title_number)
               ws.write_merge(fila, fila, 13, 13, info[8], title_number)
               ws.write_merge(fila, fila, 14, 14, Formula('N%s-M%s' % (fila+1, fila+1)), title_number)
               ws.write_merge(fila, fila, 15, 15, Formula('O%s*I%s' % (fila+1, fila+1)), title_number)


            ultima_fila = fila + 1
            fila += 2
            ws.write_merge(fila, fila, 13, 14, 'Diferencia de cambio', title)
            ws.write_merge(fila, fila, 15, 15, Formula("SUM(P2 :P%s)" % (fila-1)), title_number)
            ws.write_merge((fila + 1), (fila + 1), 14, 14, 'IVA', title)
            ws.write_merge((fila + 1), (fila + 1), 15, 15, Formula("P%s*0.22" % (fila + 1)), title_number)
            ws.write_merge((fila + 2), (fila + 2), 14, 14, 'Deudores', title)
            ws.write_merge((fila + 2), (fila + 2), 15, 15, Formula("P%s+P%s" % (fila+1, fila+2)), title_number)


    def informe_diferencia_cambio_gravado(self):
        # Creo el 'Libro' y su 'Pagina'
        file_name = 'Diferencia Cambio Gravado.xls'
        fp = BytesIO()
        wb = Workbook(encoding='utf-8')
        facturas_total = self.get_facturas_ordenados_por_mes()
        contador = 1
        if not facturas_total:
                raise Warning('No se encontraron facturas')
        for facturas in facturas_total:
            if facturas:
                self.write_page_all(wb, facturas, contador)
            contador += 1

        wb.save(fp)
        fp.seek(0)
        data = fp.read()
        fp.close()
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