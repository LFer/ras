# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import ipdb
import odoo.addons.decimal_precision as dp
from odoo import api, fields, models
_logger = logging.getLogger(__name__)
from . import num2words
import os
from odoo.modules.module import get_resource_path, get_module_path
#from openpyxl.cell import Cell
#from openpyxl import load_workbook
#from openpyxl.worksheet import Worksheet
#from openpyxl.drawing.image import Image
from io import BytesIO
import base64
#import openpyxl
#from openpyxl import Workbook
#from openpyxl.utils import coordinate_from_string

MAP_ANCHORS = {
    'M11': 'crt_number',     #CRT_Number
    # 'P32': 'field_12_2',    #Peso Neto
    # 'O32': 'field_12_1',    #Peso Neto Letra

}

class rt_service_carga(models.Model):
    _inherit = "rt.service.carga"
    _description = "Extension de carga para reporte MIC y CRT"

    market_origin = fields.Char(string='Origen de la mercadería')
    invoice_description = fields.Text(string='Descripción de Facturas')
    invoice_list = fields.Char(string='Listado de Facturas')
    ncm = fields.Char(string='NCM')
    remitente_id = fields.Many2one(comodel_name='asociados.carpeta', string='Remitente', domain="[('type', '=','remitente')]")
    partner_remitente_id = fields.Many2one(comodel_name='res.partner', string= 'Partner Remitente', domain=[('remittent', '=', True)])
    consigantario_id = fields.Many2one(comodel_name='asociados.carpeta', string='Consignatario', domain="[('type', '=','consignatario')]")
    partner_consigantario_id = fields.Many2one(comodel_name='res.partner', string= 'Partner Consignatario', domain=[('consignee', '=', True)])
    destinatario_id = fields.Many2one(comodel_name='asociados.carpeta', string='Destinatario', domain="[('type', '=','destino')]")
    partner_destinatario_id = fields.Many2one(comodel_name='res.partner', string='Partner Destinatario', domain=[('receiver', '=', True)])
    partner_notificar_id = fields.Many2one(comodel_name='res.partner', string='Partner Notificar a ', domain=[('notificar','=', True)])
    notificar_id = fields.Many2one(comodel_name='asociados.carpeta', string='Notificar a ',domain="[('type', '=','notificar')]")
    route = fields.Text(string='Rutas')
    country_id = fields.Many2one(comodel_name='res.country', string='País')
    crt_number = fields.Char(string='Numero CRT')
    mic_number = fields.Char(string='Numero MIC')
    kilaje_carga = fields.Float(string='Kilage de la Carga')
    volumen_est = fields.Char(string='Volumen Estimado')
    market_value = fields.Float(string='Valor de la Mercaderia')
    market_value_desc = fields.Text(string='Valor de la mercaderia en texto')
    market_value_currency_id = fields.Many2one(string='Moneda', comodel_name='res.currency')
    xls_file = fields.Binary(string='XLS File')
    xls_name = fields.Char(string='File Name', size=128)


    def clone_worksheet(self, workbook, ws, title=""):
        new_ws = Worksheet(parent=workbook, title=title)
        new_ws.row_dimensions = ws.row_dimensions #BoundDictionary("index", self._add_row)
        new_ws.column_dimensions = ws.column_dimensions
        new_ws.page_breaks = ws.page_breaks
        new_ws._charts = ws._charts
        new_ws._images = [] #ws._images it not good option because the images are repeated
        new_ws._rels = ws._rels
        new_ws._drawing = ws._drawing
        #new_ws._comment_count = ws._comment_count
        #new_ws._merged_cells = ws._merged_cells
        # new_ws.hyperlinks = ws.hyperlinks
        # new_ws._data_validations = ws._data_validations
        new_ws.sheet_state = ws.sheet_state
        new_ws.page_setup = ws.page_setup
        new_ws.print_options = ws.print_options
        new_ws.page_margins = ws.page_margins
        # new_ws.header_footer = ws.header_footer
        # new_ws.sheet_view = ws.sheet_view
        new_ws.sheet_view.tabSelected = None #If this line is removed then many sheet will be selected.
        new_ws.protection = ws.protection
        new_ws._current_row = ws._current_row
        # new_ws._auto_filter = ws._auto_filter
        # new_ws._freeze_panes = ws._freeze_panes
        new_ws.paper_size = ws.paper_size
        new_ws.formula_attributes = ws.formula_attributes
        new_ws.orientation = ws.orientation
        new_ws.conditional_formatting = ws.conditional_formatting
        new_ws.legacy_drawing = ws.legacy_drawing
        new_ws.sheet_properties = ws.sheet_properties
        new_ws._cells = {}
        for key, value in ws._cells.items():
            new_ws._cells[key] = Cell(new_ws, column=value.column, row=value.row, value=value.value, col_idx=value.col_idx, style_array=value._style)
        return new_ws

    @staticmethod
    def to_word(number, currency=None, decimals_separator_str=None, negative_str=None):
        return num2words.to_word( number, currency=currency, decimals_separator_str=decimals_separator_str, negative_str=negative_str)

    @api.onchange('market_value')
    def onchange_market_value(self):
        self.market_value_desc = False
        if self.market_value:
            self.market_value_desc = self.to_word(number=self.market_value, currency=None, decimals_separator_str=None, negative_str=None )

    def bind_data(self, ws, data_value, map_anchors={}, map_coord={}, context={}):
        if data_value and map_anchors:

            for key_map, value_map in map_anchors.items():
                #ws.cell(key_map)
                #M11

                #data_value[MAP_ANCHORS[key_map]]
                #self.fill_cell(data_value, ws.cell(key_map), value_map)
                cell = ws.cell(row=11, column=13)
                self.fill_cell(data_value, cell, value_map)


    def fill_cell(self, data_value, cell, value_map):
        """Override this function if you want add new cell value"""
        cell.value = data_value[value_map]
        return cell

    def add_image(self, ws, filepath, anchors=None, col=None, row=None, context={}):
        src_img = Image(filepath)
        if anchors:
            ws.add_image(src_img, anchors)
        elif row and col:
            cell = Cell(worksheet=ws, column=col, row=row)
            src_img.anchor(cell, anchortype=context.get('anchortype', "absolute"))
        return ws

    def fill_crt(self, data_value, ws):
        # #Image CRT Logo
        crt_img = os.path.join(get_module_path('servicio_base'),'img','crt_logo.png')
        self.add_image(ws, filepath=crt_img, anchors='B4')
        #Image RAS Logo
        ras_img = os.path.join(get_module_path('servicio_base'),'img','ras_logo.png')
        self.add_image(ws, filepath=ras_img, anchors='N13')
        #Image RAS Logo
        ras_img2 = os.path.join(get_module_path('servicio_base'),'img','ras_logo2.png')
        self.add_image(ws, filepath=ras_img2, anchors='F76')
        # #Bind Data
        # self.bind_data(ws, data_value, map_anchors=MAP_ANCHORS)
        for key, value in data_value.items():
            ws[key] = value

    def clean_data(self, items):
        for data in items:
            for crt,fields in data.items():
                #'O32': 'field_12_2', --> Peso Neto
                if data[crt]['field_12_2'] == 0:
                    data[crt]['field_12_1'] = ''
                    data[crt]['field_12_2'] = ''
                # #'O33': 'field_12_3', --> Peso Bruto
                # if data[crt]['field_12_4'] == 0:
                #     data[crt]['field_12_3'] = ''
                #     data[crt]['field_12_4'] = ''
                # #'O37': 'field_13_1', --> Volumen
                # if data[crt]['field_13_1'] == 0:
                #     data[crt]['field_13_1'] = ''
                #     data[crt]['field_13_2'] = ''
                # #'O42': 'field_14_1', --> Market Value
                # if data[crt]['field_14_1'] == 0:
                #     data[crt]['field_14_1'] = ''
        return items

    def _create_crt_data(self):
        # data_value = []
        data = {}


        #data = dict.fromkeys(MAP_ANCHORS.values(), '')
        data = dict.fromkeys(MAP_ANCHORS.keys(), '')
        for key in data.keys():
            #CRT NUMBER
            if key == 'M11':
                data[key] = self.crt_number

        #data[srv_prod.crt_number]['field_2_1'] = srv_prod.crt_number.upper() if srv_prod.crt_number else ''
        # data_value.append(data)
        #self.clean_data(items)

        return data

    @api.multi
    def create_crt_report(self):
        for row in self:
            if row.xls_file or row.xls_name:
                row.write({'xls_file': False, 'xls_name': False})
            filepath = os.path.join(get_module_path('servicio_base'), 'xlsx_tpl', 'CRT.xlsx')
            wb = load_workbook(filepath)
            if not wb._sheets:
                return
            count = 0
            #ws = self.clone_worksheet(wb, wb._sheets[0], title="CRT"+str(count))
            #source = wb.active
            #ws = wb.copy_worksheet(source)
            ws = self.clone_worksheet(wb, wb._sheets[0], title="CRT"+str(count))
            data_value = self._create_crt_data()
            self.fill_crt(data_value, ws)
            wb._sheets.append(ws)
            # Delete CRT template, first position
            #if len(wb._sheets) > 1:
            #wb.remove_sheet(wb._sheets[0])
            #wb.active = 0
            xls_io = BytesIO()
            wb.save(xls_io)
            row.write({'xls_file': base64.encodestring(xls_io.getvalue()), 'xls_name': 'CRT' + '.xlsx'})
            return True


    @api.multi
    def delete_crt_report(self):
        self.write({'xls_file': False, 'xls_name': False})
        return True
