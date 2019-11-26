# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api
import string
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning
import xlsxwriter
from xlwt import *
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
    _name = 'informe.ventas.cliente'

    def get_numero_factura(self, factura):
        numero_factura = ''
        if factura:
            if factura.type == 'out_invoice' and factura.state != 'draft':
                if numero_factura:
                    numero_factura += ' / ' + str(factura.fe_Serie) + '-' + str(factura.fe_DocNro)
                else:
                    numero_factura = str(factura.fe_Serie) + '-' + str(factura.fe_DocNro)

        return numero_factura

    def get_nota_de_credito(self, factura):
        numero_factura = ''
        if factura:
            if factura.type == 'out_refund' and factura.state != 'draft':
                if numero_factura:
                    numero_factura += ' / ' + str(factura.fe_Serie) + '-' + str(factura.fe_DocNro)
                else:
                    numero_factura = str(factura.fe_Serie) + '-' + str(factura.fe_DocNro)

        return numero_factura

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
    product_id = fields.Many2one(comodel_name='product.product', string='Servicio',
                                 domain=[('product_tmpl_id.type', '=', 'service'), ('sale_ok', '=', True),
                                         ('active', '=', True)], required=False, change_default=True,
                                 ondelete='restrict', track_visibility='always')
    partner_invoice_id = fields.Many2one(comodel_name='res.partner', string='Cliente a facturar', domain=[('customer', '=', True)], store=True)
    regimen = fields.Selection(_get_operation_type, string="Regimen", store=True)
    origin_id = fields.Many2one(comodel_name='res.partner.address.ext', string='Origen')
    destiny_id = fields.Many2one(comodel_name='res.partner.address.ext', string='Destino')
    info_type = fields.Selection([('operativa', 'Operativa'), ('contabilidad', 'Contabilidad')], string='Tipo de Servicio', default='contabilidad')
    make_informe_all = fields.Boolean()

    @api.multi
    @api.depends('name', 'start', 'stop')
    def name_get(self):
        return [(rec.id, '%s - %s' % (rec.start, rec.stop)) for rec in self]

    @api.onchange('partner_invoice_id')
    def onchane_partner_invoice_id(self):
        if self.partner_invoice_id:
            self.make_informe_all = True
            self.tipo_informe = 'all'
        else:
            self.make_informe_all = False

    def posicion_total(self, columna_inicio):
        dicofwords = {i: list(string.ascii_uppercase)[i] for i in range(0, len(list(string.ascii_uppercase)))}
        formula_total = "SUM(" + dicofwords[columna_inicio+1] + "%s :" + dicofwords[columna_inicio+1]+ "%s)"

        return formula_total

    def obtener_nombre_filtrado(self):
        nombre_filtro = ''
        if self.partner_invoice_id:
            nombre_filtro += self.partner_invoice_id.name
        if self.regimen:
            if nombre_filtro:
                nombre_filtro += ' / ' + self.map_regimen()[self.regimen]
            else:
                nombre_filtro = self.map_regimen()[self.regimen]
        if self.origin_id:
            if nombre_filtro:
                nombre_filtro += ' / ' + self.origin_id.name
            else:
                nombre_filtro = self.origin_id.name
        if self.destiny_id:
            if nombre_filtro:
                nombre_filtro += ' / ' + self.destiny_id.name
            else:
                nombre_filtro = self.destiny_id.name
        return nombre_filtro

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

    def get_pesos(self, condiciones_busqueda):
        facturas = self.env['account.invoice']
        pesos = self.env['res.currency'].search([('name', '=', 'UYU')]).id
        condiciones_busqueda.append(('currency_id', '=', pesos))
        facturas_pesos = facturas.search(condiciones_busqueda, order='partner_id , date_invoice')

        return facturas_pesos

    def get_dolares(self, condiciones_busqueda):
        #Si la lista viene con la condicion de busqueda para pesos, la reemplazamos por dolares
        # condiciones_busqueda.remove(('currency_id', '=', 46))
        facturas = self.env['account.invoice']
        dolares = self.env['res.currency'].search([('name', '=', 'USD')]).id
        condiciones_busqueda = list(map(lambda x: x if x != ('currency_id', '=', 46) else ('currency_id', '=', dolares), condiciones_busqueda))
        facturas_dolares = facturas.search(condiciones_busqueda, order='partner_id , date_invoice')

        return facturas_dolares

    def get_facturas(self, start, stop):
        condiciones_busqueda = []
        productos_service = self.env['rt.service.productos']
        productos_consolidado = self.env['producto.servicio.camion']
        productos_deposito = self.env['deposito.service.products']
        carpeta_marfrig = self.env['marfrig.service.base']
        condiciones_busqueda = [('date_invoice', '>=', start), ('date_invoice', '<=', stop), ('state', 'in', ('open', 'paid')), ('type', 'in', ('out_invoice', 'out_refund'))]
        if self.partner_invoice_id:
            condiciones_busqueda.append(('partner_id', '=', self.partner_invoice_id.id))
        if self.regimen or self.origin_id or self.destiny_id:
            productos_service = self.get_productos_service(productos_service)
            productos_consolidado = self.get_productos_consolidado(productos_consolidado)
            if self.regimen == 'expo_nat' or not self.regimen:
                carpeta_marfrig = self.get_productos_marfrig(carpeta_marfrig)
                condiciones_busqueda.append('|')
                condiciones_busqueda.append(('marfrig_operation_id', 'in', carpeta_marfrig.ids))
            if not self.regimen:
                productos_deposito = self.get_productos_deposito(productos_deposito)
            lineas = self.env['account.invoice.line'].search(['|', '|', ('rt_service_product_id', 'in', productos_service.ids),
                                                              ('consolidado_service_product_id', 'in', productos_consolidado.ids),
                                                              ('product_deposito_srv_id', 'in', productos_deposito.ids)])
            condiciones_busqueda.append(('invoice_line_ids', 'in', lineas.ids))

        facturas = self.env['account.invoice'].search(condiciones_busqueda,  order='partner_id , date_invoice')
        condiciones_busqueda.append(('currency_id', '=', 46))
        facturas_pesos = self.get_pesos(condiciones_busqueda)
        facturas_dolares = self.get_dolares(condiciones_busqueda)
        # if self.regimen:
        #     productos_service = self.get_productos_service(productos_service)
        #     productos_consolidado = self.get_productos_consolidado(productos_consolidado)
        #     if self.regimen == 'expo_nat':
        #         carpeta_marfrig = self.get_productos_marfrig(carpeta_marfrig)
        #     lineas = self.env['account.invoice.line'].search(['|', ('rt_service_product_id', 'in', productos_service.ids),
        #                                                       ('rt_consol_product_id', 'in', productos_consolidado.ids)])
        #     factura = self.env['account.invoice'].search([('invoice_line_ids', 'in', lineas.ids)])
        #     id_pesos = []
        #     id_dolares = []
        #     id_todos = []
        #     for filtrado in factura:
        #         if filtrado.id in facturas_pesos.ids:
        #             id_pesos.append(filtrado.id)
        #             id_todos.append(filtrado.id)
        #         if filtrado.id in facturas_dolares.ids:
        #             id_dolares.append(filtrado.id)
        #             id_todos.append(filtrado.id)
        #     facturas_pesos = self.env['account.invoice'].search([('id', 'in', id_pesos)], order='partner_id , create_date')
        #     facturas_dolares = self.env['account.invoice'].search([('id', 'in', id_dolares)], order='partner_id , create_date')
        #     facturas = self.env['account.invoice'].search([('id', 'in', id_todos)], order='partner_id , create_date')

        return facturas, facturas_pesos, facturas_dolares

    def get_productos_service(self, productos):
        condiciones_busqueda = [('invoiced', '=', True)]
        if self.regimen:
            condiciones_busqueda.append(('regimen', '=', self.regimen))
        if self.origin_id:
            condiciones_busqueda.append(('origin_id', '=', self.origin_id.id))
        if self.destiny_id:
            condiciones_busqueda.append(('destiny_id', '=', self.destiny_id.id))
        productos = productos.search(condiciones_busqueda)
        return productos

    def get_productos_deposito(self, productos):
        condiciones_busqueda = []
        if self.origin_id:
            condiciones_busqueda.append(('origin_id', '=', self.origin_id.id))
        if self.destiny_id:
            condiciones_busqueda.append(('destiny_id', '=', self.destiny_id.id))
        productos = productos.search(condiciones_busqueda)
        return productos

    def get_productos_consolidado(self, productos):
        condiciones_busqueda = [('invoiced', '=', True)]
        if self.regimen:
            condiciones_busqueda.append(('regimen', '=', self.regimen))
        if self.origin_id:
            condiciones_busqueda.append(('origin_id', '=', self.origin_id.id))
        if self.destiny_id:
            condiciones_busqueda.append(('destiny_id', '=', self.destiny_id.id))
        productos = productos.search(condiciones_busqueda)
        return productos

    def get_productos_marfrig(self, productos):
        condiciones_busqueda_lineas = []
        condiciones_busqueda = []
        if self.origin_id:
            condiciones_busqueda_lineas.append(('origin_id', '=', self.origin_id.id))
        if self.destiny_id:
            condiciones_busqueda_lineas.append(('destiny_id', '=', self.destiny_id.id))
        if condiciones_busqueda_lineas:
            lineas = self.env['marfrig.service.products'].search(condiciones_busqueda_lineas)
            condiciones_busqueda.append(('mrf_srv_ids', 'in', lineas.ids))
        productos = productos.search(condiciones_busqueda)
        return productos

    def agrupar_lineas(self, lineas, total, dolares, fecha):
        list_lineas = []
        if lineas:
            if total:
                tipo_cambio = self.env['res.currency.rate'].search([('name', '<=', fecha), ('currency_id', '=', 2)],limit=1)
            for line in lineas:
                existe = False
                linea = []
                comparacion = []
                info = []
                producto = False
                if line.rt_service_product_id:
                    producto = line.rt_service_product_id
                if line.consolidado_service_product_id:
                    producto = line.consolidado_service_product_id
                if line.product_deposito_srv_id:
                    producto = line.product_deposito_srv_id
                if line.invoice_id.service_marfrig_ids:
                    for prod in line.invoice_id.service_marfrig_ids:
                        if prod.product_id.name == line.product_id.name:
                            producto = prod
                comparacion.append(line.product_id.name) if line.product_id else comparacion.append('N/A')
                comparacion.append(line.account_id.name) if line.account_id else comparacion.append('N/A')
                if producto:
                    comparacion.append(producto.origin_id.name) if producto.origin_id else comparacion.append('N/A')
                    comparacion.append(producto.destiny_id.name) if producto.destiny_id else comparacion.append('N/A')
                    if producto == line.rt_service_product_id or producto == line.consolidado_service_product_id or producto == line.product_deposito_srv_id:
                        info.append(producto.partner_invoice_id.name) if producto.partner_invoice_id else info.append('N/A')
                    elif line.invoice_id.service_marfrig_ids:
                        info.append(line.invoice_id.partner_id.name) if line.invoice_id.partner_id else info.append('N/A')
                    else:
                        info.append('N/A')
                else:
                    comparacion.append('N/A')
                    comparacion.append('N/A')
                    info.append('N/A')
                info.append(line.currency_id.name) if line.currency_id else info.append('N/A')
                if producto == line.rt_service_product_id:
                    info.append(producto.regimen if producto.regimen else 'N/A')
                if producto == line.consolidado_service_product_id:
                    camion = producto.camion_id if producto.camion_id else producto.rt_carga_id.camion_id
                    info.append(producto.regimen if producto.regimen else camion.regimen if camion.regimen else 'N/A')
                if line.invoice_id.service_marfrig_ids:
                    info.append('expo_nat')
                if line.product_deposito_srv_id or not producto:
                    info.append('N/A')

                linea.append(comparacion)
                linea.append(info)
                if total:
                    if dolares:
                        if line.currency_id.name == 'UYU':
                            linea.append(line.price_subtotal/(tipo_cambio.rate))
                        else:
                            linea.append(line.price_subtotal)
                    else:
                        if line.currency_id.name == 'USD':
                            linea.append(line.price_subtotal*(tipo_cambio.rate))
                        else:
                            linea.append(line.price_subtotal)
                else:
                    linea.append(line.price_subtotal)
                if list_lineas:
                    for li in list_lineas:
                        if li[0] == comparacion:
                            existe = True
                            li[2] += linea[2]
                if not list_lineas or not existe:
                    list_lineas.append(linea)

        return list_lineas

    def obtener_clientes(self, facturas, total, dolares):
        dic_cliente = {}
        precio = 0
        precio_cliente = 0
        cliente_anterior = ''
        if facturas:
            for factura in facturas:
                if total:
                    tipo_cambio = self.env['res.currency.rate'].search([('name', '<=', factura.date_invoice), ('currency_id', '=', 2)], limit=1)
                    if dolares:
                        if factura.currency_id.name == 'UYU':
                            precio = factura.amount_untaxed/(tipo_cambio.rate)
                        else:
                            precio = factura.amount_untaxed
                    else:
                        if factura.currency_id.name == 'USD':
                            precio = factura.amount_untaxed*(tipo_cambio.rate)
                        else:
                            precio = factura.amount_untaxed
                else:
                    precio = factura.amount_untaxed
                if factura.type == 'out_refund':
                    precio = precio * (-1)
                cliente = factura.partner_id.name
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

    def get_report_name(self, start=None, stop=None):
        report_name = ''
        if start and stop:
            report_name = formatters.date_fmt(start.isoformat()[:10]) + ' - ' + formatters.date_fmt(stop.isoformat()[:10])
        return report_name

    def write_page_all(self, wb=None, facturas=None, total=None, dolares=None, nombre_filtro=None, fechas=None):
        fila = 4
        columna_inicio = 4
        columna_fin = 5
        inicio_cliente = 5
        cliente_anterior = False
        title = easyxf('font: name Calibri, bold True; alignment: horizontal left')
        title_number = easyxf('font: name Calibri; alignment: horizontal right',
                              num_format_str='#,##0.00;-#,##0.00;')
        lineas = easyxf('font: name Calibri; alignment: horizontal left')
        moneda = 'Original' + ' ' + facturas[0].currency_id.name
        if total:
            if dolares:
                moneda = 'USD'
            else:
                moneda = 'UYU'
        ws = wb.add_sheet(moneda, cell_overwrite_ok=True)
        ws.write_merge(fila - 3, fila - 3, 0, 2, fechas, title)
        if nombre_filtro:
            ws.write_merge(fila-2, fila-2, 0, 5, nombre_filtro, title)
        ws.write_merge(fila, fila, 0, 0, "Fecha", title)
        ws.write_merge(fila, fila, 1, 3, "Cliente a Facturar", title)
        if not self.partner_invoice_id:
            ws.write_merge(fila, fila, columna_inicio, (columna_fin+1), "Solicitante del viaje", title)
            columna_fin += 1
            columna_inicio = columna_fin + 1
            columna_fin += 2
        if not self.regimen:
            ws.write_merge(fila, fila, columna_inicio, columna_fin, "Regimen", title)
            columna_inicio += 2
            columna_fin += 2
        if not self.origin_id:
            ws.write_merge(fila, fila, columna_inicio, (columna_fin+1), "Origen", title)
            columna_fin += 1
            columna_inicio = columna_fin + 1
            columna_fin += 2
        if not self.destiny_id:
            ws.write_merge(fila, fila, columna_inicio, (columna_fin+1), "Destino", title)
            columna_fin += 1
            columna_inicio = columna_fin + 1
            columna_fin += 2
        ws.write_merge(fila, fila, columna_inicio, columna_inicio, "Moneda", title)
        ws.write_merge(fila, fila, (columna_inicio+1), (columna_fin+2), "Facturado Sin IVA", title)
        ws.write_merge(fila, fila, (columna_inicio+4), (columna_fin+4), "Nro Factura", title)
        ws.write_merge(fila, fila, (columna_inicio+6), (columna_fin+6), "Nota de Credito", title)
        formula_total = self.posicion_total(columna_inicio)
        if facturas:
            for factura in facturas:
                list_line = []
                list_line = self.agrupar_lineas(factura.invoice_line_ids, total, dolares, factura.date_invoice)
                for line in list_line:
                    fila += 1
                    columna_inicio = 4
                    columna_fin = 5
                    ws.write_merge(fila, fila, 0, 0, self.convertir_fecha(factura.date_invoice), lineas)
                    ws.write_merge(fila, fila, 1, 3, factura.partner_id.name, lineas)
                    if not self.partner_invoice_id:
                        ws.write_merge(fila, fila, columna_inicio, (columna_fin+1), line[1][0], lineas)
                        columna_fin += 1
                        columna_inicio = columna_fin + 1
                        columna_fin += 2
                    if not self.regimen:
                        if line[1][2] != 'N/A':
                            ws.write_merge(fila, fila, columna_inicio, columna_fin, self.map_regimen()[line[1][2]], lineas)
                        else:
                            ws.write_merge(fila, fila, columna_inicio, columna_fin, 'N/A', lineas)
                        columna_inicio += 2
                        columna_fin += 2
                    if not self.origin_id:
                        ws.write_merge(fila, fila, columna_inicio, (columna_fin+1), line[0][2], lineas)
                        columna_fin += 1
                        columna_inicio = columna_fin + 1
                        columna_fin += 2
                    if not self.destiny_id:
                        ws.write_merge(fila, fila, columna_inicio, (columna_fin+1), line[0][3], lineas)
                        columna_fin += 1
                        columna_inicio = columna_fin + 1
                        columna_fin += 2
                    ws.write_merge(fila, fila, columna_inicio, columna_inicio, line[1][1], title_number)
                    ws.write_merge(fila, fila, (columna_inicio + 1), (columna_fin + 2), line[2] * -1 if factura.type == 'out_refund' else line[2], title_number)
                    ws.write_merge(fila, fila, (columna_inicio + 4), (columna_fin + 4), self.get_numero_factura(factura), lineas)
                    ws.write_merge(fila, fila, (columna_inicio + 6), (columna_fin + 6), self.get_nota_de_credito(factura), lineas)
                    if cliente_anterior and cliente_anterior != factura.partner_id:
                        ws.write_merge((fila-1), (fila-1), (columna_inicio+8), (columna_inicio+8), 'Total Cli', title)
                        ws.write_merge((fila-1), (fila-1), (columna_inicio+9), (columna_inicio+9), Formula("SUM(Q%s :Q%s)" % (inicio_cliente+1, (fila))), title_number)
                        inicio_cliente = fila
                    cliente_anterior = factura.partner_id

            fila += 1
            ultima_fila = fila
            ws.write_merge((fila - 1), (fila - 1), (columna_inicio + 8), (columna_inicio + 8), 'Total Cliente', title)
            ws.write_merge((fila - 1), (fila - 1), (columna_inicio + 9), (columna_inicio + 9), Formula(formula_total % (inicio_cliente + 1, (fila))), title_number)
            ws.write(ultima_fila, columna_fin, "Total", title)
            primer_fila = 4
            ws.write_merge(fila, fila, columna_fin+1, columna_fin+2, Formula(formula_total % (primer_fila, ultima_fila)), title_number)

    def write_page_per_client(self, wb=None, facturas=None, total=None, dolares=None, nombre_filtro=None, fechas=None):
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
        # total_precio = easyxf('font: name Calibri, bold True ; alignment: horizontal left; pattern: pattern solid,'
        #                ' fore_colour pale_blue; borders: left_color black, top_color black, bottom_color black,\
        #                       left thin, top thin, bottom thin;')
        # fin = easyxf('borders: top_color black, top thin, left thin, right thin;')
        moneda = 'Cliente Original' + ' ' + facturas[0].currency_id.name
        title_moneda = facturas[0].currency_id.name
        if total:
            if dolares:
                moneda = 'Cliente USD'
                title_moneda = 'USD'
            else:
                moneda = 'Cliente UYU'
                title_moneda = 'UYU'
        ws = wb.add_worksheet(moneda)
        ws.merge_range('B1:I1', fechas, color_bold)
        ws.write(0, 0, '', color_bold)
        ws.merge_range('J1:L1', '', color_bold)
        ws.write(3, 0, '', color_bold)
        if nombre_filtro:
            ws.merge_range('A2:I3', nombre_filtro, title)
        else:
            ws.merge_range('A2:I3', '', title)
        ws.write(4, 0, "#", title_hashtag)
        ws.merge_range('B4:I5', "Cliente", title)
        ws.merge_range('J2:L3', title_moneda, title)
        ws.merge_range('J4:L5', "Facturado (Sin Impuesto)", color_bold)
        clientes = self.obtener_clientes(facturas, total, dolares)
        if clientes:
            for info in clientes:
                columna_fin += 1
                ws.write(columna_fin-1, 0, numero, color)
                ws.merge_range('B%s:I%s' % (columna_fin, columna_fin), info[0], lineas)
                ws.merge_range('J%s:L%s' % (columna_fin, columna_fin), info[1], number)
                numero += 1

            formula = "{=SUM(J4:J" + str(columna_fin) + ")}"
            ws.merge_range('K%s:L%s' % (columna_fin + 1, columna_fin + 1), formula, total_number)
            ws.merge_range('B%s:I%s' % (columna_fin+1, columna_fin+1), '', fin)
            ws.write(columna_fin, 9, "Total", total_title)

        top10 = wb.add_chart({'type': 'pie'})
        top10.add_series({
            'name': 'TOP 10',
            'categories': [moneda, 5, 1, 14, 1],
            'values': [moneda, 5, 9, 14, 9],

        })

        ws.insert_chart('O6', top10, {'x_scale': 1.2, 'y_scale': 1.2})

    @api.multi
    def informe_ventas_cliente(self):
        if self.info_type == 'operativa':
            return self.informe_ventas_cliente_operativa()
        if self.info_type == 'contabilidad':
            return self.informe_ventas_cliente_contabilidad()

    def informe_ventas_cliente_contabilidad(self):
        # Creo el 'Libro' y su 'Pagina'
        file_name = 'Informe Ventas Clientes Contabilidad - %s.xls' % self.get_report_name(start=self.start, stop=self.stop)
        fp = BytesIO()
        if self.tipo_informe == 'all':
            wb = Workbook(encoding='utf-8')
        if self.tipo_informe == 'summary':
            wb = xlsxwriter.Workbook(fp)
        dolares = False
        total = False
        start, stop = self.convert_date_to_datetime(self.start, self.stop)
        facturas_total, facturas_pesos, facturas_dolares = self.get_facturas(start, stop)
        lista_facturas = [facturas_pesos, facturas_dolares, facturas_total, facturas_total]
        contador = 1
        fechas = str(start)[:10] + ' / ' + str(stop)[:10]
        nombre_filtro = self.obtener_nombre_filtrado()
        for facturas in lista_facturas:
            if facturas:
                if contador == 3:
                    total = True
                if self.tipo_informe == 'all':
                    self.write_page_all(wb, facturas, total, dolares, nombre_filtro, fechas)
                if self.tipo_informe == 'summary':
                    self.write_page_per_client(wb, facturas, total, dolares, nombre_filtro, fechas)
                if total:
                    dolares = True
            contador += 1

        if not facturas_total:
            if self.partner_invoice_id or self.regimen or self.origin_id or self.destiny_id:
                raise Warning('No se encontraron lineas con esos filtros')
            else:
                raise Warning('No se encontraron lineas')

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
