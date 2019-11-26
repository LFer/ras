# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details

from odoo import api, fields, models
from datetime import datetime
from . import num2words
import ipdb

class ParticularReport(models.AbstractModel):
    _name = 'report.ras_trans_crt_report.report_crt_report'
    _description = 'CRT Report'

    def _get_date(self):
        return datetime.now().strftime("%d/%m/%Y")

    def recorre_lineas_factura_invoice_description(self, lineas):
        desc = ''
        if lineas:
            for l in lineas:
                if l.invoice_description:
                    if desc != '' and l.invoice_description != '':
                        desc += ', ' + l.invoice_description
                    else:
                        desc = l.invoice_description

        return desc

    def recorre_lineas_factura_invoice_list(self, lineas):
        desc = ''
        if lineas:
            for l in lineas:
                if l.invoice_list:
                    if desc != '' and l.invoice_list != '':
                        desc += ', ' + l.invoice_list
                    else:
                        desc = l.invoice_list

        return desc

    def recorre_lineas_factura_ncm(self, lineas):
        desc = ''
        if lineas:
            for l in lineas:
                if l.ncm:
                    if desc != '' and l.ncm != '':
                        desc += ', ' + l.ncm
                    else:
                        desc = l.ncm


        return desc

    def recorre_lineas_factura_market_value(self, lineas):
        desc = 0
        if lineas:
            for l in lineas:
                desc += l.market_value

        return desc


    def recorre_lineas_factura_package(self, lineas):
        desc = 0
        if lineas:
            for l in lineas:
                desc += l.package

        return desc

    def recorre_lineas_factura_raw_kg(self, lineas):
        desc = 0
        if lineas:
            for l in lineas:
                desc += l.raw_kg

        return round(desc, 2)

    def recorre_lineas_factura_volume(self, lineas):
        desc = 0
        if lineas:
            for l in lineas:
                desc += l.volume

        return round(desc, 2)

    @staticmethod
    def to_word(number, currency=None, decimals_separator_str=None, negative_str=None):
        return num2words.to_word( number, currency=currency, decimals_separator_str=decimals_separator_str, negative_str=negative_str)

    def recorre_lineas_factura_market_value_desc(self, lineas):
        desc = 0
        value_desc = ''
        if lineas:
            for l in lineas:
                desc += l.market_value
            if desc:
                value_desc = self.to_word(number=desc, currency=None, decimals_separator_str=None, negative_str=None )

        return value_desc

    def recorre_tipo_de_accion_carga(self, lineas):
        if lineas:
            for l in lineas:
                if l.action_type_id.name == 'Carga':
                    return l

    def recorre_tipo_de_accion_salida(self, lineas):
        if lineas:
            for l in lineas:
                if l.action_type_id.name == 'Salida':
                    return l

    def recorre_tipo_de_accion_frontera(self, lineas):
        if lineas:
            for l in lineas:
                if l.action_type_id.name == 'Frontera':
                    return l

    def recorre_tipo_de_accion_arribo_a_fiscal(self, lineas):
        if lineas:
            for l in lineas:
                if l.action_type_id.name == 'Arribo a fiscal':
                    return l

    def recorre_tipo_de_accion_liberacion_fiscal(self, lineas):
        if lineas:
            for l in lineas:
                if l.action_type_id.name == 'Liberación fiscal':
                    return l

    def recorre_tipo_de_accion_descarga(self, lineas):
        if lineas:
            for l in lineas:
                if l.action_type_id.name == 'Descarga':
                    return l

    def suma_tipo_de_accion_importe(self, lineas):
        desc = 0
        if lineas:
            for l in lineas:
                if l.action_type_id.name == 'Salida':
                    desc += l.importe
                if l.action_type_id.name == 'Frontera':
                    desc += l.importe
                if l.action_type_id.name == 'Descarga':
                    desc += l.importe

        return desc

    def generar_ruta(self, lineas):
        desc = ""
        if lineas:
            for l in lineas:
                if l.action_type_id.name == 'Salida':
                    if desc != "":
                        if l.origin_id.city_id:
                            desc = l.origin_id.city_id.name + desc;
                            desc += "-";
                        if l.frontera_nacional:
                            desc += l.frontera_nacional.name;
                    else:
                        if l.origin_id.city_id:
                            desc += l.origin_id.city_id.name;
                            desc += "-";
                        if l.frontera_nacional:
                            desc += l.frontera_nacional.name;
                if l.action_type_id.name == 'Descarga':
                    if l.frontera_internacional:
                        desc += "-";
                        desc += l.frontera_internacional.name;
                    if l.destiny_id.city_id:
                        desc += "-";
                        desc += l.destiny_id.city_id.name;
                        desc += "-";
                        desc += l.destiny_id.country_id.name;

        return desc

    def recorre_tipo_de_lineas(self, lineas):
        if lineas:
            for line in lineas:
                return line
        else:
            return " "


    @api.model
    def _get_report_values(self, docids, data=None):
        report = self.env['ir.actions.report']._get_report_from_name('ras_trans_crt_report.report_crt_report')

        values = {'doc_ids': docids,
                  'doc_model': report.model,
                  'docs': self.env[report.model].browse(docids),
                  'report_type': data.get('report_type') if data else '',
                  'date': self._get_date,
                  'recorre_lineas_factura_invoice_description': self.recorre_lineas_factura_invoice_description,
                  'recorre_lineas_factura_invoice_list': self.recorre_lineas_factura_invoice_list,
                  'recorre_lineas_factura_market_value': self.recorre_lineas_factura_market_value,
                  'recorre_lineas_factura_ncm': self.recorre_lineas_factura_ncm,
                  'recorre_lineas_factura_package': self.recorre_lineas_factura_package,
                  'recorre_lineas_factura_raw_kg': self.recorre_lineas_factura_raw_kg,
                  'recorre_lineas_factura_volume': self.recorre_lineas_factura_volume,
                  'recorre_lineas_factura_market_value_desc': self.recorre_lineas_factura_market_value_desc,
                  'recorre_tipo_de_accion_carga': self.recorre_tipo_de_accion_carga,
                  'recorre_tipo_de_accion_salida': self.recorre_tipo_de_accion_salida,
                  'recorre_tipo_de_accion_frontera': self.recorre_tipo_de_accion_frontera,
                  'recorre_tipo_de_accion_arribo_a_fiscal': self.recorre_tipo_de_accion_arribo_a_fiscal,
                  'recorre_tipo_de_accion_liberacion_fiscal': self.recorre_tipo_de_accion_liberacion_fiscal,
                  'recorre_tipo_de_accion_descarga': self.recorre_tipo_de_accion_descarga,
                  'suma_tipo_de_accion_importe': self.suma_tipo_de_accion_importe,
                  'generar_ruta': self.generar_ruta,
                  'recorre_tipo_de_lineas': self.recorre_tipo_de_lineas,
                  }

        return values
