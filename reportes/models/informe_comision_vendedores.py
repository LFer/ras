# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning
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
from collections import OrderedDict

MAP_REGIMEN = dict(regimen for regimen in [('transit_nat', '80 - Transito Nacional'), ('impo_nat', '10 - IMPO Nacional'), ('expo_nat', '40 - EXPO Nacional'), ('interno_plaza_nat', 'Interno Plaza Nacional'), ('interno_fiscal_nat', 'Interno Fiscal Nacional'), ('transit_inter_in', '80 - Transito Internacional Ingreso'), ('transit_inter_out', '80 - Transito Internacional Salida'), ('impo_inter', '10 - IMPO Internacional'), ('expo_inter', '40 - EXPO Internacional')])
MAP_MESES = {0: 'Enero',
             1: 'Febrero',
             2: 'Marzo',
             3: 'Abril',
             4: 'Mayo',
             5: 'Junio',
             6: 'Julio',
             7: 'Agosto',
             8: 'Setiembre',
             9: 'Octubre',
             10: 'Noviembre',
             11: 'Diciembre',

}
class InformeComisionVendedores(models.Model):
    _name = 'informe.comision.vendedores'

    def get_numero_factura_rt(self, invoice_line):
        numero_factura = ''
        for line in invoice_line:
            if line.invoice_id.type == 'out_invoice' and line.invoice_id.state != 'draft':
                if numero_factura:
                    numero_factura += ' / ' + str(line.invoice_id.fe_Serie) + '-' + str(line.invoice_id.fe_DocNro)
                else:
                    numero_factura = str(line.invoice_id.fe_Serie) + '-' + str(line.invoice_id.fe_DocNro)

        return numero_factura

    def get_nota_de_credito_rt(self, invoice_line):
        numero_factura = ''
        for line in invoice_line:
            if line.invoice_id.type == 'out_refund' and line.invoice_id.state != 'draft':
                if numero_factura:
                    numero_factura += ' / ' + str(line.invoice_id.fe_Serie) + '-' + str(line.invoice_id.fe_DocNro)
                else:
                    numero_factura = str(line.invoice_id.fe_Serie) + '-' + str(line.invoice_id.fe_DocNro)

        return numero_factura


    name = fields.Char()
    informe = fields.Selection([('informe', 'Informe'), ('list', 'Listado de Vendedores')], string='Tipo de Informe')
    start = fields.Datetime(string='Fecha Inicio', index=True, copy=False)
    stop = fields.Datetime(string='Fecha Fin', index=True, copy=False)
    partner_invoice_id = fields.Many2one(comodel_name='res.partner', string='Cliente a facturar', domain=[('customer', '=', True)], store=True)
    partner_seller_id = fields.Many2one(comodel_name='res.partner', string='Venedor', domain=[('seller', '=', True)], store=True)


    @api.multi
    @api.depends('name', 'start', 'stop')
    def name_get(self):
        return [(rec.id, '%s - %s' % (rec.start, rec.stop)) for rec in self]


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

    def get_importe(self, prod):
        currency = ''
        importe = 0
        for inv in prod.mrf_srv_id.invoices_ids:
            if prod in inv.service_marfrig_ids:
                for inv_line in inv.invoice_line_ids:
                    if inv_line.product_id.id == prod.product_id.id:
                        currency = inv_line.currency_id.name
                        importe = inv_line.price_subtotal

        return currency, importe


    def get_pesos(self, condiciones_busqueda):
        facturas = self.env['account.invoice']
        pesos = self.env['res.currency'].search([('name', '=', 'UYU')]).id
        condiciones_busqueda.append(('currency_id', '=', pesos))
        facturas_pesos = facturas.search(condiciones_busqueda)

        return facturas_pesos

    def get_dolares(self, condiciones_busqueda):
        #Si la lista viene con la condicion de busqueda para pesos, la reemplazamos por dolares
        # condiciones_busqueda.remove(('currency_id', '=', 46))
        facturas = self.env['account.invoice']
        dolares = self.env['res.currency'].search([('name', '=', 'USD')]).id
        condiciones_busqueda = list(map(lambda x: x if x != ('currency_id', '=', 46) else ('currency_id', '=', dolares), condiciones_busqueda))
        facturas_dolares = facturas.search(condiciones_busqueda)

        return facturas_dolares

    def get_productos_ordenados_por_mes(self, start, stop, vendedor):
        condiciones_busqueda = [('start', '>=', start), ('stop', '<=', stop), ('seller_commission', '!=', 0)]
        if vendedor:
            condiciones_busqueda.append(('partner_seller_id', '=', vendedor.id))

        productos = self.env['rt.service.productos'].search(condiciones_busqueda, order='start')
        productos_ordenados_por_mes = []
        productos_enero = []
        productos_febrero = []
        productos_marzo = []
        productos_abril = []
        productos_mayo = []
        productos_junio = []
        productos_julio = []
        productos_agosto = []
        productos_setiembre = []
        productos_octubre = []
        productos_noviembre = []
        productos_diciembre = []
        # datetime(year, month, day, hour, minute, second, microsecond)
        inicio_enero = datetime(2019, 1, 1, 00, 00, 00, 000000)
        fin_enero = datetime(2019, 1, 31, 23, 59, 59, 000000)

        inicio_febrero = datetime(2019, 2, 1, 00, 00, 00, 000000)
        fin_febrero = datetime(2019, 2, 28, 23, 59, 59, 000000)

        inicio_marzo = datetime(2019, 3, 1, 00, 00, 00, 000000)
        fin_marzo = datetime(2019, 3, 31, 23, 59, 59, 000000)

        inicio_abril = datetime(2019, 4, 1, 00, 00, 00, 000000)
        fin_abril = datetime(2019, 4, 30, 23, 59, 59, 000000)

        inicio_mayo = datetime(2019, 5, 1, 00, 00, 00, 000000)
        fin_mayo = datetime(2019, 5, 31, 23, 59, 59, 000000)

        inicio_junio = datetime(2019, 6, 1, 00, 00, 00, 000000)
        fin_junio = datetime(2019, 6, 30, 23, 59, 59, 000000)

        inicio_julio = datetime(2019, 7, 1, 00, 00, 00, 000000)
        fin_julio = datetime(2019, 7, 31, 23, 59, 59, 000000)

        inicio_agosto = datetime(2019, 8, 1, 00, 00, 00, 000000)
        fin_agosto = datetime(2019, 8, 31, 23, 59, 59, 000000)

        inicio_setiembre = datetime(2019, 9, 1, 00, 00, 00, 000000)
        fin_setiembre = datetime(2019, 9, 30, 23, 59, 59, 000000)

        inicio_octubre = datetime(2019, 10, 1, 00, 00, 00, 000000)
        fin_octubre = datetime(2019, 10, 31, 23, 59, 59, 000000)

        inicio_noviembre = datetime(2019, 11, 1, 00, 00, 00, 000000)
        fin_noviembre = datetime(2019, 11, 30, 23, 59, 59, 000000)

        inicio_diciembre = datetime(2019, 12, 1, 00, 00, 00, 000000)
        fin_diciembre = datetime(2019, 12, 31, 23, 59, 59, 000000)

        for prod in productos:
            if prod.start >= inicio_enero and prod.start <= fin_enero:
                productos_enero.append(prod.id)

            if prod.start >= inicio_febrero and prod.start <= fin_febrero:
                productos_febrero.append(prod.id)

            if prod.start >= inicio_marzo and prod.start <= fin_marzo:
                productos_marzo.append(prod.id)

            if prod.start >= inicio_abril and prod.start <= fin_abril:
                productos_abril.append(prod.id)

            if prod.start >= inicio_mayo and prod.start <= fin_mayo:
                productos_mayo.append(prod.id)

            if prod.start >= inicio_junio and prod.start <= fin_junio:
                productos_junio.append(prod.id)

            if prod.start >= inicio_julio and prod.start <= fin_julio:
                productos_julio.append(prod.id)

            if prod.start >= inicio_agosto and prod.start <= fin_agosto:
                productos_agosto.append(prod.id)

            if prod.start >= inicio_setiembre and prod.start <= fin_setiembre:
                productos_setiembre.append(prod.id)

            if prod.start >= inicio_octubre and prod.start <= fin_octubre:
                productos_octubre.append(prod.id)

            if prod.start >= inicio_noviembre and prod.start <= fin_noviembre:
                productos_noviembre.append(prod.id)

            if prod.start >= inicio_diciembre and prod.start <= fin_diciembre:
                productos_diciembre.append(prod.id)

        productos_ordenados_por_mes.append(productos_enero)
        productos_ordenados_por_mes.append(productos_febrero)
        productos_ordenados_por_mes.append(productos_marzo)
        productos_ordenados_por_mes.append(productos_abril)
        productos_ordenados_por_mes.append(productos_mayo)
        productos_ordenados_por_mes.append(productos_junio)
        productos_ordenados_por_mes.append(productos_julio)
        productos_ordenados_por_mes.append(productos_agosto)
        productos_ordenados_por_mes.append(productos_setiembre)
        productos_ordenados_por_mes.append(productos_octubre)
        productos_ordenados_por_mes.append(productos_noviembre)
        productos_ordenados_por_mes.append(productos_diciembre)
        return productos_ordenados_por_mes

    def get_productos_mafrig_ordenados_por_mes(self, start, stop, vendedor):
        condiciones_busqueda = [('start_datetime', '<=', stop), ('start_datetime', '>=', start)]
        if vendedor:
            condiciones_busqueda.append(('partner_seller_id', '=', vendedor.id))
        productos = self.env['marfrig.service.base'].search(condiciones_busqueda, order='start_datetime')
        productos_ordenados_por_mes = []
        productos_enero = []
        productos_febrero = []
        productos_marzo = []
        productos_abril = []
        productos_mayo = []
        productos_junio = []
        productos_julio = []
        productos_agosto = []
        productos_setiembre = []
        productos_octubre = []
        productos_noviembre = []
        productos_diciembre = []
        # datetime(year, month, day, hour, minute, second, microsecond)
        inicio_enero = datetime(2019, 1, 1, 00, 00, 00, 000000)
        fin_enero = datetime(2019, 1, 31, 23, 59, 59, 000000)

        inicio_febrero = datetime(2019, 2, 1, 00, 00, 00, 000000)
        fin_febrero = datetime(2019, 2, 28, 23, 59, 59, 000000)

        inicio_marzo = datetime(2019, 3, 1, 00, 00, 00, 000000)
        fin_marzo = datetime(2019, 3, 31, 23, 59, 59, 000000)

        inicio_abril = datetime(2019, 4, 1, 00, 00, 00, 000000)
        fin_abril = datetime(2019, 4, 30, 23, 59, 59, 000000)

        inicio_mayo = datetime(2019, 5, 1, 00, 00, 00, 000000)
        fin_mayo = datetime(2019, 5, 31, 23, 59, 59, 000000)

        inicio_junio = datetime(2019, 6, 1, 00, 00, 00, 000000)
        fin_junio = datetime(2019, 6, 30, 23, 59, 59, 000000)

        inicio_julio = datetime(2019, 7, 1, 00, 00, 00, 000000)
        fin_julio = datetime(2019, 7, 31, 23, 59, 59, 000000)

        inicio_agosto = datetime(2019, 8, 1, 00, 00, 00, 000000)
        fin_agosto = datetime(2019, 8, 31, 23, 59, 59, 000000)

        inicio_setiembre = datetime(2019, 9, 1, 00, 00, 00, 000000)
        fin_setiembre = datetime(2019, 9, 30, 23, 59, 59, 000000)

        inicio_octubre = datetime(2019, 10, 1, 00, 00, 00, 000000)
        fin_octubre = datetime(2019, 10, 31, 23, 59, 59, 000000)

        inicio_noviembre = datetime(2019, 11, 1, 00, 00, 00, 000000)
        fin_noviembre = datetime(2019, 11, 30, 23, 59, 59, 000000)

        inicio_diciembre = datetime(2019, 12, 1, 00, 00, 00, 000000)
        fin_diciembre = datetime(2019, 12, 31, 23, 59, 59, 000000)
        for prod in productos:
            if prod.start_datetime >= inicio_enero and prod.start_datetime <= fin_enero:
                productos_enero.append(prod.id)

            if prod.start_datetime >= inicio_febrero and prod.start_datetime <= fin_febrero:
                productos_febrero.append(prod.id)

            if prod.start_datetime >= inicio_marzo and prod.start_datetime <= fin_marzo:
                productos_marzo.append(prod.id)

            if prod.start_datetime >= inicio_abril and prod.start_datetime <= fin_abril:
                productos_abril.append(prod.id)

            if prod.start_datetime >= inicio_mayo and prod.start_datetime <= fin_mayo:
                productos_mayo.append(prod.id)

            if prod.start_datetime >= inicio_junio and prod.start_datetime <= fin_junio:
                productos_junio.append(prod.id)

            if prod.start_datetime >= inicio_julio and prod.start_datetime <= fin_julio:
                productos_julio.append(prod.id)

            if prod.start_datetime >= inicio_agosto and prod.start_datetime <= fin_agosto:
                productos_agosto.append(prod.id)

            if prod.start_datetime >= inicio_setiembre and prod.start_datetime <= fin_setiembre:
                productos_setiembre.append(prod.id)

            if prod.start_datetime >= inicio_octubre and prod.start_datetime <= fin_octubre:
                productos_octubre.append(prod.id)

            if prod.start_datetime >= inicio_noviembre and prod.start_datetime <= fin_noviembre:
                productos_noviembre.append(prod.id)

            if prod.start_datetime >= inicio_diciembre and prod.start_datetime <= fin_diciembre:
                productos_diciembre.append(prod.id)


        productos_ordenados_por_mes.append(productos_enero)
        productos_ordenados_por_mes.append(productos_febrero)
        productos_ordenados_por_mes.append(productos_marzo)
        productos_ordenados_por_mes.append(productos_abril)
        productos_ordenados_por_mes.append(productos_mayo)
        productos_ordenados_por_mes.append(productos_junio)
        productos_ordenados_por_mes.append(productos_julio)
        productos_ordenados_por_mes.append(productos_agosto)
        productos_ordenados_por_mes.append(productos_setiembre)
        productos_ordenados_por_mes.append(productos_octubre)
        productos_ordenados_por_mes.append(productos_noviembre)
        productos_ordenados_por_mes.append(productos_diciembre)
        return productos_ordenados_por_mes

    def dame_todos_los_productos(self, consolidado):
        productos_ids = []
        for consol in consolidado:
            for carga in consol.cargas_ids:
                for prod in carga.producto_servicio_carga_ids:
                    if prod.partner_seller_id:
                        if self.partner_seller_id == prod.partner_seller_id:
                            productos_ids.append(prod.id)
                        else:
                            productos_ids.append(prod.id)
            for prod in consol.productos_servicios_camion_ids:
                if prod.partner_seller_id:
                    if self.partner_seller_id == prod.partner_seller_id:
                        productos_ids.append(prod.id)
                    else:
                        productos_ids.append(prod.id)
        return productos_ids

    def get_productos_consol_ordenados_por_mes(self, start, stop):
        condiciones_busqueda = [('start_datetime', '<=', stop), ('start_datetime', '>=', start)]
        consolidados = self.env['carpeta.camion'].search(condiciones_busqueda, order='start_datetime')

        productos_ordenados_por_mes = []
        productos_enero = []
        productos_febrero = []
        productos_marzo = []
        productos_abril = []
        productos_mayo = []
        productos_junio = []
        productos_julio = []
        productos_agosto = []
        productos_setiembre = []
        productos_octubre = []
        productos_noviembre = []
        productos_diciembre = []
        # datetime(year, month, day, hour, minute, second, microsecond)
        inicio_enero = datetime(2019, 1, 1, 00, 00, 00, 000000)
        fin_enero = datetime(2019, 1, 31, 23, 59, 59, 000000)

        inicio_febrero = datetime(2019, 2, 1, 00, 00, 00, 000000)
        fin_febrero = datetime(2019, 2, 28, 23, 59, 59, 000000)

        inicio_marzo = datetime(2019, 3, 1, 00, 00, 00, 000000)
        fin_marzo = datetime(2019, 3, 31, 23, 59, 59, 000000)

        inicio_abril = datetime(2019, 4, 1, 00, 00, 00, 000000)
        fin_abril = datetime(2019, 4, 30, 23, 59, 59, 000000)

        inicio_mayo = datetime(2019, 5, 1, 00, 00, 00, 000000)
        fin_mayo = datetime(2019, 5, 31, 23, 59, 59, 000000)

        inicio_junio = datetime(2019, 6, 1, 00, 00, 00, 000000)
        fin_junio = datetime(2019, 6, 30, 23, 59, 59, 000000)

        inicio_julio = datetime(2019, 7, 1, 00, 00, 00, 000000)
        fin_julio = datetime(2019, 7, 31, 23, 59, 59, 000000)

        inicio_agosto = datetime(2019, 8, 1, 00, 00, 00, 000000)
        fin_agosto = datetime(2019, 8, 31, 23, 59, 59, 000000)

        inicio_setiembre = datetime(2019, 9, 1, 00, 00, 00, 000000)
        fin_setiembre = datetime(2019, 9, 30, 23, 59, 59, 000000)

        inicio_octubre = datetime(2019, 10, 1, 00, 00, 00, 000000)
        fin_octubre = datetime(2019, 10, 31, 23, 59, 59, 000000)

        inicio_noviembre = datetime(2019, 11, 1, 00, 00, 00, 000000)
        fin_noviembre = datetime(2019, 11, 30, 23, 59, 59, 000000)

        inicio_diciembre = datetime(2019, 12, 1, 00, 00, 00, 000000)
        fin_diciembre = datetime(2019, 12, 31, 23, 59, 59, 000000)

        for camion in consolidados:
            if camion.start_datetime >= inicio_enero and camion.start_datetime <= fin_enero:
                productos_camion = self.dame_todos_los_productos(consolidado=camion)
                if productos_camion:
                    for prod in productos_camion:
                        productos_enero.append(prod)

            if camion.start_datetime >= inicio_febrero and camion.start_datetime <= fin_febrero:
                productos_camion = self.dame_todos_los_productos(consolidado=camion)
                if productos_camion:
                    for prod in productos_camion:
                        productos_febrero.append(prod)

            if camion.start_datetime >= inicio_marzo and camion.start_datetime <= fin_marzo:
                productos_camion = self.dame_todos_los_productos(consolidado=camion)
                if productos_camion:
                    for prod in productos_camion:
                        productos_marzo.append(prod)

            if camion.start_datetime >= inicio_abril and camion.start_datetime <= fin_abril:
                productos_camion = self.dame_todos_los_productos(consolidado=camion)
                if productos_camion:
                    for prod in productos_camion:
                        productos_abril.append(prod)

            if camion.start_datetime >= inicio_mayo and camion.start_datetime <= fin_mayo:
                productos_camion = self.dame_todos_los_productos(consolidado=camion)
                if productos_camion:
                    for prod in productos_camion:
                        productos_mayo.append(prod)

            if camion.start_datetime >= inicio_junio and camion.start_datetime <= fin_junio:
                productos_camion = self.dame_todos_los_productos(consolidado=camion)
                if productos_camion:
                    for prod in productos_camion:
                        productos_junio.append(prod)

            if camion.start_datetime >= inicio_julio and camion.start_datetime <= fin_julio:
                productos_camion = self.dame_todos_los_productos(consolidado=camion)
                if productos_camion:
                    for prod in productos_camion:
                        productos_julio.append(prod)

            if camion.start_datetime >= inicio_agosto and camion.start_datetime <= fin_agosto:
                productos_camion = self.dame_todos_los_productos(consolidado=camion)
                if productos_camion:
                    for prod in productos_camion:
                        productos_agosto.append(prod)

            if camion.start_datetime >= inicio_setiembre and camion.start_datetime <= fin_setiembre:
                productos_camion = self.dame_todos_los_productos(consolidado=camion)
                if productos_camion:
                    for prod in productos_camion:
                        productos_setiembre.append(prod)

            if camion.start_datetime >= inicio_octubre and camion.start_datetime <= fin_octubre:
                productos_camion = self.dame_todos_los_productos(consolidado=camion)
                if productos_camion:
                    for prod in productos_camion:
                        productos_octubre.append(prod)

            if camion.start_datetime >= inicio_noviembre and camion.start_datetime <= fin_noviembre:
                productos_camion = self.dame_todos_los_productos(consolidado=camion)
                if productos_camion:
                    for prod in productos_camion:
                        productos_noviembre.append(prod)

            if camion.start_datetime >= inicio_diciembre and camion.start_datetime <= fin_diciembre:
                productos_camion = self.dame_todos_los_productos(consolidado=camion)
                if productos_camion:
                    for prod in productos_camion:
                        productos_diciembre.append(prod)

        productos_ordenados_por_mes.append(productos_enero)
        productos_ordenados_por_mes.append(productos_febrero)
        productos_ordenados_por_mes.append(productos_marzo)
        productos_ordenados_por_mes.append(productos_abril)
        productos_ordenados_por_mes.append(productos_mayo)
        productos_ordenados_por_mes.append(productos_junio)
        productos_ordenados_por_mes.append(productos_junio)
        productos_ordenados_por_mes.append(productos_agosto)
        productos_ordenados_por_mes.append(productos_setiembre)
        productos_ordenados_por_mes.append(productos_octubre)
        productos_ordenados_por_mes.append(productos_noviembre)
        productos_ordenados_por_mes.append(productos_diciembre)
        return productos_ordenados_por_mes

    def get_productos_depo_ordenados_por_mes(self, start, stop, vendedor):
        condiciones_busqueda = [('start', '>=', start), ('stop', '<=', stop), ('seller_commission', '!=', 0)]
        if vendedor:
            condiciones_busqueda.append(('partner_seller_id', '=', vendedor.id))

        productos = self.env['deposito.service.products'].search(condiciones_busqueda, order='start')
        productos_ordenados_por_mes = []
        productos_enero = []
        productos_febrero = []
        productos_marzo = []
        productos_abril = []
        productos_mayo = []
        productos_junio = []
        productos_julio = []
        productos_agosto = []
        productos_setiembre = []
        productos_octubre = []
        productos_noviembre = []
        productos_diciembre = []
        # datetime(year, month, day, hour, minute, second, microsecond)
        inicio_enero = datetime(2019, 1, 1, 00, 00, 00, 000000)
        fin_enero = datetime(2019, 1, 31, 23, 59, 59, 000000)

        inicio_febrero = datetime(2019, 2, 1, 00, 00, 00, 000000)
        fin_febrero = datetime(2019, 2, 28, 23, 59, 59, 000000)

        inicio_marzo = datetime(2019, 3, 1, 00, 00, 00, 000000)
        fin_marzo = datetime(2019, 3, 31, 23, 59, 59, 000000)

        inicio_abril = datetime(2019, 4, 1, 00, 00, 00, 000000)
        fin_abril = datetime(2019, 4, 30, 23, 59, 59, 000000)

        inicio_mayo = datetime(2019, 5, 1, 00, 00, 00, 000000)
        fin_mayo = datetime(2019, 5, 31, 23, 59, 59, 000000)

        inicio_junio = datetime(2019, 6, 1, 00, 00, 00, 000000)
        fin_junio = datetime(2019, 6, 30, 23, 59, 59, 000000)

        inicio_julio = datetime(2019, 7, 1, 00, 00, 00, 000000)
        fin_julio = datetime(2019, 7, 31, 23, 59, 59, 000000)

        inicio_agosto = datetime(2019, 8, 1, 00, 00, 00, 000000)
        fin_agosto = datetime(2019, 8, 31, 23, 59, 59, 000000)

        inicio_setiembre = datetime(2019, 9, 1, 00, 00, 00, 000000)
        fin_setiembre = datetime(2019, 9, 30, 23, 59, 59, 000000)

        inicio_octubre = datetime(2019, 10, 1, 00, 00, 00, 000000)
        fin_octubre = datetime(2019, 10, 31, 23, 59, 59, 000000)

        inicio_noviembre = datetime(2019, 11, 1, 00, 00, 00, 000000)
        fin_noviembre = datetime(2019, 11, 30, 23, 59, 59, 000000)

        inicio_diciembre = datetime(2019, 12, 1, 00, 00, 00, 000000)
        fin_diciembre = datetime(2019, 12, 31, 23, 59, 59, 000000)

        for prod in productos:
            if prod.start >= inicio_enero and prod.start <= fin_enero:
                productos_enero.append(prod.id)

            if prod.start >= inicio_febrero and prod.start <= fin_febrero:
                productos_febrero.append(prod.id)

            if prod.start >= inicio_marzo and prod.start <= fin_marzo:
                productos_marzo.append(prod.id)

            if prod.start >= inicio_abril and prod.start <= fin_abril:
                productos_abril.append(prod.id)

            if prod.start >= inicio_mayo and prod.start <= fin_mayo:
                productos_mayo.append(prod.id)

            if prod.start >= inicio_junio and prod.start <= fin_junio:
                productos_junio.append(prod.id)

            if prod.start >= inicio_julio and prod.start <= fin_julio:
                productos_julio.append(prod.id)

            if prod.start >= inicio_agosto and prod.start <= fin_agosto:
                productos_agosto.append(prod.id)

            if prod.start >= inicio_setiembre and prod.start <= fin_setiembre:
                productos_setiembre.append(prod.id)

            if prod.start >= inicio_octubre and prod.start <= fin_octubre:
                productos_octubre.append(prod.id)

            if prod.start >= inicio_noviembre and prod.start <= fin_noviembre:
                productos_noviembre.append(prod.id)

            if prod.start >= inicio_diciembre and prod.start <= fin_diciembre:
                productos_diciembre.append(prod.id)

        productos_ordenados_por_mes.append(productos_enero)
        productos_ordenados_por_mes.append(productos_febrero)
        productos_ordenados_por_mes.append(productos_marzo)
        productos_ordenados_por_mes.append(productos_abril)
        productos_ordenados_por_mes.append(productos_mayo)
        productos_ordenados_por_mes.append(productos_junio)
        productos_ordenados_por_mes.append(productos_julio)
        productos_ordenados_por_mes.append(productos_agosto)
        productos_ordenados_por_mes.append(productos_setiembre)
        productos_ordenados_por_mes.append(productos_octubre)
        productos_ordenados_por_mes.append(productos_noviembre)
        productos_ordenados_por_mes.append(productos_diciembre)
        return productos_ordenados_por_mes

    def get_report_name(self, start=None, stop=None, vendedor=None):
        report_name = ''
        if start and stop:
            report_name = formatters.date_fmt(start.isoformat()[:10]) + ' - ' + formatters.date_fmt(stop.isoformat()[:10])
            if self.partner_seller_id:
                report_name = formatters.date_fmt(start.isoformat()[:10]) + ' - ' + formatters.date_fmt(stop.isoformat()[:10]) + ' - ' + self.partner_seller_id.name

        return report_name

    def this_actually_returns_the_recepit_number(self, invoice_line=None, invoice=None):
        recepit_number = ''
        no_pago = False
        if invoice_line:
            for line in invoice_line:
                if line.invoice_id.state != 'paid':
                    no_pago = True
                else:
                    no_pago = False
                if line.invoice_id.payment_ids:
                    for pay in line.invoice_id.payment_ids:
                        recepit_number += pay.communication + ' | '
                elif line.invoice_id.payment_move_line_ids:
                    for pay in line.invoice_id.payment_move_line_ids:
                        if pay.ref:
                            recepit_number += pay.ref + ' | '
                        else:
                            recepit_number += 'Sin Referencia?'

        if invoice:
            for inv in invoice:
                if inv.state != 'paid':
                    no_pago = True
                else:
                    no_pago = False
                if inv.payment_ids:
                    for pay in inv.payment_ids:
                        recepit_number += pay.communication + ' | '
                elif inv.payment_move_line_ids:
                    for pay in inv.payment_move_line_ids:
                        if pay.ref:
                            recepit_number += pay.ref + ' | '
                        else:
                            recepit_number += 'Sin Referencia?'

        if no_pago:
            recepit_number = 'No Pago'
        return recepit_number

    def return_recepit_number(self, rt_service_product_id=None, producto_marfrig=None, producto_consol=None, productos_depo=None):
        recepit_number = ''
        # inv_line.invoice_id.payment_ids
        ail_obj = self.env['account.invoice.line']
        if rt_service_product_id:
            inv_line = ail_obj.search([('rt_service_product_id', '=', rt_service_product_id.id)])
            if inv_line:
                numero_recibo = self.this_actually_returns_the_recepit_number(invoice_line=inv_line)
                if numero_recibo == 'No Pago':
                    recepit_number = numero_recibo
                else:
                    recepit_number += numero_recibo

        if producto_marfrig:
            for inv in producto_marfrig.mrf_srv_id.invoices_ids:
                if producto_marfrig in inv.service_marfrig_ids:
                    for inv_line in inv.invoice_line_ids:
                        if inv_line.product_id.id == producto_marfrig.product_id.id:
                            numero_recibo = self.this_actually_returns_the_recepit_number(invoice_line=inv_line)
                            if numero_recibo == 'No Pago':
                                recepit_number = numero_recibo
                            else:
                                recepit_number += numero_recibo

        if producto_consol:
            if producto_consol:
                inv_line = ail_obj.search([('consolidado_service_product_id', '=', producto_consol.id)])
                for line in inv_line:
                    numero_recibo = self.this_actually_returns_the_recepit_number(invoice_line=line)
                    if numero_recibo == 'No Pago':
                        recepit_number = numero_recibo
                    else:
                        recepit_number += numero_recibo

        if productos_depo:
            inv_line = ail_obj.search([('product_deposito_srv_id', '=', productos_depo.id)])
            if inv_line:
                numero_recibo = self.this_actually_returns_the_recepit_number(invoice_line=inv_line)
                if numero_recibo == 'No Pago':
                    recepit_number = numero_recibo
                else:
                    recepit_number += numero_recibo

        return recepit_number[:-3] if recepit_number != 'No Pago' else recepit_number

    def return_invoice_number(self, rt_service_product_id=None, producto_marfrig=None, producto_consol=None, productos_depo=None):
        inv_number = ''
        ail_obj = self.env['account.invoice.line']
        if rt_service_product_id:
            if rt_service_product_id.rt_service_id.state in ['inprocess', 'progress', 'invoice_rejected']:
                inv_line = ail_obj.search([('rt_service_product_id', '=', rt_service_product_id.id)])
                for line in inv_line:
                    inv_number += str(line.invoice_id.fe_Serie) + '-' + str(line.invoice_id.fe_DocNro) + ' | ' if line.invoice_id.fe_Serie else ''
                if not inv_number:
                    inv_number += 'Factura Borrador!!!'
            else:
                inv_number += 'Carpeta No Facturada!!!'

        if producto_marfrig:
            if producto_marfrig.mrf_srv_id.state in ['inprocess', 'progress', 'invoiced', 'invoice_rejected', 'partially_invoiced', 'totally_invoiced']:
                if producto_marfrig.mrf_srv_id.invoices_ids:
                    for inv in producto_marfrig.mrf_srv_id.invoices_ids:
                        if producto_marfrig in inv.service_marfrig_ids:
                            if inv_number != 'Factura Borrador!!!':
                                inv_number += str(inv.fe_Serie) + '-' + str(inv.fe_DocNro) + ' | ' if inv.fe_Serie else ''
                            else:
                                inv_number = str(inv.fe_Serie) + '-' + str(
                                    inv.fe_DocNro) + ' | ' if inv.fe_Serie else ''
                        if not inv_number:
                            inv_number += 'Factura Borrador!!!'
            else:
                inv_number += 'Carpeta No Facturada!!!'

        if producto_consol:
            camion = producto_consol.camion_id if producto_consol.camion_id else producto_consol.rt_carga_id.camion_id if producto_consol.rt_carga_id and producto_consol.rt_carga_id.camion_id else 'N/A'
            if camion.state in ['inprocess', 'progress', 'progress_national', 'progress_international', 'rejected']:
                inv_line = ail_obj.search([('consolidado_service_product_id', '=', producto_consol.id)])
                for line in inv_line:
                    inv_number += str(line.invoice_id.fe_Serie) + '-' + str(line.invoice_id.fe_DocNro) + ' | '
                if not inv_number:
                    inv_number += 'Factura Borrador!!!'
            else:
                inv_number += 'Carpeta No Facturada!!!'

        if productos_depo:
            if productos_depo.deposito_srv_id.state in ['inprocess', 'invoiced', 'invoice_rejected']:
                inv_line = ail_obj.search([('product_deposito_srv_id', '=', productos_depo.id)])
                for line in inv_line:
                    inv_number += str(line.invoice_id.fe_Serie) + '-' + str(line.invoice_id.fe_DocNro) + ' | ' if line.invoice_id.fe_Serie else ''
                if not inv_number:
                    inv_number += 'Factura Borrador!!!'
            else:
                inv_number += 'Carpeta No Facturada!!!'

        return inv_number[:-3]

    def write_page_per_driver(self, wb=None, productos=None, posicion=None, carpetas_marfrig=None, productos_consol=None, productos_depo=None):
        fila = 4
        fila_inicio = 6
        fila_fin = 7
        total_uyu = 0
        total_usd = 0
        lineas_no_pago = easyxf('font: name Calibri; alignment: horizontal left; pattern: pattern solid,'
                       ' fore_colour light_yellow;')
        title_number_no_pago = easyxf('font: name Calibri; alignment: horizontal right; pattern: pattern solid,'
                       ' fore_colour light_yellow;', num_format_str='#,##0.00;-#,##0.00;')
        lineas_borrador = easyxf('font: name Calibri; alignment: horizontal left; pattern: pattern solid,'
                                ' fore_colour pale_blue;')
        title_number_borrador = easyxf('font: name Calibri; alignment: horizontal right; pattern: pattern solid,'
                                      ' fore_colour pale_blue;', num_format_str='#,##0.00;-#,##0.00;')
        lineas_pago = easyxf('font: name Calibri; alignment: horizontal left')
        title_number_pago = easyxf('font: name Calibri; alignment: horizontal right',
                              num_format_str='#,##0.00;-#,##0.00;')
        lineas_marfrig = easyxf('font: name Calibri; alignment: horizontal left; pattern: pattern solid,'
                                 ' fore_colour light_green;')
        title_number_marfrig = easyxf('font: name Calibri; alignment: horizontal right; pattern: pattern solid,'
                                       ' fore_colour light_green;', num_format_str='#,##0.00;-#,##0.00;')
        title = easyxf('font: name Calibri, bold True; alignment: horizontal left', num_format_str='#,##0.00;-#,##0.00;')
        total_number = easyxf('font: name Calibri, bold True; alignment: horizontal right')
        ws = wb.add_sheet(MAP_MESES[posicion], cell_overwrite_ok=True)
        ws.write(0, 0, self.env['res.company'].browse(1).name, title)
        ws.write(0, 5, formatters.date_fmt(fields.Date.today().isoformat()), title)

        prod_obj = self.env['rt.service.productos']
        carpetas_marfrig_obj = self.env['marfrig.service.base']
        prod_consol_obj = self.env['producto.servicio.camion']
        prod_depo_obj = self.env['deposito.service.products']
        ws.write(fila, 0, "Fecha", title)
        ws.write(fila, 1, "Carpeta", title)
        ws.write(fila, 2, "Vendedor", title)
        ws.write(fila, 3, "Comisión UYU", title)
        ws.write(fila, 4, "Comisión USD", title)
        ws.write(fila, 5, "Moneda Comisión", title)
        ws.write(fila, 6, "Regimen", title)
        ws.write(fila, 7, "Moneda Venta USD", title)
        ws.write(fila, 8, "Cliente", title)
        ws.write(fila, 9, "Dueño de la Mercaderia", title)
        ws.write(fila, 10, "Tipo de Carga", title)
        ws.write(fila, 11, "Internacional/Nacional", title)
        ws.write(fila, 12, "Venta USD", title)
        ws.write(fila, 13, "Venta UYU", title)
        ws.write(fila, 14, "Factura", title)
        ws.write(fila, 15, "Recibo", title)
        fila += 1

        if productos:
            for prod in prod_obj.browse(productos):
                recipt_number = self.return_recepit_number(rt_service_product_id=prod)
                invoice_number = self.return_invoice_number(rt_service_product_id=prod)
                if recipt_number == 'No Pago' and invoice_number not in ['Factura Borrador', 'Carpeta No Facturada']:
                    lineas = lineas_no_pago
                    title_number = title_number_no_pago
                else:
                    if invoice_number in ['Factura Borrador', 'Carpeta No Facturada']:
                        lineas = lineas_borrador
                        title_number = title_number_borrador
                    else:
                        lineas = lineas_pago
                        title_number = title_number_pago
                ws.write(fila, 0, self.convertir_fecha(prod.start), lineas)
                ws.write(fila, 1, ((prod.rt_service_id.name if prod.rt_service_id else 'N/A SERVICE') + ' - ' + (prod.rt_carga_id.seq if prod.rt_carga_id else 'N/A SERVICE')), lineas)
                ws.write(fila, 2, prod.partner_seller_id.name, lineas)
                if prod.currency_id_vendedor.name == 'UYU':
                    if recipt_number and recipt_number != 'No Pago':
                        total_uyu += prod.seller_commission
                    ws.write(fila, 3, prod.seller_commission, title_number)
                    ws.write(fila, 4, '', title_number)
                if prod.currency_id_vendedor.name == 'USD':
                    if recipt_number and recipt_number != 'No Pago':
                        total_usd += prod.seller_commission
                    ws.write(fila, 3, '', title_number)
                    ws.write(fila, 4, prod.seller_commission, title_number)
                ws.write(fila, 5, prod.currency_id_vendedor.name, lineas)
                ws.write(fila, 6, MAP_REGIMEN[prod.regimen if prod.regimen else 'transit_nat'], lineas)
                ws.write(fila, 7, prod.currency_id.name, lineas)
                ws.write(fila, 8, prod.partner_invoice_id.name, lineas)
                ws.write(fila, 9, prod.partner_id.name, lineas)
                ws.write(fila, 10, 'Contenedor' if prod.rt_carga_id.load_type == 'contenedor' else 'Carga Suelta', lineas)
                ws.write(fila, 11, 'Nacional' if prod.rt_service_id.operation_type == 'national' else 'Internacional' if prod.rt_service_id.operation_type == 'international' else 'NOPE', lineas)
                if prod.currency_id.name == 'USD':
                    ws.write(fila, 12, prod.importe, title_number)
                    ws.write(fila, 13, '', title_number)
                if prod.currency_id.name == 'UYU':
                    ws.write(fila, 12, '', title_number)
                    ws.write(fila, 13, prod.importe, title_number)
                ws.write(fila, 14, self.return_invoice_number(rt_service_product_id=prod), title_number)
                ws.write(fila, 15, self.return_recepit_number(rt_service_product_id=prod), title_number)
                fila += 1

        if carpetas_marfrig:
            for carpeta in carpetas_marfrig_obj.browse(carpetas_marfrig):
                if carpeta.seller_commission:
                    ws.write(fila, 0, self.convertir_fecha(carpeta.start_datetime), lineas_marfrig)
                    ws.write(fila, 1, carpeta.name, lineas_marfrig)
                    ws.write(fila, 2, carpeta.partner_seller_id.name, lineas_marfrig)
                    if carpeta.currency_id_vendedor.name == 'UYU':
                        if recipt_number and recipt_number != 'No Pago':
                            total_uyu += carpeta.seller_commission
                        ws.write(fila, 3, carpeta.seller_commission, title_number_marfrig)
                        ws.write(fila, 4, '', title_number_marfrig)
                    if carpeta.currency_id_vendedor.name == 'USD':
                        if recipt_number and recipt_number != 'No Pago':
                            total_usd += carpeta.seller_commission
                        ws.write(fila, 3, '', title_number_marfrig)
                        ws.write(fila, 4, carpeta.seller_commission, title_number_marfrig)
                    ws.write(fila, 5, carpeta.currency_id_vendedor.name, lineas_marfrig)
                    ws.write(fila, 6, 'Expo', lineas_marfrig)
                    ws.write(fila, 7, carpeta.currency_id.name, lineas_marfrig)
                    ws.write(fila, 8, self.env['res.partner'].search([('name', 'ilike', 'Marfrig')], limit=1).name, lineas_marfrig)
                    ws.write(fila, 9, self.env['res.partner'].search([('name', 'ilike', 'Marfrig')], limit=1).name, lineas_marfrig)
                    ws.write(fila, 10, 'Contenedor', lineas_marfrig)
                    ws.write(fila, 11, 'Nacional', lineas_marfrig)
                    ws.write(fila, 12, '', title_number_marfrig)
                    ws.write(fila, 13, '', title_number_marfrig)
                    ws.write(fila, 14, '', title_number_marfrig)
                    ws.write(fila, 15, '', title_number_marfrig)
                    fila += 1
                    for prod in carpeta.mrf_srv_ids:
                        if prod.is_invoiced:
                            currency, importe = self.get_importe(prod)
                            recipt_number = self.return_recepit_number(producto_marfrig=prod)
                            invoice_number = self.return_invoice_number(producto_marfrig=prod)
                            if recipt_number == 'No Pago':
                                lineas = lineas_no_pago
                                title_number = title_number_no_pago
                            else:
                                if invoice_number in ['Factura Borrador', 'Carpeta No Facturada']:
                                    lineas = lineas_borrador
                                    title_number = title_number_borrador
                                else:
                                    lineas = lineas_pago
                                    title_number = title_number_pago
                            ws.write(fila, 0, self.convertir_fecha(prod.start), lineas)
                            ws.write(fila, 1, '', lineas)
                            ws.write(fila, 2, carpeta.partner_seller_id.name, lineas)
                            ws.write(fila, 3, '', title_number)
                            ws.write(fila, 4, '', title_number)
                            ws.write(fila, 5, '', lineas)
                            ws.write(fila, 6, 'Expo', lineas)
                            ws.write(fila, 7, prod.currency_id.name, lineas)
                            ws.write(fila, 8, self.env['res.partner'].search([('name', 'ilike', 'Marfrig')], limit=1).name, lineas)
                            ws.write(fila, 9, self.env['res.partner'].search([('name', 'ilike', 'Marfrig')], limit=1).name, lineas)
                            ws.write(fila, 10, 'Contenedor', lineas)
                            ws.write(fila, 11, 'Nacional', lineas)
                            if currency == 'UYU':
                                ws.write(fila, 12, '', title_number)
                                ws.write(fila, 13, importe, title_number)
                            if currency == 'USD':
                                ws.write(fila, 12, importe, title_number)
                                ws.write(fila, 13, '', title_number)
                            if not currency and not importe:
                                ws.write(fila, 12, '', title_number)
                                ws.write(fila, 13, '', title_number)
                            ws.write(fila, 14, self.return_invoice_number(producto_marfrig=prod), title_number)
                            ws.write(fila, 15, self.return_recepit_number(producto_marfrig=prod), title_number)
                            fila += 1

        if productos_consol:
            for prod in prod_consol_obj.browse(productos_consol):
                recipt_number = self.return_recepit_number(producto_consol=prod)
                invoice_number = self.return_invoice_number(producto_consol=prod)
                if recipt_number == 'No Pago':
                    lineas = lineas_no_pago
                    title_number = title_number_no_pago
                else:
                    if invoice_number in ['Factura Borrador', 'Carpeta No Facturada']:
                        lineas = lineas_borrador
                        title_number = title_number_borrador
                    else:
                        lineas = lineas_pago
                        title_number = title_number_pago
                carga = prod.rt_carga_id
                camion = prod.camion_id if prod.camion_id else carga.camion_id
                if prod.seller_commission:
                    if self.partner_seller_id:
                        if prod.partner_seller_id.id == self.partner_seller_id.id:
                            ws.write(fila, 0, self.convertir_fecha(camion.start_datetime), lineas)
                            ws.write(fila, 1, ((camion.name if camion else 'N/A CAMION') + ' - ' + (carga.name if carga.name else 'Carga Sin Nombre' if carga else '')), lineas)
                            ws.write(fila, 2, prod.partner_seller_id.name, lineas)
                            if prod.currency_id_vendedor.name == 'UYU':
                                if recipt_number and recipt_number != 'No Pago':
                                    total_uyu += prod.seller_commission
                                ws.write(fila, 3, prod.seller_commission, title_number)
                                ws.write(fila, 4, '', title_number)
                            if prod.currency_id_vendedor.name == 'USD':
                                if recipt_number and recipt_number != 'No Pago':
                                    total_usd += prod.seller_commission
                                ws.write(fila, 3, '', title_number)
                                ws.write(fila, 4, prod.seller_commission, title_number)
                            ws.write(fila, 5, prod.currency_id_vendedor.name, lineas)
                            ws.write(fila, 6, MAP_REGIMEN[prod.regimen if prod.regimen else camion.regimen], lineas)
                            ws.write(fila, 7, prod.currency_id.name, lineas)
                            ws.write(fila, 8, prod.partner_invoice_id.name, lineas)
                            ws.write(fila, 9, prod.partner_invoice_id.name, lineas)
                            ws.write(fila, 10, 'Consolidado', lineas)
                            ws.write(fila, 11, 'Internacional', lineas)
                            if prod.currency_id.name == 'USD':
                                ws.write(fila, 12, prod.importe, title_number)
                                ws.write(fila, 13, '', title_number)
                            if prod.currency_id.name == 'UYU':
                                ws.write(fila, 12, '', title_number)
                                ws.write(fila, 13, prod.importe, title_number)

                            ws.write(fila, 14, self.return_invoice_number(producto_consol=prod), title_number)
                            ws.write(fila, 15, self.return_recepit_number(producto_consol=prod), title_number)

                            fila += 1
                        else:
                            continue

                    if not self.partner_seller_id:
                        ws.write(fila, 0, self.convertir_fecha(camion.start_datetime), lineas)
                        ws.write(fila, 1, camion.name if camion else 'N/A', lineas)
                        ws.write(fila, 2, prod.partner_seller_id.name, lineas)
                        if prod.currency_id_vendedor.name == 'UYU':
                            if recipt_number and recipt_number != 'No Pago':
                                total_uyu += prod.seller_commission
                            ws.write(fila, 3, prod.seller_commission, title_number)
                            ws.write(fila, 4, '', title_number)
                        if prod.currency_id_vendedor.name == 'USD':
                            if recipt_number and recipt_number != 'No Pago':
                                total_usd += prod.seller_commission
                            ws.write(fila, 3, '', title_number)
                            ws.write(fila, 4, prod.seller_commission, title_number)
                        ws.write(fila, 5, prod.currency_id_vendedor.name, lineas)
                        ws.write(fila, 6, prod.regimen, lineas)
                        ws.write(fila, 7, prod.currency_id.name, lineas)
                        ws.write(fila, 8, prod.partner_invoice_id.name, lineas)
                        ws.write(fila, 9, prod.partner_invoice_id.name, lineas)
                        ws.write(fila, 10, 'Consolidado', lineas)
                        ws.write(fila, 11, 'Internacional', lineas)
                        if prod.currency_id.name == 'USD':
                            ws.write(fila, 12, prod.importe, title_number)
                            ws.write(fila, 13, '', title_number)
                        if prod.currency_id.name == 'UYU':
                            ws.write(fila, 12, '', title_number)
                            ws.write(fila, 13, prod.importe, title_number)

                        ws.write(fila, 14, self.return_invoice_number(producto_consol=prod), title_number)
                        ws.write(fila, 15, self.return_recepit_number(producto_consol=prod), title_number)

                        fila += 1

        if productos_depo:
            for prod in prod_depo_obj.browse(productos_depo):
                recipt_number = self.return_recepit_number(productos_depo=prod)
                invoice_number = self.return_invoice_number(productos_depo=prod)
                if recipt_number == 'No Pago' and invoice_number not in ['Factura Borrador',
                                                                         'Carpeta No Facturada']:
                    lineas = lineas_no_pago
                    title_number = title_number_no_pago
                else:
                    if invoice_number in ['Factura Borrador', 'Carpeta No Facturada']:
                        lineas = lineas_borrador
                        title_number = title_number_borrador
                    else:
                        lineas = lineas_pago
                        title_number = title_number_pago
                ws.write(fila, 0, self.convertir_fecha(prod.start), lineas)
                ws.write(fila, 1, prod.deposito_srv_id.name, lineas)
                ws.write(fila, 2, prod.partner_seller_id.name, lineas)
                if prod.currency_id_vendedor.name == 'UYU':
                    if recipt_number and recipt_number != 'No Pago':
                        total_uyu += prod.seller_commission
                    ws.write(fila, 3, prod.seller_commission, title_number)
                    ws.write(fila, 4, '', title_number)
                if prod.currency_id_vendedor.name == 'USD':
                    if recipt_number and recipt_number != 'No Pago':
                        total_usd += prod.seller_commission
                    ws.write(fila, 3, '', title_number)
                    ws.write(fila, 4, prod.seller_commission, title_number)
                ws.write(fila, 5, prod.currency_id_vendedor.name, lineas)
                ws.write(fila, 6, 'Depo', lineas)
                ws.write(fila, 7, prod.currency_id.name, lineas)
                ws.write(fila, 8, prod.partner_invoice_id.name, lineas)
                ws.write(fila, 9, prod.partner_invoice_id.name, lineas)
                ws.write(fila, 10, 'Contenedor' if prod.deposito_srv_id.load_type == 'contenedor' else 'Carga Suelta',
                         lineas)
                ws.write(fila, 11, 'Nacional', lineas)
                if prod.currency_id.name == 'USD':
                    ws.write(fila, 12, prod.importe, title_number)
                    ws.write(fila, 13, '', title_number)
                if prod.currency_id.name == 'UYU':
                    ws.write(fila, 12, '', title_number)
                    ws.write(fila, 13, prod.importe, title_number)
                ws.write(fila, 14, invoice_number, title_number)
                ws.write(fila, 15, recipt_number, title_number)
                fila += 1

        ultima_fila = fila + 1
        ws.write_merge(ultima_fila, ultima_fila, 1, 2, "Total Pago:", total_number)
        ws.write(ultima_fila, 3, '$ ' + str(total_uyu), total_number)
        ws.write(ultima_fila, 4, 'USD ' + str(total_usd), total_number)

    @api.multi
    def informe_comision_cliente(self):
        # Creo el 'Libro' y su 'Pagina'
        wb = Workbook(encoding='utf-8')
        condiciones_busqueda = []
        start, stop = self.convert_date_to_datetime(self.start, self.stop)
        productos_ordenados_por_mes = self.get_productos_ordenados_por_mes(start, stop, self.partner_seller_id)
        carpetas_marfrig_ordenados_por_mes = self.get_productos_mafrig_ordenados_por_mes(start, stop, self.partner_seller_id)
        productos_consol_ordenados_por_mes = self.get_productos_consol_ordenados_por_mes(start, stop)
        productos_depo_ordenados_por_mes = self.get_productos_depo_ordenados_por_mes(start, stop, self.partner_seller_id)
        posicion = 0
        if not productos_ordenados_por_mes and not carpetas_marfrig_ordenados_por_mes and not productos_consol_ordenados_por_mes and not productos_depo_ordenados_por_mes:
            raise Warning('No se encontraron lineas')
        for productos in productos_ordenados_por_mes:
            if productos or carpetas_marfrig_ordenados_por_mes[posicion] or productos_consol_ordenados_por_mes[posicion] or productos_depo_ordenados_por_mes[posicion]:
                self.write_page_per_driver(wb=wb, productos=productos, posicion=posicion, carpetas_marfrig=carpetas_marfrig_ordenados_por_mes[posicion], productos_consol=productos_consol_ordenados_por_mes[posicion], productos_depo=productos_depo_ordenados_por_mes[posicion])
            posicion += 1

        fp = BytesIO()
        wb.save(fp)
        fp.seek(0)
        data = fp.read()
        fp.close()
        data_to_save = base64.encodebytes(data)
        file_name = 'Informe Comision Vendedores - %s.xls' % self.get_report_name(start=self.start, stop=self.stop, vendedor=self.partner_seller_id)
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
