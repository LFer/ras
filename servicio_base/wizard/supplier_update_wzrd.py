# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
import ipdb
import functools
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning
class rt_supplier_update_wzd(models.TransientModel):
    _name = "rt.supplier.update"
    _description = "Make Supplier Invoice"

    def get_dua(self, line):
        dua = ''
        if line.rt_service_id.dua_type == 'cabezal':
            carpeta = line.rt_service_id
            dua = carpeta.dua_aduana + '-' if carpeta.dua_aduana else ''
            dua += carpeta.dua_anio + '-' if carpeta.dua_anio else ''
            dua += carpeta.dua_numero if carpeta.dua_numero else ''
        elif line.rt_service_id.dua_type == 'linea':
            carga = line.rt_service_product_id.rt_carga_id
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

    @api.multi
    def update_values(self):
        context = self._context.copy()
        _ids = context.get('active_ids', [])
        _all_products = self.env['rt.service.product.supplier'].browse(_ids)
        for line in _all_products:
            #Servicio Nacional / Internacional
            if line.rt_service_id:
                if not line.supplier_id:
                    line.supplier_id = line.rt_service_id.supplier_id.id

                if not line.currency_id:
                    line.currency_id = line.rt_service_id.currency_id.id

                if not line.amount:
                    line.amount = line.rt_service_product_id.valor_compra

                if not line.service_state:
                    line.service_state = line.rt_service_id.state

                if not line.service_date:
                    line.service_date = line.rt_service_product_id.start

                if not line.tack_id:
                    line.tack_id = line.rt_service_product_id.rt_carga_id.container_number

                if not line.dua:
                    line.dua = self.get_dua(line=line)

                if not line.mic:
                    line.mic = line.rt_service_product_id.rt_carga_id.mic_number

                if not line.crt:
                    line.crt = line.rt_service_product_id.rt_carga_id.crt_number

                if not line.origin_id:
                    line.origin_id = line.rt_service_product_id.origin_id.id

                if not line.destiny_id:
                    line.destiny_id = line.rt_service_product_id.destiny_id.id

                if not line.output_reference:
                    line.output_reference = line.rt_service_id.name

                if not line.partner_invoice_id:
                    line.partner_invoice_id = line.rt_service_id.partner_invoice_id.id

                print('listo')

            if line.rt_service_product_id:
                # if not line.rt_service_id:
                #     line.rt_service_id = line.rt_service_product_id.rt_service_id.id
                if not line.rt_service_id:
                    line.rt_service_id = line.rt_service_product_id.rt_carga_id.rt_service_id.id

                if not line.supplier_id:
                    line.supplier_id = line.rt_service_product_id.supplier_id.id

                if not line.currency_id:
                    line.currency_id = line.rt_service_product_id.currency_id.id

                if not line.amount:
                    line.amount = line.rt_service_product_id.valor_compra

                if not line.service_state:
                    line.service_state = line.rt_service_product_id.rt_service_id.state

                if not line.service_date:
                    line.service_date = line.rt_service_product_id.start

                if not line.tack_id:
                    line.tack_id = line.rt_service_product_id.rt_carga_id.container_number

                if not line.dua:
                    line.dua = self.get_dua(line=line)

                if not line.mic:
                    line.mic = line.rt_service_product_id.rt_carga_id.mic_number

                if not line.crt:
                    line.crt = line.rt_service_product_id.rt_carga_id.crt_number

                if not line.origin_id:
                    line.origin_id = line.rt_service_product_id.origin_id.id

                if not line.destiny_id:
                    line.destiny_id = line.rt_service_product_id.destiny_id.id

                if not line.output_reference:
                    line.output_reference = line.rt_service_product_id.rt_service_id.name

                if not line.partner_invoice_id:
                    line.partner_invoice_id = line.rt_service_product_id.partner_invoice_id.id

                print('listo')

            #Deposito
            if line.rt_deposito_product_id:
                if not line.service_state:
                    line.service_state = line.rt_deposito_product_id.state

                if not line.service_date:
                    line.service_date = line.rt_deposito_product_id.start

                if not line.deposito_id:
                    line.deposito_id = line.rt_deposito_product_id.deposito_srv_id.id

            if line.rt_consol_product_id:
                if not line.service_state:
                    line.service_state = line.rt_consol_product_id.state

                if not line.service_date:
                    line.service_date = line.rt_consol_product_id.rt_carga_id.camion_id.start_datetime if line.rt_consol_product_id.rt_carga_id.camion_id else line.rt_consol_product_id.camion_id.start_datetime

                if not line.consol_id:
                    line.consol_id = line.rt_consol_product_id.rt_carga_id.camion_id.id if line.rt_consol_product_id.rt_carga_id.camion_id else line.rt_consol_product_id.camion_id.id


    name = fields.Char()