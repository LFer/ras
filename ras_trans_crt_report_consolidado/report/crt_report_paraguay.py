# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details

from odoo import api, fields, models
from datetime import datetime
from . import num2words
import ipdb

class ParticularReport(models.AbstractModel):
    _name = 'report.ras_trans_crt_report_consolidado.paraguay'
    _description = 'CRT Report Paraguay'

    def obtener_ids(self, camion):
        lista_dev = []
        for carga in camion.cargas_ids:
            crt = ""
            l_identidad = []
            identidad = ""
            existe = False
            if carga.crt_number:
                crt = carga.crt_number
                identidad = carga.id
                if lista_dev:
                    for l in lista_dev:
                        if crt == l[0]:
                            existe = True
                            l[1].append(identidad)
                if not lista_dev or not existe:
                    l_identidad.append(identidad)
                    lista_dev.append((crt, l_identidad))

        return lista_dev

    def _get_date(self):
        return datetime.now().strftime("%d/%m/%Y")

    def recorre_lineas_factura_invoice_description(self, lineas):
        desc = ''
        if lineas:
            for l in lineas:
                if l.invoice_description:
                    if desc != '' and l.invoice_description != '':
                        desc += ', '
                    desc += l.invoice_description

        return desc

    def recorre_lineas_factura_invoice_list(self, cargas):
        desc = ''
        if cargas:
            for carga in cargas:
                if carga.factura_carga_ids:
                    for l in carga.factura_carga_ids:
                        if l.invoice_list:
                            if desc != '' and l.invoice_list != '':
                                desc += ' / '
                            desc += l.invoice_list

        return desc

    def recorre_lineas_factura_ncm(self, lineas):
        desc = ''
        if lineas:
            for l in lineas:
                if l.ncm:
                    if desc != '' and l.ncm != '':
                        desc += '; ' + l.ncm
                    desc += l.ncm

        return desc

    def recorre_lineas_factura_market_value(self, cargas):
        desc = 0
        if cargas:
            for carga in cargas:
                if carga.factura_carga_ids:
                    for l in carga.factura_carga_ids:
                        desc += l.market_value

        return desc

    def recorre_lineas_factura_market_origin(self, cargas):
        desc = ''
        origin_list = []
        if cargas:
            for carga in cargas:
                if carga.factura_carga_ids:
                    for l in carga.factura_carga_ids:
                        if l.market_origin:
                            existe = False
                            origin = l.market_origin
                            if origin_list:
                                for l_ori in origin_list:
                                    if origin == l_ori:
                                        existe = True
                            if not origin_list or not existe:
                                origin_list.append(origin)
                                if desc != '' and l.market_origin != '':
                                    desc += ' / '
                                desc += l.market_origin

        return desc

    def recorre_lineas_factura_package(self, lineas):
        desc = 0
        if lineas:
            for l in lineas:
                desc += l.package

        return desc

    def recorre_lineas_factura_raw_kg(self, cargas):
        desc = 0
        if cargas:
            for carga in cargas:
                if carga.packing_list_carga_ids:
                    for l in carga.packing_list_carga_ids:
                        desc += l.raw_kg

        return round(desc, 2)

    def recorre_lineas_factura_volume(self, cargas):
        desc = 0
        if cargas:
            for carga in cargas:
                if carga.packing_list_carga_ids:
                    for l in carga.packing_list_carga_ids:
                        desc += l.volume

        return round(desc, 2)

    @staticmethod
    def to_word(number, currency=None, decimals_separator_str=None, negative_str=None):
        return num2words.to_word( number, currency=currency, decimals_separator_str=decimals_separator_str, negative_str=negative_str)

    def recorre_lineas_factura_market_value_desc(self, cargas):
        desc = 0
        value_desc = ''
        if cargas:
            for carga in cargas:
                if carga.factura_carga_ids:
                    for l in carga.factura_carga_ids:
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

    def suma_tipo_de_accion_salida_importe(self, cargas):
        desc = 0
        if cargas:
            for carga in cargas:
                if carga.producto_servicio_carga_ids:
                    for l in carga.producto_servicio_carga_ids:
                        if l.action_type_id.name == 'Salida':
                            desc += l.importe

        return desc

    def suma_tipo_de_accion_frontera_importe(self, cargas):
        desc = 0
        if cargas:
            for carga in cargas:
                if carga.producto_servicio_carga_ids:
                    for l in carga.producto_servicio_carga_ids:
                        if l.action_type_id.name == 'Frontera':
                            desc += l.importe

        return desc

    def suma_tipo_de_accion_descarga_importe(self, cargas):
        desc = 0
        if cargas:
            for carga in cargas:
                if carga.producto_servicio_carga_ids:
                    for l in carga.producto_servicio_carga_ids:
                        if l.action_type_id.name == 'Descarga':
                            desc += l.importe

        return desc

    def suma_tipo_de_accion_importe(self, cargas):
        desc = 0
        if cargas:
            for carga in cargas:
                if carga.producto_servicio_carga_ids:
                    for l in carga.producto_servicio_carga_ids:
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
                        if l.frontera_nacional:
                            desc = "-" + desc;
                            desc = l.frontera_nacional.name + desc;
                        if l.origin_id.city_id:
                            desc = "-" + desc;
                            desc = l.origin_id.city_id.name + desc;
                    else:
                        if l.origin_id.city_id:
                            desc += l.origin_id.city_id.name;
                        if l.frontera_nacional:
                            desc += "-";
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

    def obtener_cargas(self, camion, ids):
        carga_obj = camion.env['carga.camion']
        carga_lista = []
        for carga in camion.cargas_ids:
            if carga.id in ids[1]:
                carga_lista.append(carga.id)
        carga_filtradas = carga_obj.browse(carga_lista)

        return carga_filtradas

    def obtener_primera_carga(self, cargas):
        if cargas:
            for carga in cargas:
                    return carga
        else:
            return " "

    def carga_total_bultos(self, cargas):
        desc = 0
        if cargas:
            for carga in cargas:
                for linea in carga.packing_list_carga_ids:
                    desc += linea.package

        return desc

    def bultos_totales(self, cargas):
        lista_dev = []
        res = ""
        if cargas:
            for carga in cargas:
                for linea in carga.packing_list_carga_ids:
                    existe = False
                    tipo_bulto = str(linea.load_presentation.tipo_bulto)
                    cantidad_bulto = linea.package
                    if lista_dev:
                        for li in lista_dev:
                            if tipo_bulto == li[0]:
                                existe = True
                                cantidad_actual = li[1]
                                cantidad_actual += cantidad_bulto
                                lista_dev.append((tipo_bulto, cantidad_actual))
                                lista_dev.remove(li)
                    if not lista_dev or not existe:
                        lista_dev.append((tipo_bulto, cantidad_bulto))

        for lista in lista_dev:
            if res != '':
                res += ' + '
            res += lista[0] + str(lista[1])

        return res

    def bultos_lineas(self, cargas):
        desc = ""
        res = ''
        lista_dev = []
        if cargas:
            for carga in cargas:
                total_bultos = self.recorre_lineas_factura_package(carga.packing_list_carga_ids)
                descripcion = self.recorre_lineas_factura_invoice_description(carga.factura_carga_ids)
                ncm = self.recorre_lineas_factura_ncm(carga.factura_carga_ids)
                lista_dev.append((total_bultos, descripcion, ncm))

        for lista in lista_dev:
            if res != '':
                res += ' / '
            res += str(lista[0]) + ' BULTOS CON ' + lista[1] + lista[2]

        return res

    def recorre_tipo_de_lineas(self, lineas):
        if lineas:
            for line in lineas:
                return line
        else:
            return " "


    @api.model
    def _get_report_values(self, docids, data=None):
        report = self.env['ir.actions.report']._get_report_from_name('ras_trans_crt_report_consolidado.paraguay')

        values = {'doc_ids': docids,
                  'doc_model': report.model,
                  'docs': self.env[report.model].browse(docids),
                  'report_type': data.get('report_type') if data else '',
                  'date': self._get_date,
                  'bultos_lineas': self.bultos_lineas,
                  'bultos_totales': self.bultos_totales,
                  'carga_total_bultos': self.carga_total_bultos,
                  'recorre_lineas_factura_invoice_description': self.recorre_lineas_factura_invoice_description,
                  'recorre_lineas_factura_invoice_list': self.recorre_lineas_factura_invoice_list,
                  'recorre_lineas_factura_market_value': self.recorre_lineas_factura_market_value,
                  'recorre_lineas_factura_market_origin': self.recorre_lineas_factura_market_origin,
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
                  'suma_tipo_de_accion_salida_importe': self.suma_tipo_de_accion_salida_importe,
                  'suma_tipo_de_accion_frontera_importe': self.suma_tipo_de_accion_frontera_importe,
                  'suma_tipo_de_accion_descarga_importe': self.suma_tipo_de_accion_descarga_importe,
                  'suma_tipo_de_accion_importe': self.suma_tipo_de_accion_importe,
                  'recorre_tipo_de_lineas': self.recorre_tipo_de_lineas,
                  'generar_ruta': self.generar_ruta,
                  'obtener_primera_carga': self.obtener_primera_carga,
                  'obtener_cargas': self.obtener_cargas,
                  'obtener_ids': self.obtener_ids,
                  }

        return values
