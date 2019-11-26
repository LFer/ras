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

class SetupTools(models.Model):
    _name = 'setup.tools'
    _description = 'Modelo para poner botones y demas cosas para las ediccion masiva'

    name = fields.Char(string='Nombre')
    fecha = fields.Date(string='Fecha')
    state = fields.Selection([('draft', 'Borrador'), ('done', 'Hecho')], string='Estado', default='draft', track_visibility='onchange', copy=False)


    def write_page_per_products(self,work_book=None, productos=None):
        maximo_largo_contenido_por_columna = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        title = easyxf('font: name Calibri, bold True; alignment: horizontal left')
        title_number = easyxf('font: name Calibri, bold True; alignment: horizontal right', num_format_str='#,##0.00;-#,##0.00;')
        lineas = easyxf('font: name Calibri; alignment: horizontal left')
        fila = 0

        # ws = work_book.add_sheet(productos.name, cell_overwrite_ok=True)
        ws = work_book.add_sheet('Stock 12-11', cell_overwrite_ok=True)
        # ws.write(0, 0, self.env['res.company'].browse(1).name, title)
        # ws.write(0, 5, formatters.date_fmt(fields.Date.today().isoformat()), title)
        ws.write(fila, 0, "cod_articulo", title)
        # ws.write(fila, 1, "Store", title)
        ws.write(fila, 1, "cantidad", title)
        ultima_columna = 16
        fila += 1
        primer_fila = 0
        ultima_fila = 0
        primer_fila = fila + 1

        # for line in productos.move_ids_without_package:
        #     # ws.write(fila, 0, line.barcode, lineas)
        #     ws.write(fila, 0, line.product_id.barcode, lineas)
        #     ws.write(fila, 1, line.quantity_done, lineas)
        #     # ws.write(fila, 1, line.x_studio_store, lineas)
        #     fila += 1
        #     ultima_fila = fila
        for line in productos:
            if line.qty_available > 0:
                ws.write(fila, 0, line.barcode, lineas)
                ws.write(fila, 1, line.qty_available, lineas)
                fila += 1
                ultima_fila = fila
        column = 0
        for maximo in maximo_largo_contenido_por_columna:
            if maximo <= 3:
                maximo = 10
            ws.col(column).width = maximo * 290
            if column == 15:
                ws.col(column).width = 12 * 290
            column += 1
        return

    @api.multi
    def arma_excel(self):
        wb = Workbook(encoding='utf-8')
        produc_obj = self.env['product.template']
        store_1 = '8981'
        store_basicos = 'Basicos'
        productos = produc_obj.search([('barcode', '!=', False), ('x_studio_store', '!=', False)])
        productos_2 = produc_obj.search([('barcode', '!=', False), ('x_studio_store', '=', store_basicos)])
        self.write_page_per_products(work_book=wb, productos=productos)
        hacer = False
        if hacer:
            for prod in productos:
                if not prod.partner_owner_id:
                    prod.partner_owner_id = 951
        #
        # for prod2 in productos_2:
        #     if not prod2.partner_owner_id:
        #         prod2.partner_owner_id = 951
        # stock_picking = self.env['stock.picking'].search([('partner_id', '=', 951), ('state', '=', 'done'), ('picking_type_id', '=', 1)])
        # for pick in stock_picking:
        #     self.write_page_per_products(work_book=wb, productos=pick)
        fp = BytesIO()
        wb.save(fp)
        fp.seek(0)
        data = fp.read()
        fp.close()

        data_to_save = base64.encodebytes(data)
        file_name = 'Stock-Odds-12-11.xls'
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

    @api.multi
    def button_draft_done(self):
        contador = 0
        # facturas = self.env['account.invoice'].search([('type', 'in', ['out_invoice']), ('fe_Serie', '!=', False)])
        facturas = self.env['account.invoice'].search([('type', 'in', ['out_invoice'])])
        for inv in facturas:
            if not inv.fe_Serie and not inv.fe_DocNro:
                continue
            internal_number = inv.number
            number = ''
            if inv.fe_Serie and inv.fe_DocNro:
                number = str(inv.fe_Serie + '-' + str(inv.fe_DocNro))
            inv.internal_number = internal_number
            if inv.move_id:
                inv.move_id.name = number
            inv.move_name = number
            inv.reference = number
            contador += 1
            number = False
            internal_number = False
            print('listo %d ' % contador)
        return
        #Primero actualizo el estado de la carpeta
        carpetas = self.env['rt.service'].search([])
        for carpeta in carpetas:
            if carpeta.carga_ids:
                contador += 1
                carpeta.load_type = carpeta.carga_ids[0].load_type
                print('listo %d ' % contador)

        calendarios = self.env['servicio.calendario'].search([('operation_type', '=', 'national')])
        for cal in calendarios:
            contador += 1
            cal.load_type = cal.rt_service_id.load_type
            if cal.marfrig_id:
                cal.load_type = 'contenedor'
            print('listo %d ' % contador)

        marfrig = self.env['marfrig.service.base'].search([])
        for ma in marfrig:
            ma.load_type = 'contenedor'
            raise Warning("La linea no tiene impuesto asociado  %s" % (self.ref))

        return self.write({'state': 'done'})
