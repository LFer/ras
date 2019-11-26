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


class ComisionChoferes(models.Model):
    _name = "comision.choferes"
    _description = "Reporte Comision de Choferes"

    name = fields.Char(string='Nombre')
    inicio = fields.Date(string='Desde', required=True)
    fin = fields.Date(string='Hasta', required=True)
    archivo = fields.Binary(string="placeholder")
    driver_id = fields.Many2one(comodel_name='hr.employee', string='Chofer')
    categ_id = fields.Many2one(comodel_name='hr.job', string='Categoria')
    operation_type = fields.Selection([('national', 'Nacional'), ('international', 'Internacional')], string='Operativa')

    def convert_date_to_datetime(self, start, stop):
        if start and stop:
            start_datetime = datetime.combine(start, datetime.min.time()) + timedelta(hours=3)
            stop_datetime = datetime.combine(stop, datetime.min.time()) + timedelta(days=1)
            user_tz = self.env.user.tz or pytz.utc
            local = pytz.timezone(user_tz)
            # start_datetime_normalised = datetime.strftime(pytz.utc.localize(start_datetime).astimezone(local), '%Y-%m-%d %H:%M:%S')
            # stop_datetime_normalised = datetime.strftime(pytz.utc.localize(stop_datetime).astimezone(local), '%Y-%m-%d %H:%M:%S')

        return start_datetime, stop_datetime

    def get_sheet_by_name(self, book, name):
        """Get a sheet by name from xlwt.Workbook, a strangely missing method.
        Returns None if no sheet with the given name is present.
        """
        # Note, we have to use exceptions for flow control because the
        # xlwt API is broken and gives us no other choice.
        try:
            for idx in itertools.count():
                sheet = book.get_sheet(idx)
                if sheet.name == name:
                    return sheet
        except IndexError:
            return False

    def get_lineas(self, start, stop, driver, categ, operation_type):

        lineas = False
        if not driver and not categ:
            lineas = self.env['rt.service.productos'].search([('start', '>=', start), ('stop', '<=', stop), ('driver_id', '!=', False), ('operation_type', '=', operation_type)], order='start')
        if driver:
            lineas = self.env['rt.service.productos'].search([('start', '>=', start), ('stop', '<=', stop), ('driver_id', '=', driver.id), ('operation_type', '=', operation_type)], order='start')
        if categ:
            driver_categ = self.env['hr.employee'].search([('job_id', '=', categ.id)]).ids
            lineas = self.env['rt.service.productos'].search([('start', '>=', start), ('stop', '<=', stop), ('driver_id', 'in', driver_categ), ('operation_type', '=', operation_type)], order='start')

        return lineas

    def get_lineas_m(self, start, stop, driver, categ, operation_type):
        lineas = False
        if operation_type == 'international':
            return lineas
        if not driver and not categ:
            lineas = self.env['marfrig.service.products'].search([('start', '>=', start), ('stop', '<=', stop), ('driver_id', '!=', False)], order='start')
        if driver:
            lineas = self.env['marfrig.service.products'].search([('start', '>=', start), ('stop', '<=', stop), ('driver_id', '=', driver.id)], order='start')
        if categ:
            driver_categ = self.env['hr.employee'].search([('job_id', '=', categ.id)]).ids
            lineas = self.env['marfrig.service.products'].search([('start', '>=', start), ('stop', '<=', stop), ('driver_id', 'in', driver_categ)], order='start')

        return lineas

    def lines_consol(self, start, stop, driver, categ, operation_type):
        lineas = False
        if operation_type == 'national':
            return lineas
        if not driver and not categ:
            lineas = self.env['carpeta.camion'].search([('start_datetime', '>=', start), ('start_datetime', '<=', stop), ('driver_id', '!=', False)], order='start_datetime')
        if driver:
            lineas = self.env['carpeta.camion'].search([('start_datetime', '>=', start), ('start_datetime', '<=', stop), ('driver_id', '=', driver.id)], order='start_datetime')
        if categ:
            driver_categ = self.env['hr.employee'].search([('job_id', '=', categ.id)]).ids
            lineas = self.env['carpeta.camion'].search([('start_datetime', '>=', start), ('start_datetime', '<=', stop), ('driver_id', 'in', driver_categ)], order='start_datetime')
        return lineas

    def get_lineas_deposito(self, start, stop, driver, categ, operation_type):
        lineas = False
        if operation_type == 'international':
            return lineas
        if not driver and not categ:
            lineas = self.env['deposito.service.products'].search([('start', '>=', start), ('stop', '<=', stop), ('driver_id', '!=', False)], order='start')
        if driver:
            lineas = self.env['deposito.service.products'].search([('start', '>=', start), ('stop', '<=', stop), ('driver_id', '=', driver.id)], order='start')
        if categ:
            driver_categ = self.env['hr.employee'].search([('job_id', '=', categ.id)]).ids
            lineas = self.env['deposito.service.products'].search([('start', '>=', start), ('stop', '<=', stop), ('driver_id', 'in', driver_categ)], order='start')

        return lineas

    def get_drivers_ids(self, lines=None):
        driver_ids = []

        for line in lines:
            driver_ids.append(line.driver_id.id)
        return set(driver_ids)
        # return self.env['hr.employee'].search([]).ids

    def get_lines_by_driver(self, lines=None, driver=None):
        lines_obj = self.env['rt.service.productos']
        _ids = []
        driver_name = self.env['hr.employee'].browse(driver).name
        for line in lines:
            if line.driver_id.name == driver_name:
                _ids.append(line.id)
        return lines_obj.browse(_ids)

    def get_lines_by_driver_m(self, lines=None, driver=None):
        lines_obj = self.env['marfrig.service.products']
        _ids = []
        driver_name = self.env['hr.employee'].browse(driver).name
        for line in lines:
            if line.driver_id.name == driver_name:
                _ids.append(line.id)
            else:
                return False
        return lines_obj.browse(_ids)

    def get_dua(self, line):
        dua = ''
        if line._name == 'marfrig.service.products':
            dua = 'N/A'
            return dua
        if line._name == 'carpeta.camion':
            dua = 'N/A'
            return dua
        if line.rt_service_id.dua_type == 'cabezal':
            carpeta = line.rt_service_id
            dua = carpeta.dua_aduana + '-' if carpeta.dua_aduana else ''
            dua += carpeta.dua_anio + '-' if carpeta.dua_anio else ''
            dua += carpeta.dua_numero if carpeta.dua_numero else ''
        elif line.rt_service_id.dua_type == 'linea':
            carga = line.rt_carga_id
            if not carga.multiple_dua:
                dua = carga.dua_aduana + '-' if carga.dua_aduana else ''
                dua += carga.dua_anio + '-' if carga.dua_anio else ''
                dua += carga.dua_numero if carga.dua_numero else ''
            if carga.multiple_dua:
                dua = ''
                for duas in carga.duas_ids:
                    if dua:
                        dua += ' / '
                        dua += duas.dua_aduana + '-' + duas.dua_anio + '-' + duas.dua_numero
                    else:
                        dua += duas.dua_aduana + '-' + duas.dua_anio + '-' + duas.dua_numero
        else:
            dua = ' '
        return dua

    def get_partner_to_invoice_name(self, line=None):
        parter_name = ''
        if line:
            if line._name == 'marfrig.service.products':
                parter_name = line.mrf_srv_id.partner_invoice_id.name
            if line._name == 'rt.service.productos':
                parter_name = line.partner_invoice_id.name if line.partner_invoice_id else line.rt_service_id.partner_invoice_id.name if line.rt_service_id else line.rt_carga_id.partner_invoice_id.name if line.rt_carga_id else 'NOT FOUND'
            if line._name == 'carpeta.camion':
                parter_name = line.partner_id.name
            if line._name == 'deposito.service.products':
                parter_name = line.partner_invoice_id.name

        return parter_name

    def get_ref_carpeta(self, line=None):
        ref_carpeta = ''
        if line:
            if line._name == 'marfrig.service.products':
                ref_carpeta = line.mrf_srv_id.name
            if line._name == 'rt.service.productos':
                ref_carpeta = line.rt_service_id.name if line.rt_service_id else 'NOT FOUND'

            if line._name == 'carpeta.camion':
                ref_carpeta = line.name
            if line._name == 'deposito.service.products':
                ref_carpeta = line.deposito_srv_id.name
        return ref_carpeta

    def get_container_number(self, line=None):
        container_number = ''
        if line:
            if line._name == 'marfrig.service.products':
                container_number = line.mrf_srv_id.container_number
            if line._name == 'rt.service.productos':
                container_number = line.rt_carga_id.container_number if line.rt_carga_id.load_type == 'contenedor' else 'N/A'

            if line._name == 'carpeta.camion':
                container_number = 'N/A'

        return container_number

    def get_product_name(self, line=None):
        product_name = ''
        if line:
            if line._name == 'marfrig.service.products':
                product_name = line.product_id.name
            if line._name == 'rt.service.productos':
                product_name = line.product_id.name
            if line._name == 'carpeta.camion':
                product_name = 'N/A'
            if line._name == 'deposito.service.products':
                product_name = line.product_id.name if line.product_id else 'N/A'

        return product_name

    def get_mic(self, line=None):
        mic = ''
        if line:
            if line._name == 'marfrig.service.products':
                mic = 'N/A'
                return mic
            if line._name == 'rt.service.productos':
                mic = line.rt_carga_id.mic_number if line.rt_carga_id.mic_number else 'N/A'

            if line._name == 'carpeta.camion':
                mic = line.mic_number if line.mic_number else 'N/A'

        return mic


    def get_date(self, line=None):
        date = ''
        if line:
            if line._name == 'marfrig.service.products':
                date = formatters.date_fmt(line.start.isoformat()[:10])
            if line._name == 'rt.service.productos':
                date = formatters.date_fmt(line.start.isoformat()[:10])
            if line._name == 'carpeta.camion':
                date = formatters.date_fmt(line.start_datetime.isoformat()[:10])
            if line._name == 'deposito.service.products':
                date = formatters.date_fmt(line.start.isoformat()[:10])

        return date


    def get_crt(self, line=None):
        crt = ''
        if line:
            if line._name == 'marfrig.service.products':
                crt = 'N/A'
                return crt
            if line._name == 'rt.service.productos':
                crt = line.rt_carga_id.crt_number if line.rt_carga_id.crt_number else 'N/A'

            if line._name == 'carpeta.camion':
                crt = 'N/A'

        return crt

    def get_ref_carga(self, line=None):
        ref_carga = ''
        if line:
            if line._name == 'marfrig.service.products':
                ref_carga = line.mrf_srv_id.sale_number if line.mrf_srv_id.sale_number else 'N/A'

            if line._name == 'rt.service.productos':
                ref_carga = line.rt_carga_id.name if line.rt_carga_id.name else 'N/A'

            if line._name == 'carpeta.camion':
                ref_carga = 'N/A'

        return ref_carga

    def get_origin(self, line=None):
        origin = ''
        if line:
            if line._name == 'marfrig.service.products':
                origin = line.origin_id.name if line.origin_id else 'N/A'

            if line._name == 'rt.service.productos':
                origin = line.origin_id.name if line.origin_id else 'N/A'

            if line._name == 'carpeta.camion':
                origin = line.aduana_origen_id.name if line.aduana_origen_id else 'N/A'

            if line._name == 'deposito.service.products':
                origin = line.origin_id.name if line.origin_id else 'N/A'

        return origin

    def get_destiny(self, line=None):
        destiny = ''
        if line:
            if line._name == 'marfrig.service.products':
                destiny = line.destiny_id.name if line.destiny_id else 'N/A'

            if line._name == 'rt.service.productos':
                destiny = line.destiny_id.name if line.destiny_id else 'N/A'

            if line._name == 'carpeta.camion':
                destiny = line.aduana_destino_id.name.name if line.aduana_destino_id else 'N/A'

            if line._name == 'deposito.service.products':
                destiny = line.destiny_id.name if line.destiny_id else 'N/A'

        return destiny

    def get_driver_ids(self, lines):
        if not lines:
            return list()
        driver_ids = []
        for line in lines:
            if line.driver_id:
                driver_ids.append(line.driver_id.id)
        return driver_ids

    def write_page_per_driver(self, work_book=None, lines_rt=None, lines_m=None, lines_consol=None, lines_deposito=None):
        maximo_largo_contenido_por_columna = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        title = easyxf('font: name Calibri, bold True; alignment: horizontal left')
        title_number = easyxf('font: name Calibri, bold True; alignment: horizontal right', num_format_str='#,##0.00;-#,##0.00;')
        lineas = easyxf('font: name Calibri; alignment: horizontal left')
        fila = 0
        if lines_consol:
            lines = lines_consol
        if lines_rt:
            lines = lines_rt
        if lines_m:
            lines = lines_m
        if lines_deposito:
            lines = lines_deposito

        ws = work_book.add_sheet('%s' % lines[0].driver_id.name, cell_overwrite_ok=True)
        ws.write(0, 0, self.env['res.company'].browse(1).name, title)
        ws.write(0, 5, formatters.date_fmt(fields.Date.today().isoformat()), title)
        ws.write(fila, 0, "Producto", title)
        ws.write(fila, 1, "Cliente a Facturar", title)
        ws.write(fila, 2, "Ref Carpeta", title)
        ws.write(fila, 3, "Contenedor", title)
        ws.write(fila, 4, "DUA", title)
        ws.write(fila, 5, "MIC", title)
        ws.write(fila, 6, "CRT", title)
        ws.write(fila, 7, "Ref Producto", title)
        ws.write(fila, 8, "Ref Carga", title_number)
        ws.write(fila, 9, "Fecha Servicio", title_number)
        ws.write(fila, 10, "Chofer", title_number)
        ws.write(fila, 11, "Matricula", title)
        ws.write(fila, 12, "Origen", title)
        ws.write(fila, 13, "Destino", title)
        ws.write(fila, 14, "Moneda", title)
        ws.write(fila, 15, "Monto", title)
        ultima_columna = 165
        ws.write(fila, ultima_columna, "ID", title)
        fila += 1
        primer_fila = 0
        ultima_fila = 0
        primer_fila = fila + 1

        if lines_rt:
            for line in lines_rt:
                producto = line.product_id.name
                largo_producto = len(str(producto))
                maximo_largo_contenido_por_columna[0] = max(maximo_largo_contenido_por_columna[0], largo_producto)

                cliente = self.get_partner_to_invoice_name(line)
                largo_cliente = len(str(cliente))
                maximo_largo_contenido_por_columna[1] = max(maximo_largo_contenido_por_columna[1], largo_cliente)

                ref_carpeta = self.get_ref_carpeta(line)
                largo_ref_carpeta = len(str(ref_carpeta))
                maximo_largo_contenido_por_columna[2] = max(maximo_largo_contenido_por_columna[2], largo_ref_carpeta)

                contenedor = self.get_container_number(line)
                largo_contenedor = len(str(contenedor))
                maximo_largo_contenido_por_columna[3] = max(maximo_largo_contenido_por_columna[3], largo_contenedor)

                dua = self.get_dua(line)
                largo_dua = len(str(dua))
                maximo_largo_contenido_por_columna[4] = max(maximo_largo_contenido_por_columna[4], largo_dua)

                mic = self.get_mic(line)
                largo_mic = len(str(mic))
                maximo_largo_contenido_por_columna[5] = max(maximo_largo_contenido_por_columna[5], largo_mic)

                crt = self.get_crt(line)
                largo_crt = len(str(crt))
                maximo_largo_contenido_por_columna[6] = max(maximo_largo_contenido_por_columna[6], largo_crt)

                ref_prod = line.name if line.name else 'N/A'
                largo_ref_prodo = len(str(ref_prod))
                maximo_largo_contenido_por_columna[7] = max(maximo_largo_contenido_por_columna[7], largo_ref_prodo)

                ref_carga = self.get_ref_carga(line)
                largo_ref_carga = len(str(ref_carga))
                maximo_largo_contenido_por_columna[8] = max(maximo_largo_contenido_por_columna[8], largo_ref_carga)

                fecha = self.get_date(line)
                largo_fecha = len(str(fecha))
                maximo_largo_contenido_por_columna[9] = max(maximo_largo_contenido_por_columna[9], largo_fecha)

                chofer = line.driver_id.name if line.driver_id.name else 'N/A'
                largo_chofer = len(str(chofer))
                maximo_largo_contenido_por_columna[10] = max(maximo_largo_contenido_por_columna[10], largo_chofer)

                matricula = line.vehicle_id.license_plate
                largo_matricula = len(str(matricula))
                maximo_largo_contenido_por_columna[11] = max(maximo_largo_contenido_por_columna[11], largo_matricula)

                origen = line.origin_id.name if line.origin_id else 'N/A'
                largo_origen = len(str(origen))
                maximo_largo_contenido_por_columna[12] = max(maximo_largo_contenido_por_columna[12], largo_origen)

                destino = line.destiny_id.name if line.destiny_id else 'N/A'
                largo_destino = len(str(destino))
                maximo_largo_contenido_por_columna[13] = max(maximo_largo_contenido_por_columna[13], largo_destino)

                moneda = line.currency_id_chofer.name if line.currency_id_chofer else 'N/A'
                largo_moneda = len(str(moneda))
                maximo_largo_contenido_por_columna[14] = max(maximo_largo_contenido_por_columna[14], largo_moneda)

                monto = line.driver_commission
                largo_monto = len(str(monto))
                maximo_largo_contenido_por_columna[15] = max(maximo_largo_contenido_por_columna[15], largo_monto)

                ws.write(fila, ultima_columna, line.id, lineas)
                ws.col(ultima_columna).hidden = True

                ws.write(fila, 0, producto, lineas)
                ws.write(fila, 1, cliente, lineas)
                ws.write(fila, 2, ref_carpeta, lineas)
                ws.write(fila, 3, contenedor, lineas)
                ws.write(fila, 4, dua, lineas)
                ws.write(fila, 5, mic, lineas)
                ws.write(fila, 6, crt, lineas)
                ws.write(fila, 7, ref_prod, lineas)
                ws.write(fila, 8, ref_carga, lineas)
                ws.write(fila, 9, fecha, lineas)
                ws.write(fila, 10, chofer, lineas)
                ws.write(fila, 11, matricula, lineas)
                ws.write(fila, 12, origen, lineas)
                ws.write(fila, 13, destino, lineas)
                ws.write(fila, 14, moneda, lineas)
                ws.write(fila, 15, monto, lineas)


                fila += 1
                ultima_fila = fila
                ws.write(ultima_fila, 14, "Total", title_number)
                primer_fila = 1
                ws.write(fila, 15, Formula("SUM(P%s :P%s)" % (primer_fila, ultima_fila)), title_number)
                column = 0
                for maximo in maximo_largo_contenido_por_columna:
                    if maximo <= 3:
                        maximo = 10
                    ws.col(column).width = maximo * 290

                    if column == 15:
                        ws.col(column).width = 12 * 290
                    column += 1

        if lines_m:
            for line in lines_m:
                producto = line.product_id.name
                largo_producto = len(str(producto))
                maximo_largo_contenido_por_columna[0] = max(maximo_largo_contenido_por_columna[0], largo_producto)

                cliente = self.get_partner_to_invoice_name(line)
                largo_cliente = len(str(cliente))
                maximo_largo_contenido_por_columna[1] = max(maximo_largo_contenido_por_columna[1], largo_cliente)

                ref_carpeta = self.get_ref_carpeta(line)
                largo_ref_carpeta = len(str(ref_carpeta))
                maximo_largo_contenido_por_columna[2] = max(maximo_largo_contenido_por_columna[2], largo_ref_carpeta)

                contenedor = self.get_container_number(line)
                largo_contenedor = len(str(contenedor))
                maximo_largo_contenido_por_columna[3] = max(maximo_largo_contenido_por_columna[3], largo_contenedor)

                dua = self.get_dua(line)
                largo_dua = len(str(dua))
                maximo_largo_contenido_por_columna[4] = max(maximo_largo_contenido_por_columna[4], largo_dua)

                mic = self.get_mic(line)
                largo_mic = len(str(mic))
                maximo_largo_contenido_por_columna[5] = max(maximo_largo_contenido_por_columna[5], largo_mic)

                crt = self.get_crt(line)
                largo_crt = len(str(crt))
                maximo_largo_contenido_por_columna[6] = max(maximo_largo_contenido_por_columna[6], largo_crt)

                ref_prod = line.name if line.name else 'N/A'
                largo_ref_prodo = len(str(ref_prod))
                maximo_largo_contenido_por_columna[7] = max(maximo_largo_contenido_por_columna[7], largo_ref_prodo)

                ref_carga = self.get_ref_carga(line)
                largo_ref_carga = len(str(ref_carga))
                maximo_largo_contenido_por_columna[8] = max(maximo_largo_contenido_por_columna[8], largo_ref_carga)

                fecha = self.get_date(line)
                largo_fecha = len(str(fecha))
                maximo_largo_contenido_por_columna[9] = max(maximo_largo_contenido_por_columna[9], largo_fecha)

                chofer = line.driver_id.name if line.driver_id.name else 'N/A'
                largo_chofer = len(str(chofer))
                maximo_largo_contenido_por_columna[10] = max(maximo_largo_contenido_por_columna[10], largo_chofer)

                matricula = line.vehicle_id.name
                largo_matricula = len(str(matricula))
                maximo_largo_contenido_por_columna[11] = max(maximo_largo_contenido_por_columna[11], largo_matricula)

                origen = line.origin_id.name if line.origin_id else 'N/A'
                largo_origen = len(str(origen))
                maximo_largo_contenido_por_columna[12] = max(maximo_largo_contenido_por_columna[12], largo_origen)

                destino = line.destiny_id.name if line.destiny_id else 'N/A'
                largo_destino = len(str(destino))
                maximo_largo_contenido_por_columna[13] = max(maximo_largo_contenido_por_columna[13], largo_destino)

                moneda = line.currency_id_chofer.name if line.currency_id_chofer else 'N/A'
                largo_moneda = len(str(moneda))
                maximo_largo_contenido_por_columna[14] = max(maximo_largo_contenido_por_columna[14], largo_moneda)

                monto = line.driver_commission
                largo_monto = len(str(monto))
                maximo_largo_contenido_por_columna[15] = max(maximo_largo_contenido_por_columna[15], largo_monto)

                ws.write(fila, ultima_columna, line.id, lineas)
                ws.col(ultima_columna).hidden = True

                ws.write(fila, 0, producto, lineas)
                ws.write(fila, 1, cliente, lineas)
                ws.write(fila, 2, ref_carpeta, lineas)
                ws.write(fila, 3, contenedor, lineas)
                ws.write(fila, 4, dua, lineas)
                ws.write(fila, 5, mic, lineas)
                ws.write(fila, 6, crt, lineas)
                ws.write(fila, 7, ref_prod, lineas)
                ws.write(fila, 8, ref_carga, lineas)
                ws.write(fila, 9, fecha, lineas)
                ws.write(fila, 10, chofer, lineas)
                ws.write(fila, 11, matricula, lineas)
                ws.write(fila, 12, origen, lineas)
                ws.write(fila, 13, destino, lineas)
                ws.write(fila, 14, moneda, lineas)
                ws.write(fila, 15, monto, lineas)
                fila += 1
                ultima_fila = fila

        if lines_consol:
            for line in lines_consol:
                producto = self.get_product_name(line)
                largo_producto = len(str(producto))
                maximo_largo_contenido_por_columna[0] = max(maximo_largo_contenido_por_columna[0], largo_producto)

                cliente = self.get_partner_to_invoice_name(line)
                largo_cliente = len(str(cliente))
                maximo_largo_contenido_por_columna[1] = max(maximo_largo_contenido_por_columna[1], largo_cliente)

                ref_carpeta = self.get_ref_carpeta(line)
                largo_ref_carpeta = len(str(ref_carpeta))
                maximo_largo_contenido_por_columna[2] = max(maximo_largo_contenido_por_columna[2], largo_ref_carpeta)

                contenedor = self.get_container_number(line)
                largo_contenedor = len(str(contenedor))
                maximo_largo_contenido_por_columna[3] = max(maximo_largo_contenido_por_columna[3], largo_contenedor)

                dua = self.get_dua(line)
                largo_dua = len(str(dua))
                maximo_largo_contenido_por_columna[4] = max(maximo_largo_contenido_por_columna[4], largo_dua)

                mic = self.get_mic(line)
                largo_mic = len(str(mic))
                maximo_largo_contenido_por_columna[5] = max(maximo_largo_contenido_por_columna[5], largo_mic)

                crt = self.get_crt(line)
                largo_crt = len(str(crt))
                maximo_largo_contenido_por_columna[6] = max(maximo_largo_contenido_por_columna[6], largo_crt)

                ref_prod = line.name if line.name else 'N/A'
                largo_ref_prodo = len(str(ref_prod))
                maximo_largo_contenido_por_columna[7] = max(maximo_largo_contenido_por_columna[7], largo_ref_prodo)

                ref_carga = self.get_ref_carga(line)
                largo_ref_carga = len(str(ref_carga))
                maximo_largo_contenido_por_columna[8] = max(maximo_largo_contenido_por_columna[8], largo_ref_carga)

                fecha = self.get_date(line)
                largo_fecha = len(str(fecha))
                maximo_largo_contenido_por_columna[9] = max(maximo_largo_contenido_por_columna[9], largo_fecha)

                chofer = line.driver_id.name if line.driver_id.name else 'N/A'
                largo_chofer = len(str(chofer))
                maximo_largo_contenido_por_columna[10] = max(maximo_largo_contenido_por_columna[10], largo_chofer)

                matricula = line.vehicle_id.name
                largo_matricula = len(str(matricula))
                maximo_largo_contenido_por_columna[11] = max(maximo_largo_contenido_por_columna[11], largo_matricula)

                origen = self.get_origin(line)
                largo_origen = len(str(origen))
                maximo_largo_contenido_por_columna[12] = max(maximo_largo_contenido_por_columna[12], largo_origen)

                destino = self.get_destiny(line)
                largo_destino = len(str(destino))
                maximo_largo_contenido_por_columna[13] = max(maximo_largo_contenido_por_columna[13], largo_destino)

                moneda = line.currency_id_chofer.name if line.currency_id_chofer else 'N/A'
                largo_moneda = len(str(moneda))
                maximo_largo_contenido_por_columna[14] = max(maximo_largo_contenido_por_columna[14], largo_moneda)

                monto = line.driver_commission
                largo_monto = len(str(monto))
                maximo_largo_contenido_por_columna[15] = max(maximo_largo_contenido_por_columna[15], largo_monto)

                ws.write(fila, ultima_columna, line.id, lineas)
                ws.col(ultima_columna).hidden = True

                ws.write(fila, 0, producto, lineas)
                ws.write(fila, 1, cliente, lineas)
                ws.write(fila, 2, ref_carpeta, lineas)
                ws.write(fila, 3, contenedor, lineas)
                ws.write(fila, 4, dua, lineas)
                ws.write(fila, 5, mic, lineas)
                ws.write(fila, 6, crt, lineas)
                ws.write(fila, 7, ref_prod, lineas)
                ws.write(fila, 8, ref_carga, lineas)
                ws.write(fila, 9, fecha, lineas)
                ws.write(fila, 10, chofer, lineas)
                ws.write(fila, 11, matricula, lineas)
                ws.write(fila, 12, origen, lineas)
                ws.write(fila, 13, destino, lineas)
                ws.write(fila, 14, moneda, lineas)
                ws.write(fila, 15, monto, lineas)
                fila += 1
                ultima_fila = fila

        if lines_deposito:
            for line in lines_deposito:
                producto = self.get_product_name(line)
                largo_producto = len(str(producto))
                maximo_largo_contenido_por_columna[0] = max(maximo_largo_contenido_por_columna[0], largo_producto)

                cliente = self.get_partner_to_invoice_name(line)
                largo_cliente = len(str(cliente))
                maximo_largo_contenido_por_columna[1] = max(maximo_largo_contenido_por_columna[1], largo_cliente)

                ref_carpeta = self.get_ref_carpeta(line)
                largo_ref_carpeta = len(str(ref_carpeta))
                maximo_largo_contenido_por_columna[2] = max(maximo_largo_contenido_por_columna[2], largo_ref_carpeta)

                contenedor = 'N/A'
                largo_contenedor = len(str(contenedor))
                maximo_largo_contenido_por_columna[3] = max(maximo_largo_contenido_por_columna[3], largo_contenedor)

                dua = 'N/A'
                largo_dua = len(str(dua))
                maximo_largo_contenido_por_columna[4] = max(maximo_largo_contenido_por_columna[4], largo_dua)

                mic = 'N/A'
                largo_mic = len(str(mic))
                maximo_largo_contenido_por_columna[5] = max(maximo_largo_contenido_por_columna[5], largo_mic)

                crt = 'N/A'
                largo_crt = len(str(crt))
                maximo_largo_contenido_por_columna[6] = max(maximo_largo_contenido_por_columna[6], largo_crt)

                ref_prod = line.name if line.name else 'N/A'
                largo_ref_prodo = len(str(ref_prod))
                maximo_largo_contenido_por_columna[7] = max(maximo_largo_contenido_por_columna[7], largo_ref_prodo)

                ref_carga = 'N/A'
                largo_ref_carga = len(str(ref_carga))
                maximo_largo_contenido_por_columna[8] = max(maximo_largo_contenido_por_columna[8], largo_ref_carga)

                fecha = self.get_date(line)
                largo_fecha = len(str(fecha))
                maximo_largo_contenido_por_columna[9] = max(maximo_largo_contenido_por_columna[9], largo_fecha)

                chofer = line.driver_id.name if line.driver_id.name else 'N/A'
                largo_chofer = len(str(chofer))
                maximo_largo_contenido_por_columna[10] = max(maximo_largo_contenido_por_columna[10], largo_chofer)

                matricula = line.vehicle_id.name
                largo_matricula = len(str(matricula))
                maximo_largo_contenido_por_columna[11] = max(maximo_largo_contenido_por_columna[11], largo_matricula)

                origen = self.get_origin(line)
                largo_origen = len(str(origen))
                maximo_largo_contenido_por_columna[12] = max(maximo_largo_contenido_por_columna[12], largo_origen)

                destino = self.get_destiny(line)
                largo_destino = len(str(destino))
                maximo_largo_contenido_por_columna[13] = max(maximo_largo_contenido_por_columna[13], largo_destino)

                moneda = line.currency_id_chofer.name if line.currency_id_chofer else 'N/A'
                largo_moneda = len(str(moneda))
                maximo_largo_contenido_por_columna[14] = max(maximo_largo_contenido_por_columna[14], largo_moneda)

                monto = line.driver_commission
                largo_monto = len(str(monto))
                maximo_largo_contenido_por_columna[15] = max(maximo_largo_contenido_por_columna[15], largo_monto)

                ws.write(fila, ultima_columna, line.id, lineas)
                ws.col(ultima_columna).hidden = True

                ws.write(fila, 0, producto, lineas)
                ws.write(fila, 1, cliente, lineas)
                ws.write(fila, 2, ref_carpeta, lineas)
                ws.write(fila, 3, contenedor, lineas)
                ws.write(fila, 4, dua, lineas)
                ws.write(fila, 5, mic, lineas)
                ws.write(fila, 6, crt, lineas)
                ws.write(fila, 7, ref_prod, lineas)
                ws.write(fila, 8, ref_carga, lineas)
                ws.write(fila, 9, fecha, lineas)
                ws.write(fila, 10, chofer, lineas)
                ws.write(fila, 11, matricula, lineas)
                ws.write(fila, 12, origen, lineas)
                ws.write(fila, 13, destino, lineas)
                ws.write(fila, 14, moneda, lineas)
                ws.write(fila, 15, monto, lineas)
                fila += 1
                ultima_fila = fila

        ws.write(ultima_fila, 14, "Total", title_number)
        ws.write(fila, 15, Formula("SUM(P%s :P%s)" % (primer_fila, ultima_fila)), title_number)
        column = 0
        for maximo in maximo_largo_contenido_por_columna:
            if maximo <= 3:
                maximo = 10
            ws.col(column).width = maximo * 290
            if column == 15:
                ws.col(column).width = 12 * 290
            column += 1
        return

    def get_report_name(self, driver=None, categ=None, start=None, stop=None, operation_type=None):
        report_mame = ''
        if operation_type == 'national':
            operativa = 'Nacional'
        if operation_type == 'international':
            operativa = 'Internacional'
        driver_name = str(driver.first_name) + ' ' + str(driver.first_surname)
        if driver and not categ:
            report_mame = operativa + ' - ' + driver_name + ' - ' + formatters.date_fmt(start.isoformat()[:10]) + ' - ' + formatters.date_fmt(stop.isoformat()[:10])

        if categ and not driver:
            report_mame = operativa + ' - ' + categ.name + ' - ' + formatters.date_fmt(start.isoformat()[:10]) + ' - ' + formatters.date_fmt(stop.isoformat()[:10])

        if driver and categ:
            report_mame = operativa + ' - ' + categ.name + ' - ' + driver_name + ' - ' + formatters.date_fmt(start.isoformat()[:10]) + ' - ' + formatters.date_fmt(stop.isoformat()[:10])

        if not driver and not categ:
            report_mame = operativa + ' - ' + formatters.date_fmt(start.isoformat()[:10]) + ' - ' + formatters.date_fmt(stop.isoformat()[:10])
        return report_mame

    @api.multi
    def gen_report_xls_ventas_fleteros(self):
        #Creo el 'Libro' y su 'Pagina'
        wb = Workbook(encoding='utf-8')
        maximo_largo_contenido_por_columna = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        # Datos de la empresa y fecha de emision
        nombre_empresa = self.env['res.company'].browse(1).name
        largo_nombre_empresa = len(nombre_empresa)
        start, stop = self.convert_date_to_datetime(self.inicio, self.fin)
        maximo_largo_contenido_por_columna[0] = max(maximo_largo_contenido_por_columna[0], largo_nombre_empresa)
        lines = self.get_lineas(start, stop, self.driver_id, self.categ_id, self.operation_type)
        lines_m = self.get_lineas_m(start, stop, self.driver_id, self.categ_id, self.operation_type)
        lines_consol = self.lines_consol(start, stop, self.driver_id, self.categ_id, self.operation_type)
        lines_deposito = self.get_lineas_deposito(start, stop, self.driver_id, self.categ_id, self.operation_type)
        total_per_driver = {}

        drivers_rt = self.get_driver_ids(lines)
        drivers_mar = self.get_driver_ids(lines_m)
        drivers_consol = self.get_driver_ids(lines_consol)
        drivers_deposito = self.get_driver_ids(lines_deposito)
        drivers_combined = set(drivers_rt + drivers_mar + drivers_consol + drivers_deposito)
        filtered_rt = filtered_mar = filtered_consol = filtered_deposito = []
        for driver in drivers_combined:
            driver_id = driver
            if lines:
                filtered_rt = lines.filtered(lambda x: x.driver_id.id == driver_id)
            if lines_m:
                filtered_mar = lines_m.filtered(lambda x: x.driver_id.id == driver_id)
            if lines_consol:
                filtered_consol = lines_consol.filtered(lambda x: x.driver_id.id == driver_id)
            if lines_deposito:
                filtered_deposito = lines_deposito.filtered(lambda x: x.driver_id.id == driver_id)
            if not filtered_rt and not filtered_mar and not filtered_consol and not filtered_deposito:
                continue

            if filtered_rt or filtered_rt or filtered_consol or filtered_deposito:
                total_per_driver[driver] = sum(_x.driver_commission for _x in filtered_rt) + sum(_x.driver_commission for _x in filtered_mar) + sum(_x.driver_commission for _x in filtered_consol) + sum(_x.driver_commission for _x in filtered_deposito)
                self.write_page_per_driver(work_book=wb, lines_rt=filtered_rt, lines_m=filtered_mar, lines_consol=filtered_consol, lines_deposito=filtered_deposito)

        #Totales
        title = easyxf('font: name Calibri, bold True; alignment: horizontal left')
        lineas = easyxf('font: name Calibri; alignment: horizontal left')
        title_number = easyxf('font: name Calibri, bold True; alignment: horizontal right',num_format_str='#,##0.00;-#,##0.00;')
        ws = wb.add_sheet('Totales', cell_overwrite_ok=True)
        fila = 3
        ws.write(2, 0, "Chofer", title)
        ws.write(2, 1, "Total", title)
        primer_fila = fila
        ultima_fila = 0
        column_size = [0, 0]
        for k, v in total_per_driver.items():
            # fila = fila + 1
            driver_name = self.env['hr.employee'].browse(k).name
            size_driver_name = len(driver_name)
            column_size[0] = max(column_size[0], size_driver_name)
            column_size[1] = 12
            ws.write(fila, 0, driver_name, lineas)
            ws.write(fila, 1, v, lineas)
            fila += 1
            ultima_fila = fila



        ws.write(fila, 0, "Total", title_number)
        if ultima_fila == 0:
            ultima_fila = 10
        ws.write(fila, 1, Formula("SUM(B%s :B%s)" % (primer_fila, ultima_fila)), title_number)
        column = 0
        for maximo in maximo_largo_contenido_por_columna:
            if maximo <= 3:
                maximo = 10
            ws.col(column).width = maximo * 290
            if column == 15:
                ws.col(column).width = 12 * 290
            column += 1

        column = 0
        if ws.name == 'Totales':
            for max_column_size in column_size:
                ws.col(column).width = max_column_size * 290
                if column == 1:
                    ws.col(column).width = 12 * 290
                column += 1
        # Salvo el contenido
        fp = BytesIO()
        wb.save(fp)
        fp.seek(0)
        data = fp.read()
        fp.close()

        data_to_save = base64.encodebytes(data)
        file_name = 'Reporte de Viajes - %s.xls' % self.get_report_name(driver=self.driver_id, categ=self.categ_id, start=self.inicio, stop=self.fin, operation_type=self.operation_type)
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
