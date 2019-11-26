# -*- coding: utf-8 -*-

from odoo import models, fields, api
import ipdb
from xlrd import open_workbook
import base64
import io
from io import BytesIO
from io import StringIO
import time
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning
from xlwt import *
class ImportEnhanced(models.Model):
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _name = 'import.enhanced'
    _description = 'Enhanced Data Importation'

    name = fields.Char()
    model_id = fields.Many2one(comodel_name='ir.model', string='Data Model')
    archive = fields.Binary(string="Archive", attachment=True)
    no_duplicates = fields.Boolean(string="Don't import if arleady exist" )

    # def create_products(self, sheet=None, field_names=None, model=None):



    @api.multi
    def upload_archive(self):
        product = 'Plantilla de producto'
        en_que_anda = 0
        ipdb.set_trace()
        for rec in self:
            with io.BytesIO(base64.b64decode(rec.archive)) as f:
                try:
                    book = open_workbook(file_contents=f.getvalue())
                except TypeError as e:
                    raise ValidationError(u'ERROR: {}'.format(e))
                sheet = book.sheets()[0]
                column_names = []
                wb = Workbook(encoding='utf-8')
                res_dict = {}
                start_time = time.time()
                contador = 0
                total_productos = sheet.nrows - 1
                entro = False
                entro2 = False
                product = self.env['product.template']
                bien = 0
                mal = 0
                lineas = easyxf('font: name Calibri; alignment: horizontal left')
                title = easyxf('font: name Calibri, bold True; alignment: horizontal left')
                fila = 0
                fila2 = 0
                # ipdb.set_trace()
                ws1 = wb.add_sheet('Ajustar cantidad real', cell_overwrite_ok=True)
                ws1.write(fila, 0, "sku", title)
                ws1.write(fila, 1, "cantidad", title)
                ajuste_obj = self.env['stock.inventory']
                # for row in range(50000):
                ipdb.set_trace()
                for row in range(sheet.nrows):
                    print(row)
                    # sku = sheet.cell_value(row, 0).replace('Total ', '')
                    sku = sheet.cell_value(row, 0)
                    if not sku:
                        continue
                    prod = product.search([('barcode', '=', sku)])
                    if prod:
                        en_que_anda = row
                        if str() in sheet.cell_value(row, 0):
                            # ipdb.set_trace()
                            # if prod.qty_available == sheet.cell_value(row, 2):
                            if prod.qty_available == sheet.cell_value(row, 1):
                                print('parece que esta todo bien')
                                bien += 1
                            # if prod.qty_available != sheet.cell_value(row, 2):
                            if prod.qty_available != sheet.cell_value(row, 1):
                                print('hay diferencia')
                                diferencia = sheet.cell_value(row, 1)
                                ajuste = prod.action_update_quantity_on_hand()
                                vals = ajuste['context']
                                location = False
                                ubicacion_basicos = 4148
                                ubicacion_nbasico = 4147
                                to_ceate = {
                                    'name': sku,
                                    'filter': 'product',
                                    'product_id': prod.product_variant_id.id,
                                    'location_id': ubicacion_nbasico,
                                }
                                ajuste_iniciado = ajuste_obj.create(to_ceate)
                                ajuste_iniciado.action_start()

                                if not ajuste_iniciado.line_ids:
                                    line_values = {
                                        'product_id': prod.product_variant_id.id,
                                        'product_uom_id': 1,
                                        'location_id': ubicacion_nbasico,
                                        'inventory_id': ajuste_iniciado.id,
                                    }
                                    data1 = {'line_ids': [(0, 0, line_values)]}
                                    ajuste_iniciado.write(data1)

                                ajuste_iniciado.line_ids.product_qty = diferencia
                                ajuste_iniciado.action_validate()



                                ws1.write(fila, 0, sku, lineas)
                                ws1.write(fila, 1, diferencia, lineas)
                                ws1.write(fila, 2, 'hay mas de un quant', lineas)



                print('se quedo en %s de %s' %(en_que_anda, row))
                print('hay %s bien y %s mal' % (bien, mal))
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

