# -*- coding: utf-8 -*-
from odoo import models, fields, api
import ipdb
from ..library import formatters

class AttrObjectAccess(dict):
    def __init__(self, *args, **kwargs):
        super(AttrObjectAccess, self).__init__(*args, **kwargs)
        self.__dict__ = self

class invoice(models.Model):
    _inherit = 'account.invoice'
    #Campos para la impresión de factura
    print_output_reference = fields.Boolean('Referencia Carpeta', help="ID: referencia_de_salida")
    print_origin_destiny_grouped = fields.Boolean('Agrupar Origen y Destino', help="ID: origen_destino_agrup")
    print_cont_grouped = fields.Boolean('Agrupar por Carga', help="ID: cargas_agrup")
    print_product_grouped = fields.Boolean('Agrupar por Productos', help="ID: product_agrup")
    print_invoice_load = fields.Boolean('Referencia Carga', help="ID: referencia")
    print_invoice_product = fields.Boolean('Referencia Producto', help="ID: referencia")
    print_date_start = fields.Boolean('Travel Date', help="ID: fecha_viaje")
    print_ms_in_out = fields.Boolean('Nº MS', help="ID: ms_entrada and ms_salida")
    print_mic = fields.Boolean('Nº MIC', help="ID: mic")
    print_crt = fields.Boolean('Nº CRT', help="ID: crt")
    print_consignee = fields.Boolean('Consignatario', help="ID: consignatario")
    print_purchase_order = fields.Boolean('Orden de Compra', help="ID: purchase order")
    print_delivery_order = fields.Boolean('Delivery Order', help='ID: delivery_order')
    print_origin_destiny = fields.Boolean('Origen y Destino', help="ID: origen and destino")
    print_container_number = fields.Boolean('Nº de Contenedor', help="ID: numero_contenedor")
    print_container_size = fields.Boolean('Tamaño Contenedor', help="ID: tamano_contenedor")
    print_booking = fields.Boolean('Nº Booking', help="ID: booking")
    print_gex = fields.Boolean('Nº GEX', help="ID: gex")
    print_sender = fields.Boolean('Remito', help="ID: remito")
    print_dua = fields.Boolean('DUA', help="ID: dua")
    print_all_info = fields.Boolean('Imprimir 0')
    print_packages = fields.Boolean('Bultos', help="ID: bultos")
    print_kg = fields.Boolean('Kilogramos', help="ID: kg")
    print_volume = fields.Boolean('Volumen', help="ID: volumen")
    print_extra_info = fields.Boolean('Agregar Info', help="Others informations that the user need include in the invoice report.")
    show_extra_info = fields.Boolean('Preview', help="Preview Code")
    qweb_extra_info = fields.Html('Others Informations')
    doct_type = fields.Char(string='Tipo de documento', compute="get_doc_type")
    DgiParam = fields.Char(string=u'Resolución DGI')

    def format_fmt(self, amount):
        return formatters.currency_fmt(amount)

    @api.multi
    @api.depends('name')
    def get_doc_type(self):
        #vat type =
        #2: RUC ( Uruguay )
        #3: C.I. ( Uruguay )
        #4: Otros
        #5: Pasaporte (todos los países)
        #6: DNI (documento de identidad de Argentina, Brasil, Chile o Paraguay)
        #pdb.set_trace()
        for recs in self:
            if recs.partner_id:
                if recs.partner_id.vat:
                    recs.rut = recs.partner_id.vat[2:]
                #Notas de Credito
                if recs.type == 'out_refund':
                    if recs.partner_id.vat_type == '2' and recs.partner_id.country_id.code == 'UY':
                        recs.doct_type = 'Nota de Credito de e-Factura'
                    #Si es 4 es otros y el codigo de pais es diferente a UY es e-ticket
                    if recs.partner_id.vat_type == '4' and recs.partner_id.country_id.code != 'UY':
                        recs.doct_type = u'Nota de Credito de e-Ticket'
                #Facturas de Cliente
                if recs.type == 'out_invoice':
                    #Nos vamos a guiar por vat type y el codigo de pais
                    #Si es 2 es rut y codigo de pais UY es e-factura
                    if recs.partner_id.vat_type == '2' and recs.partner_id.country_id.code == 'UY':
                        recs.doct_type = 'e-Factura'
                    #Si es 4 es otros y el codigo de pais es diferente a UY es e-ticket
                    if recs.partner_id.vat_type != '2' and recs.partner_id.country_id.code != 'UY':
                        recs.doct_type = 'e-Ticket'

            if recs.is_debit_note:
                if recs.type == 'out_invoice' and recs.partner_id.vat != "":
                    recs.doct_type = "Nota de Debito de e-Factura"
                if recs.type == 'out_invoice' and recs.partner_id.vat == "":
                    recs.doct_type = "Nota de Debito de e-Ticket"

            sys_cfg = recs.env['ir.config_parameter']
            #Aprovecho para sacar del parametro de sistema el valor de la resolución DGI para cada cliente
            SysParam = self.env['ir.config_parameter']
            if SysParam.get_param('fe_resolucion_DGI'):
                self.DgiParam = SysParam.get_param('fe_resolucion_DGI')

            if recs.payment_term_id.name == 'Contado':
                recs.tipo_pago = 'Contado'
            else:
                recs.tipo_pago = 'Crédito'

    def calcular_medidas(self, lineas):
        carga_anterior = 0
        medidas = ''
        bultos = 0
        kg = 0
        volumen = 0
        for inv_line in lineas:
            if inv_line.rt_service_product_id:
                prod = inv_line.rt_service_product_id
                if prod.rt_carga_id:
                    carga = prod.rt_carga_id
                    if carga_anterior != carga.id:
                        if carga.package:
                            bultos += carga.package
                        if carga.raw_kg:
                            kg += carga.raw_kg
                        if carga.volume:
                            volumen += carga.volume
        if bultos:
            medidas = ' ' + str(bultos) + ' Bultos'
        if kg:
            medidas += ' ' + str(kg) + ' Kg'
        if volumen:
            medidas = ' ' + str(volumen) + ' Mt3'

        return medidas

    def esta_en_factura(self, producto, invoice_line_ids):
        for inv_line in invoice_line_ids:
            if producto.id == inv_line.rt_service_product_id.id:
                return True

        return False

    def tiene_producto_facturable(self, carga):
        prod_fact = False
        if carga:
            for prod in carga.producto_servicio_ids:
                if prod.is_invoiced:
                    prod_fact = True

        return prod_fact

    def return_details_producto(self, product):
        """
        Se Devuelve la Referencia del producto
        """
        details = ''
        ### CONSOLIDADO ###
        if product:
            if self.print_invoice_product and product.name:
                details = 'Referencia: ' + str(product.name)

        return details

    def return_origin_destiny(self):
        """
        Devuelve origen y destino
        :return:
        """
        origin_destiny = []
        ### CONSOLIDADOS ###
        if self.camion_id:
            con = self.camion_id
            if self.print_origin_destiny and con.aduana_origen_id and con.aduana_destino_id:
                origin_destiny.append('Origen: ' + str(con.aduana_origen_id.name))
                origin_destiny.append('Destino: ' + str(con.aduana_destino_id.name))

        return origin_destiny

    def get_information(self):
        information = []
        prod_name = ""
        price = 0
        data_carpeta = []
        carga_anterior = 0
        price_anterior = 0
        anterior_flete = False
        contador_fiscal_internos = 0
        contador_fiscal_externos = 0
        contador_lavados = 0
        precio_fiscal_interno = 0
        precio_fiscal_externo = 0
        precio_lavados = 0

        # CONSOLIDADOS
        if self.camion_id:
            # Datos Carpeta
            con = self.camion_id
            servicio_fletes = len(self.invoice_line_ids.filtered(lambda x: x.product_id.name == 'Flete'))
            if servicio_fletes > 1:
                tramo_adelantado = False
            else:
                tramo_adelantado = True
            if self.print_output_reference and con.name:
                data_carpeta.append('Referencia de Salida: ' + str(con.name))
            if self.print_mic and con.mic_number:
                data_carpeta.append('MIC: ' + str(con.mic_number))
            if self.print_date_start and con.start_datetime:
                data_carpeta.append('Fecha de Incio: ' + str(con.start_datetime))

            for inv_line in self.invoice_line_ids:
                data = []
                if inv_line.consolidado_service_product_id:
                    prod = inv_line.consolidado_service_product_id
                    if prod.rt_carga_id:
                        # Datos Carga
                        carga = prod.rt_carga_id
                        if carga_anterior != carga.id:
                            string = ''
                            if self.print_invoice_load and carga.name:
                                data.append('Referencia: ' + str(carga.name))
                            if self.print_crt:
                                    if carga.crt_number:
                                        data.append('CRT: ' + str(carga.crt_number))
                            if carga.load_type == 'contenedor':
                                if self.print_container_number and carga.container_number:
                                    data.append('Nº de Contenedor: ' + str(carga.container_number))
                                if self.print_container_size and carga.container_type:
                                    data.append('Tamaño de Contenedor: ' + str(carga.container_type.size))
                                if self.print_booking and carga.booking:
                                    data.append('Booking: ' + str(carga.booking))
                                if self.print_sender and carga.remito:
                                    data.append('Remito: ' + str(carga.remito))
                            if self.print_dua:
                                if carga.dua_aduana and carga.dua_anio and carga.dua_numero:
                                    string = 'DUA: ' + str(carga.dua_aduana) + '-' + str(carga.dua_anio) + '-' + str(
                                        carga.dua_numero)
                                elif con.dua_aduana and con.dua_anio and con.dua_numero:
                                    string = 'DUA: ' + str(con.dua_aduana) + '-' + str(con.dua_anio) + '-' + str(
                                        con.dua_numero)
                            if self.print_packages and carga.package:
                                string += '  ' + str(carga.package) + ' Bultos'
                            if self.print_kg and carga.raw_kg:
                                string += '  ' + str(carga.raw_kg) + ' Kg'
                            if self.print_volume and carga.volume:
                                string += '  ' + str(carga.volume) + ' Mt3'
                            if string:
                                data.append(string)
                            carga_anterior = carga.id
                    #Datos Producto
                    if prod.product_id.name != 'Flete':
                        if self.print_invoice_product and inv_line.name:
                            data.append('Referencia: ' + str(inv_line.name))
                            # prod_name = 'Referencia: ' + str(prod.name)
                        if prod.product_id:
                            prod_name = str(prod.product_id.name)
                        price = inv_line.price_subtotal
                    if prod.product_id.name == 'Flete':
                        if anterior_flete or tramo_adelantado:
                            anterior_flete = False
                            if self.print_invoice_product and inv_line.name:
                                data.append('Referencia: ' + str(inv_line.name))
                                # prod_name = 'Referencia: ' + str(prod.name)
                            if prod.product_id:
                                prod_name = str(prod.product_id.name)
                            price = inv_line.price_subtotal + price_anterior
                        else:
                            anterior_flete = True
                            price_anterior = inv_line.price_subtotal
                    if prod.product_id.name == 'Verificación':
                        data.append('Verificación aduanera en Midomux/Doraline')
                #Cargo la informacion
                if prod.product_id.name != 'Flete' or not anterior_flete:
                    information.append((data, prod_name, price))
                else:
                    information.append((data, "", ""))

        #MARFRIG
        if self.marfrig_operation_id:
            mar = self.marfrig_operation_id
            # Datos Carpeta/Carga
            origen = ''
            if mar.mrf_srv_ids:
                servicios_con_planta_facturable = mar.mrf_srv_ids.filtered(lambda x: set(x.planta_id.ids) and x.is_invoiced and x.product_id.name != 'Horas de Espera')
                servicio_fletes = len(servicios_con_planta_facturable)
                if servicio_fletes > 1:
                    for servi in self.service_marfrig_ids:
                        if servi.product_id.name == 'Flete':
                            origen = servi.destiny_id.name
                else:
                    for servi in self.service_marfrig_ids:
                        if servi.product_id.name == 'Flete' and servi.is_invoiced:
                            origen = servi.origin_id.name
            string = ''
            oridesti = ''
            if self.print_output_reference and mar.sale_number:
                data_carpeta.append('Venta: ' + str(mar.sale_number))
            if self.print_purchase_order and self.comment:
                string += ' O/C: ' + str(self.comment)
            if self.print_origin_destiny and origen:
                oridesti = 'Origen: ' + origen
            if self.print_origin_destiny and origen and mar.destiny_id:
                oridesti += '  -  '
            if self.print_origin_destiny and mar.destiny_id:
                oridesti += 'Destino: ' + str(mar.destiny_id.name)
            if oridesti:
                data_carpeta.append(oridesti)
            if self.print_container_size and mar.container_type:
                data_carpeta.append('Tamaño de Contenedor: ' + str(mar.container_type.size))
            if self.print_container_number and mar.container_number:
                data_carpeta.append('Nº de Contenedor: ' + str(mar.container_number))
            if self.print_booking and mar.booking:
                data_carpeta.append('Booking: ' + str(mar.booking))
            if self.print_sender and mar.remito:
                data_carpeta.append('Remito: ' + str(mar.remito))
            if self.print_dua and mar.dua_aduana and mar.dua_anio and mar.dua_numero:
                string = 'DUA: ' + str(mar.dua_aduana) + '-' + str(mar.dua_anio) + '-' + str(
                    mar.dua_numero)
            data_carpeta.append(string)
            ver = 'Verificación aduanera en Midomux/Doraline'
            for inv_line in self.invoice_line_ids:
                # Datos Producto
                prod_name = ""
                if inv_line.product_id.name == 'Flete':
                    prod_name = 'Flete de Exportacion'
                if inv_line.product_id.name == 'Horas de Espera' and inv_line.price_subtotal != 0:
                    prod_name = str(inv_line.product_id.name + ' - Estadia en plaza') + ' - ' + str(formatters.convert_decimal_to_sexadecimal(inv_line.quantity)) + ' hrs'
                if inv_line.product_id.name == 'Verificación':
                    prod_name = 'Verificación aduanera en Midomux/Doraline'
                if inv_line.product_id.name != 'Flete' and inv_line.product_id.name != 'Horas de Espera' and prod_name != ver:
                        prod_name = str(inv_line.product_id.name)
                price = inv_line.price_subtotal

                # Cargo la informacion
                information.append((0, prod_name, price))

        #Servicio Nacional/Interancional
        if self.rt_service_id:
            # Datos Carpeta
            srv = self.rt_service_id
            if self.print_output_reference and srv.reference:
                data_carpeta.append('Referencia de Salida: ' + str(srv.reference))
            for inv_line in self.invoice_line_ids:
                data = []
                if inv_line.rt_service_product_id:
                    prod = inv_line.rt_service_product_id
                    if prod.rt_carga_id:
                        # Datos Carga
                        carga = prod.rt_carga_id
                        if carga_anterior != carga.id:
                            string = ''
                            oridesti = ''
                            contenedor = ''
                            if self.print_invoice_load and carga.name:
                                data.append('Referencia: ' + str(carga.name))
                            if self.print_date_start and prod.start:
                                data.append('Fecha Viaje: ' + prod.start.strftime("%d-%m-%Y"))
                            if self.print_origin_destiny and carga.origin_id.name:
                                oridesti += 'Origen: ' + str(carga.origin_id.name)
                            if self.print_origin_destiny and carga.origin_id.name and carga.destiny_id.name:
                                oridesti += ' - '
                            if self.print_origin_destiny and carga.destiny_id.name:
                                oridesti += 'Destino: ' + str(carga.destiny_id.name)
                            if oridesti:
                                data.append(oridesti)
                            if self.print_crt and carga.crt_number:
                                data.append('CRT: ' + str(carga.crt_number))
                            if self.print_mic and carga.mic_number:
                                data.append('MIC: ' + str(carga.mic_number))
                            if carga.load_type == 'contenedor':
                                if self.print_container_number and carga.container_number:
                                    contenedor += 'Nº de Contenedor: ' + str(carga.container_number)
                                if self.print_container_number and carga.container_number and carga.container_type:
                                    contenedor += '   '
                                if self.print_container_size and carga.container_type:
                                    contenedor += 'Tamaño de Contenedor: ' + str(carga.container_type.size)
                                if contenedor:
                                    data.append(contenedor)
                            if self.print_purchase_order and carga.purchase_order:
                                string += ' O/C: ' + str(carga.purchase_order)
                            if self.print_delivery_order and carga.delivery_order:
                                string += ' Delivery Order: ' + str(carga.delivery_order)
                            if self.print_booking and carga.booking:
                                string += ' Booking: ' + str(carga.booking)
                            if self.print_sender and prod.remito:
                                string += ' Remito: ' + str(prod.remito)
                            if self.print_ms_in_out and srv.mensaje_simplificado:
                                string += ' M/S: ' + str(srv.mensaje_simplificado)
                            if self.print_dua:
                                if srv.dua_type == 'linea':
                                    if not carga.multiple_dua:
                                        if carga.dua_aduana and carga.dua_anio and carga.dua_numero:
                                            string += ' DUA: ' + str(carga.dua_aduana) + '-' + str(
                                                carga.dua_anio) + '-' + str(carga.dua_numero)
                                    if carga.multiple_dua:
                                        dua = ''
                                        for duas in carga.duas_ids:
                                            if dua:
                                                dua += ' / '
                                                dua += str(duas.dua_aduana) + '-' + str(duas.dua_anio) + '-' + str(
                                                    duas.dua_numero)
                                            else:
                                                dua += str(duas.dua_aduana) + '-' + str(duas.dua_anio) + '-' + str(
                                                    duas.dua_numero)
                                        string += ' DUA: ' + dua
                                    if self.print_gex and carga.gex_number:
                                        string += ' GEX: ' + str(carga.gex_number)
                                if srv.dua_type == 'cabezal':
                                    if srv.dua_aduana and srv.dua_anio and srv.dua_numero:
                                        string += ' DUA: ' + str(srv.dua_aduana) + '-' + str(
                                            srv.dua_anio) + '-' + str(srv.dua_numero)
                                    if self.print_gex and srv.gex_number:
                                        string += ' GEX: ' + str(srv.gex_number)
                            if self.print_packages and carga.package:
                                string += '  ' + str(carga.package) + ' Bultos'
                            if self.print_kg and carga.raw_kg:
                                string += '  ' + str(carga.raw_kg) + ' Kg'
                            if self.print_volume and carga.volume:
                                string += '  ' + str(carga.volume) + ' Mt3'
                            if string:
                                data.append(string)
                            carga_anterior = carga.id
                    # Datos Producto
                    if srv.regimen == 'interno_fiscal_nat' and (prod.product_id.name == 'Fiscal Interno' or prod.product_id.name == 'Fiscal Externo' or prod.product_id.name == 'Lavado'):
                        if prod.product_id.name == 'Fiscal Interno':
                            contador_fiscal_internos += 1
                            precio_fiscal_interno += inv_line.price_subtotal
                            price = 0
                            string_fiscal_interno = 'Referencia Movimientos Fiscales Internos  ' + str(contador_fiscal_internos)
                        if prod.product_id.name == 'Fiscal Externo':
                            contador_fiscal_externos += 1
                            precio_fiscal_externo += inv_line.price_subtotal
                            price = 0
                            string_fiscal_externo = 'Referencia Movimientos Fiscales Externos  ' + str(contador_fiscal_externos)
                        if prod.product_id.name == 'Lavado':
                            contador_lavados += 1
                            precio_lavados += inv_line.price_subtotal
                            price = 0
                            string_lavado = 'Referencia Lavado de Contenedor  ' + str(contador_lavados)
                    else:
                        if prod.product_id.name != 'Flete':
                            if self.print_invoice_product and inv_line.name:
                                # prod_name = 'Referencia: ' + str(prod.name)
                                prod_name = 'Referencia: ' + str(inv_line.name)
                            else:
                                if prod.product_id:
                                    prod_name = str(prod.product_id.name)
                                if prod.product_id.name == 'Verificación':
                                    prod_name = 'Verificación aduanera en Midomux/Doraline'
                        if prod.product_id.name == 'Flete':
                            if self.print_invoice_product and prod.name:
                                prod_name = 'Referencia: ' + str(prod.name)
                            else:
                                if prod.operation_type == 'national':
                                    if prod.regimen == 'transit_nat':
                                        prod_name = str(prod.product_id.name) + ' de Transito'
                                    if prod.regimen == 'impo_nat':
                                        prod_name = str(prod.product_id.name) + ' de Importación'
                                    if prod.regimen == 'expo_nat':
                                        prod_name = str(prod.product_id.name) + ' de Exportación'
                                    if prod.regimen == 'interno_plaza_nat':
                                        prod_name = str(prod.product_id.name) + ' interno plaza'
                                    if prod.regimen == 'interno_fiscal_nat':
                                        prod_name = str(prod.product_id.name) + ' interno fiscal'
                                else:
                                    if inv_line.price_subtotal != 0:
                                        prod_name = str(prod.product_id.name)
                                    else:
                                        prod_name = ''

                        price = inv_line.price_subtotal

                if inv_line.rt_service_product_ids:
                    for prod in inv_line.rt_service_product_ids:
                        if prod.rt_carga_id:
                            # Datos Carga
                            carga = prod.rt_carga_id
                            if carga_anterior != carga.id:
                                string = ''
                                oridesti = ''
                                contenedor = ''
                                if self.print_invoice_load and carga.name:
                                    data.append('Referencia: ' + str(carga.name))
                                if self.print_date_start and prod.start:
                                    data.append('Fecha Viaje: ' + prod.start.strftime("%d-%m-%Y"))
                                if self.print_origin_destiny and carga.origin_id.name:
                                    oridesti += 'Origen: ' + str(carga.origin_id.name)
                                if self.print_origin_destiny and carga.origin_id.name and carga.destiny_id.name:
                                    oridesti += ' - '
                                if self.print_origin_destiny and carga.destiny_id.name:
                                    oridesti += 'Destino: ' + str(carga.destiny_id.name)
                                if oridesti:
                                    data.append(oridesti)
                                if self.print_crt and carga.crt_number:
                                    data.append('CRT: ' + str(carga.crt_number))
                                if self.print_mic and carga.mic_number:
                                    data.append('MIC: ' + str(carga.mic_number))
                                if carga.load_type == 'contenedor':
                                    if self.print_container_number and carga.container_number:
                                        contenedor += 'Nº de Contenedor: ' + str(carga.container_number)
                                    if self.print_container_number and carga.container_number and carga.container_type:
                                        contenedor += '   '
                                    if self.print_container_size and carga.container_type:
                                        contenedor += 'Tamaño de Contenedor: ' + str(carga.container_type.size)
                                    if contenedor:
                                        data.append(contenedor)
                                if self.print_purchase_order and carga.purchase_order:
                                    string += ' O/C: ' + str(carga.purchase_order)
                                if self.print_delivery_order and carga.delivery_order:
                                    string += ' Delivery Order: ' + str(carga.delivery_order)
                                if self.print_booking and carga.booking:
                                    string += ' Booking: ' + str(carga.booking)
                                if self.print_sender and prod.remito:
                                    string += ' Remito: ' + str(prod.remito)
                                if self.print_ms_in_out and srv.mensaje_simplificado:
                                    string += ' M/S: ' + str(srv.mensaje_simplificado)
                                if self.print_dua:
                                    if srv.dua_type == 'linea':
                                        if not carga.multiple_dua:
                                            if carga.dua_aduana and carga.dua_anio and carga.dua_numero:
                                                string += ' DUA: ' + str(carga.dua_aduana) + '-' + str(
                                                    carga.dua_anio) + '-' + str(carga.dua_numero)
                                        if carga.multiple_dua:
                                            dua = ''
                                            for duas in carga.duas_ids:
                                                if dua:
                                                    dua += ' / '
                                                    dua += str(duas.dua_aduana) + '-' + str(duas.dua_anio) + '-' + str(
                                                        duas.dua_numero)
                                                else:
                                                    dua += str(duas.dua_aduana) + '-' + str(duas.dua_anio) + '-' + str(
                                                        duas.dua_numero)
                                            string += ' DUA: ' + dua
                                        if self.print_gex and carga.gex_number:
                                            string += ' GEX: ' + str(carga.gex_number)
                                    if srv.dua_type == 'cabezal':
                                        if srv.dua_aduana and srv.dua_anio and srv.dua_numero:
                                            string += ' DUA: ' + str(srv.dua_aduana) + '-' + str(
                                                srv.dua_anio) + '-' + str(srv.dua_numero)
                                        if self.print_gex and srv.gex_number:
                                            string += ' GEX: ' + str(srv.gex_number)
                                if self.print_packages and carga.package:
                                    string += '  ' + str(carga.package) + ' Bultos'
                                if self.print_kg and carga.raw_kg:
                                    string += '  ' + str(carga.raw_kg) + ' Kg'
                                if self.print_volume and carga.volume:
                                    string += '  ' + str(carga.volume) + ' Mt3'
                                if string:
                                    data.append(string)
                                carga_anterior = carga.id
                        # Datos Producto
                        if srv.regimen == 'interno_fiscal_nat' and (prod.product_id.name == 'Fiscal Interno' or prod.product_id.name == 'Fiscal Externo' or prod.product_id.name == 'Lavado'):
                            if prod.product_id.name == 'Fiscal Interno':
                                contador_fiscal_internos += 1
                                precio_fiscal_interno += inv_line.price_subtotal
                                price = 0
                                string_fiscal_interno = 'Referencia Movimientos Fiscales Internos  ' + str(contador_fiscal_internos)
                            if prod.product_id.name == 'Fiscal Externo':
                                contador_fiscal_externos += 1
                                precio_fiscal_externo += inv_line.price_subtotal
                                price = 0
                                string_fiscal_externo = 'Referencia Movimientos Fiscales Externos  ' + str(contador_fiscal_externos)
                            if prod.product_id.name == 'Lavado':
                                contador_lavados += 1
                                precio_lavados += inv_line.price_subtotal
                                price = 0
                                string_lavado = 'Referencia Lavado de Contenedor  ' + str(contador_lavados)
                        else:
                            if prod.product_id.name != 'Flete':
                                if self.print_invoice_product and inv_line.name:
                                    # prod_name = 'Referencia: ' + str(prod.name)
                                    prod_name = 'Referencia: ' + str(inv_line.name)
                                    if prod.product_id.name == 'Verificación':
                                        prod_name = 'Verificación aduanera en Midomux/Doraline'
                                else:
                                    if prod.product_id:
                                        prod_name = str(prod.product_id.name)
                            if prod.product_id.name == 'Flete':
                                if self.print_invoice_product and prod.name:
                                    prod_name = 'Referencia: ' + str(prod.name)
                                else:
                                    if prod.operation_type == 'national':
                                        if prod.regimen == 'transit_nat':
                                            prod_name = str(prod.product_id.name) + ' de Transito'
                                        if prod.regimen == 'impo_nat':
                                            prod_name = str(prod.product_id.name) + ' de Importación'
                                        if prod.regimen == 'expo_nat':
                                            prod_name = str(prod.product_id.name) + ' de Exportación'
                                        if prod.regimen == 'interno_plaza_nat':
                                            prod_name = str(prod.product_id.name) + ' interno plaza'
                                        if prod.regimen == 'interno_fiscal_nat':
                                            prod_name = str(prod.product_id.name) + ' interno fiscal'
                                    else:
                                        if inv_line.price_subtotal != 0:
                                            prod_name = str(prod.product_id.name)
                                        else:
                                            prod_name = ''

                            price = inv_line.price_subtotal
                # Cargo la informacion
                information.append((data, prod_name, price))
            if contador_fiscal_internos != 0:
                information.append(("", string_fiscal_interno, ""))
                information.append(("", "Movimientos Interno", precio_fiscal_interno))
            if contador_fiscal_externos != 0:
                information.append(("", string_fiscal_externo, ""))
                information.append(("", "Movimientos Externo", precio_fiscal_externo))
            if contador_lavados != 0:
                information.append(("", string_lavado, ""))
                information.append(("", "Movimientos Externo", precio_lavados))

        if self.deposito_operation_id:
            depo = self.deposito_operation_id
            if self.print_output_reference and depo.referencia:
                data_carpeta.append('Referencia de Salida: ' + str(depo.referencia))
            for inv_line in self.invoice_line_ids:
                data = []
                string = ''
                if inv_line.product_deposito_srv_id:
                    inv_producto = inv_line.product_deposito_srv_id
                    if self.print_date_start and inv_producto.start:
                        string += 'Fecha: ' + str(inv_producto.start.strftime("%d-%m-%Y"))
                    if self.print_origin_destiny:
                        if inv_producto.origin_id:
                            string += ' Origen: ' + str(inv_producto.origin_id.name)
                        if inv_producto.origin_id and inv_producto.destiny_id:
                            string += ' - '
                        if inv_producto.destiny_id:
                            string += ' Destino: ' + str(inv_producto.destiny_id.name)
                data.append(string)
                if inv_line.product_id.name == 'Flete':
                    producto = 'Referencia: ' + str(inv_line.product_id.name)

                if inv_line.product_id.name == 'Verificación':
                    producto = 'Verificación aduanera en Midomux/Doraline'
                else:
                    producto = 'Referencia: ' + str(inv_line.name)
                price = inv_line.price_subtotal
                information.append((data, producto, price))

        elif not self.camion_id and not self.marfrig_operation_id and not self.rt_service_id and not self.deposito_operation_id:
            for inv_line in self.invoice_line_ids:
                data = ''
                if inv_line.product_id.name == 'Flete':
                    producto = 'Referencia: ' + str(inv_line.product_id.name)
                if inv_line.product_id.name == 'Verificación':
                    producto = 'Verificación aduanera en Midomux/Doraline'
                else:
                    if self.print_invoice_product and inv_line.name:
                        producto = str(inv_line.name)
                    else:
                        producto = str(inv_line.product_id.name)
                price = inv_line.price_subtotal
                information.append((data, producto, price))


        return data_carpeta, information

    def group_origin_destiny(self):
        srv = self.rt_service_id
        lista_dev = []
        list_producto = []
        for carga in srv.carga_ids:
            datos = []
            orig = ""
            dest = ""
            string = ""
            contenedor = ""
            data_carga = []
            price = 0
            existe = False
            existe_prod = False
            # Origen y Destino
            if not dest:
                if carga.destiny_id:
                    dest = carga.destiny_id.name
            _key = ""
            if dest:
                _key = "Dest. " + str(dest.upper())
            if not _key:
                _key = "Dest. Desconocido"
            # Datos
            if carga.load_type == 'contenedor':
                if self.print_container_number and carga.container_number:
                    contenedor += 'Nº de Contenedor: ' + str(carga.container_number)
                if self.print_container_number and carga.container_number and carga.container_type:
                    contenedor += '  '
                if self.print_container_size and carga.container_type:
                    contenedor += 'Tamaño de Contenedor:' + str(carga.container_type.size)
                if contenedor:
                    data_carga.append(contenedor)
            if self.print_purchase_order and carga.purchase_order:
                string += 'O/C: ' + str(carga.purchase_order)
            if self.print_gex:
                if carga.gex_number:
                    string += ' GEX: ' + str(carga.gex_number)
                else:
                    if srv.gex_number:
                        string += ' GEX: ' + str(srv.gex_number)
            if self.print_dua:
                if carga.dua_aduana and carga.dua_anio and carga.dua_numero:
                    string += ' DUA: ' + str(carga.dua_aduana) + '-' + str(carga.dua_anio) + '-' + str(
                        carga.dua_numero)
                else:
                    if srv.dua_aduana and srv.dua_anio and srv.dua_numero:
                        string += ' DUA: ' + str(srv.dua_aduana) + '-' + str(srv.dua_anio) + '-' + str(
                            srv.dua_numero)
            if self.print_packages and carga.package:
                string += ' ' + str(carga.package) + ' Bultos'
            if self.print_kg and carga.raw_kg:
                string += ' ' + str(carga.raw_kg) + ' Kg'
            if self.print_volume and carga.volume:
                string += ' ' + str(carga.volume) + ' Mt3'
            if string:
                data_carga.append(string)
            if self.print_product_grouped:
                for prod in carga.producto_servicio_ids:
                    if self.esta_en_factura(prod, self.invoice_line_ids):
                        existe_prod = False
                        if prod.product_id.name == 'Flete':
                            if prod.operation_type == 'national':
                                if prod.regimen == 'transit_nat':
                                    producto = str(prod.product_id.name) + ' de Transito'
                                if prod.regimen == 'impo_nat':
                                    producto = str(prod.product_id.name) + ' de Importación'
                                if prod.regimen == 'expo_nat':
                                    producto = str(prod.product_id.name) + ' de Exportación'
                                if prod.regimen == 'interno_plaza_nat':
                                    producto = str(prod.product_id.name) + ' interno plaza'
                                if prod.regimen == 'interno_fiscal_nat':
                                    producto = str(prod.product_id.name) + ' interno fiscal'
                        else:
                            producto = prod.product_id.name
                        price = prod.importe
                        if list_producto:
                            for l in list_producto:
                                if producto == l[0]:
                                    existe_prod = True
                                    l[1] += price
                        if not list_producto or not existe_prod:
                            list_producto.append([producto, price])
                if lista_dev:
                    for l in lista_dev:
                        if _key == l[0]:
                            existe = True
                            l[1].append((data_carga, 0))
                if not lista_dev or not existe:
                    datos.append((data_carga, 0))
                    lista_dev.append((_key, datos))
            else:
                for producto in carga.producto_servicio_ids:
                    if self.esta_en_factura(producto, self.invoice_line_ids):
                        price += producto.importe
                if lista_dev:
                    for l in lista_dev:
                        if _key == l[0]:
                            existe = True
                            l[1].append((data_carga, price))
                if not lista_dev or not existe:
                    datos.append((data_carga, price))
                    lista_dev.append((_key, datos))

        if self.print_product_grouped:
            return lista_dev, list_producto
        else:
            return lista_dev

    def group_product(self):
        data_carpeta = ''
        data_carga = []
        carga_anterior = 0
        bultos = 0
        list_producto = []

        if self.rt_service_id:
            srv = self.rt_service_id
            if self.print_output_reference and srv.reference:
                data_carpeta = 'Referencia de Salida: ' + str(srv.reference) + ' '
            if srv.dua_type == 'cabezal':
                if self.print_dua and srv.dua_aduana and srv.dua_anio and srv.dua_numero:
                    data_carpeta += 'DUA: ' + str(srv.dua_aduana) + '-' + str(
                        srv.dua_anio) + '-' + str(srv.dua_numero)
                if self.print_gex and srv.gex_number:
                    data_carpeta += ' GEX: ' + str(srv.gex_number)
                medidas = self.calcular_medidas(self.invoice_line_ids)
                data_carpeta += medidas
            for inv_line in self.invoice_line_ids:
                existe = False
                if inv_line.rt_service_product_id:
                    prod = inv_line.rt_service_product_id
                    if prod.rt_carga_id:
                        # Datos Carga
                        carga = prod.rt_carga_id
                        if carga_anterior != carga.id:
                            string = ''
                            if self.print_invoice_load and carga.name:
                                string += 'Referencia: ' + str(carga.name)
                            if carga.load_type == 'contenedor':
                                if self.print_container_number and carga.container_number:
                                    string += ' Nº Cont: ' + str(carga.container_number)
                                if self.print_container_number and carga.container_number and carga.container_type:
                                    string += '   '
                                if self.print_container_size and carga.container_type:
                                    string += 'Tamaño Cont: ' + str(carga.container_type.size)
                            if self.print_purchase_order and carga.purchase_order:
                                string += ' O/C: ' + str(carga.purchase_order)
                            if self.print_sender and prod.remito:
                                string += ' Remito: ' + str(prod.remito)
                            if self.print_ms_in_out and srv.mensaje_simplificado:
                                string += ' M/S: ' + str(srv.mensaje_simplificado)
                            if self.print_booking and carga.booking:
                                string += ' Booking: ' + str(carga.booking)
                            if srv.dua_type == 'linea':
                                if self.print_dua:
                                    if not carga.multiple_dua:
                                        if carga.dua_aduana and carga.dua_anio and carga.dua_numero:
                                            string += ' DUA: ' + str(carga.dua_aduana) + '-' + str(
                                                carga.dua_anio) + '-' + str(carga.dua_numero)
                                    if carga.multiple_dua:
                                        dua = ''
                                        for duas in carga.duas_ids:
                                            if dua:
                                                dua += ' / '
                                                dua += str(duas.dua_aduana) + '-' + str(duas.dua_anio) + '-' + str(
                                                    duas.dua_numero)
                                            else:
                                                dua += str(duas.dua_aduana) + '-' + str(duas.dua_anio) + '-' + str(
                                                    duas.dua_numero)
                                        string += ' DUA: ' + dua
                                if self.print_gex and carga.gex_number:
                                    string += ' GEX: ' + str(carga.gex_number)
                                if self.print_packages and carga.package:
                                    string += '  ' + str(carga.package) + ' Bultos'
                                if self.print_kg and carga.raw_kg:
                                    string += '  ' + str(carga.raw_kg) + ' Kg'
                                if self.print_volume and carga.volume:
                                    string += '  ' + str(carga.volume) + ' Mt3'
                            if self.print_origin_destiny and carga.origin_id.name:
                                string += ' Origen: ' + str(carga.origin_id.name)
                            if self.print_origin_destiny and carga.origin_id.name and carga.destiny_id.name:
                                string += ' - '
                            if self.print_origin_destiny and carga.destiny_id.name:
                                string += 'Destino: ' + str(carga.destiny_id.name)
                            if string:
                                data_carga.append(string)
                            carga_anterior = carga.id
                    if prod.product_id.name == 'Flete':
                        if prod.operation_type == 'national':
                            if prod.regimen == 'transit_nat':
                                producto = str(prod.product_id.name) + ' de Transito'
                            if prod.regimen == 'impo_nat':
                                producto = str(prod.product_id.name) + ' de Importación'
                            if prod.regimen == 'expo_nat':
                                producto = str(prod.product_id.name) + ' de Exportación'
                            if prod.regimen == 'interno_plaza_nat':
                                producto = str(prod.product_id.name) + ' interno plaza'
                            if prod.regimen == 'interno_fiscal_nat':
                                producto = str(prod.product_id.name) + ' interno fiscal'
                    else:
                        producto = prod.product_id.name
                    price = inv_line.price_subtotal
                    if list_producto:
                        for l in list_producto:
                            if producto == l[0]:
                                existe = True
                                l[1] += price
                    if not list_producto or not existe:
                        list_producto.append([producto, price])
        if self.camion_id:
            # Datos Carpeta
            con = self.camion_id
            if self.print_output_reference and con.name:
                data_carpeta += 'Referencia de Salida: ' + str(con.name)
            if self.print_mic and con.mic_number:
                data_carpeta += 'MIC: ' + str(con.mic_number)
            if self.print_date_start and con.start_datetime:
                data_carpeta += 'Fecha de Incio: ' + str(con.start_datetime)
            for inv_line in self.invoice_line_ids:
                existe = False
                data = []
                if inv_line.consolidado_service_product_id:
                    prod = inv_line.consolidado_service_product_id
                    if prod.rt_carga_id:
                        # Datos Carga
                        carga = prod.rt_carga_id
                        if carga_anterior != carga.id:
                            string = ''
                            if self.print_invoice_load and carga.name:
                                string += 'Referencia: ' + str(carga.name)
                            if self.print_crt and carga.crt_number:
                                string += ' CRT: ' + str(carga.crt_number)
                            if carga.load_type == 'contenedor':
                                if self.print_container_number and carga.container_number:
                                    string += ' Nº de Contenedor: ' + str(carga.container_number)
                                if self.print_container_size and carga.container_type:
                                    string += ' Tamaño de Contenedor: ' + str(carga.container_type.size)
                                if self.print_booking and carga.booking:
                                    string += ' Booking: ' + str(carga.booking)
                                if self.print_sender and carga.remito:
                                    string += ' Remito: ' + str(carga.remito)
                            if self.print_dua:
                                if carga.dua_aduana and carga.dua_anio and carga.dua_numero:
                                    string += ' DUA: ' + str(carga.dua_aduana) + '-' + str(carga.dua_anio) + '-' + str(
                                        carga.dua_numero)
                                elif con.dua_aduana and con.dua_anio and con.dua_numero:
                                    string += ' DUA: ' + str(con.dua_aduana) + '-' + str(con.dua_anio) + '-' + str(
                                        con.dua_numero)
                            if self.print_packages and carga.package:
                                string += '  ' + str(carga.package) + ' Bultos'
                            if self.print_kg and carga.raw_kg:
                                string += '  ' + str(carga.raw_kg) + ' Kg'
                            if self.print_volume and carga.volume:
                                string += '  ' + str(carga.volume) + ' Mt3'
                            if string:
                                data.append(string)
                            carga_anterior = carga.id
                    #Datos Producto
                    if prod.product_id.name == 'Verificación':
                        producto = 'Verificación aduanera en Midomux/Doraline'
                    else:
                        producto = prod.product_id.name
                    price = inv_line.price_subtotal
                    if list_producto:
                        for l in list_producto:
                            if producto == l[0]:
                                existe = True
                                l[1] += price
                    if not list_producto or not existe:
                        list_producto.append([producto, price])

        return data_carpeta, data_carga, list_producto

    def group_carga(self):
        data = []
        data_carpeta = ''
        data_carga = []
        precios = []
        destino = ''
        carga_anterior = 0
        string = ''
        if self.rt_service_id:
            srv = self.rt_service_id
            if self.print_output_reference and srv.reference:
                data_carpeta = 'Referencia de Salida: ' + str(srv.reference) + ' '
            if srv.dua_type == 'cabezal':
                if srv.dua_aduana and srv.dua_anio and srv.dua_numero:
                    data_carpeta += 'DUA: ' + str(srv.dua_aduana) + '-' + str(
                        srv.dua_anio) + '-' + str(srv.dua_numero)
                if self.print_gex and srv.gex_number:
                    data_carpeta += ' GEX: ' + str(srv.gex_number)
                medidas = self.calcular_medidas(self.invoice_line_ids)
                data_carpeta += medidas
            for inv_line in self.invoice_line_ids:
                existe = False
                if inv_line.rt_service_product_id:
                    prod = inv_line.rt_service_product_id
                    if prod.rt_carga_id:
                        # Datos Carga
                        carga = prod.rt_carga_id
                        if carga_anterior != carga.id:
                            if inv_line.price_subtotal != 0:
                                precios = inv_line.price_subtotal
                                if string:
                                    string += destino
                                    data_carga.append((string, precios))
                                    string = ''
                            else:
                                if string:
                                    string += ' / '
                            if self.print_invoice_load and carga.name:
                                string += str(carga.name)
                            if carga.load_type == 'contenedor':
                                if self.print_container_number and carga.container_number:
                                    string += 'Nº Cont: ' + str(carga.container_number)
                                if self.print_container_number and carga.container_number and carga.container_type:
                                    string += '   '
                                if self.print_container_size and carga.container_type:
                                    string += 'Tamaño Cont: ' + str(carga.container_type.size)
                            if self.print_purchase_order and carga.purchase_order:
                                string += ' O/C: ' + str(carga.purchase_order)
                            if self.print_sender and prod.remito:
                                string += ' Remito: ' + str(prod.remito)
                            if self.print_ms_in_out and srv.mensaje_simplificado:
                                string += ' M/S: ' + str(srv.mensaje_simplificado)
                            if srv.dua_type == 'linea':
                                if self.print_dua:
                                    if not carga.multiple_dua:
                                        if carga.dua_aduana and carga.dua_anio and carga.dua_numero:
                                            string += ' DUA: ' + str(carga.dua_aduana) + '-' + str(
                                                carga.dua_anio) + '-' + str(carga.dua_numero)
                                    if carga.multiple_dua:
                                        dua = ''
                                        for duas in carga.duas_ids:
                                            if dua:
                                                dua += ' / '
                                                dua += str(duas.dua_aduana) + '-' + str(duas.dua_anio) + '-' + str(
                                                    duas.dua_numero)
                                            else:
                                                dua += str(duas.dua_aduana) + '-' + str(duas.dua_anio) + '-' + str(
                                                    duas.dua_numero)
                                        string += ' DUA: ' + dua
                                if self.print_gex and carga.gex_number:
                                    string += ' GEX: ' + str(carga.gex_number)
                                if self.print_packages and carga.package:
                                    string += '  ' + str(carga.package) + ' Bultos'
                                if self.print_kg and carga.raw_kg:
                                    string += '  ' + str(carga.raw_kg) + ' Kg'
                                if self.print_volume and carga.volume:
                                    string += '  ' + str(carga.volume) + ' Mt3'
                            if self.print_origin_destiny and carga.destiny_id.name:
                                destino = ' Destino: ' + str(carga.destiny_id.name)
                            carga_anterior = carga.id

        return data_carga

    def group_origin_destiny_carga(self):
        srv = self.rt_service_id
        lista_dev = []
        for carga in srv.carga_ids:
            if self.tiene_producto_facturable(carga):
                datos = []
                dest = ""
                string = ""
                price = 0
                existe = False
                # Origen y Destino
                if not dest:
                    if carga.destiny_id:
                        dest = carga.destiny_id.name
                _key = ""
                if dest:
                    _key = "Dest. " + str(dest.upper())
                if not _key:
                    _key = "Dest. Desconocido"
                # Datos
                if self.print_invoice_load and carga.name:
                    string = carga.name
                for producto in carga.producto_servicio_ids:
                    if self.esta_en_factura(producto, self.invoice_line_ids):
                        price += producto.importe
                if lista_dev:
                    for li in lista_dev:
                        if _key == li[0]:
                            existe = True
                            li[1][0] += ' / ' + string
                            li[1][1] += price
                if not lista_dev or not existe:
                    lista_dev.append([_key, [string, price]])

        return lista_dev

    def print_all(self):
        information = []
        prod_name = ""
        price = 0
        data_carpeta = []
        if self.rt_service_id:
            # Datos Carpeta
            srv = self.rt_service_id
            if self.print_output_reference and srv.reference:
                data_carpeta.append('Referencia de Salida: ' + str(srv.reference))
            for carga in srv.carga_ids:
                prod_list = []
                data = []
                string = ''
                oridesti = ''
                contenedor = ''
                if self.print_invoice_load and carga.name:
                    data.append('Referencia: ' + str(carga.name))
                if self.print_origin_destiny and carga.origin_id.name:
                    oridesti += 'Origen: ' + str(carga.origin_id.name)
                if self.print_origin_destiny and carga.origin_id.name and carga.destiny_id.name:
                    oridesti += ' - '
                if self.print_origin_destiny and carga.destiny_id.name:
                    oridesti += 'Destino: ' + str(carga.destiny_id.name)
                if oridesti:
                    data.append(oridesti)
                if self.print_mic and carga.mic_number:
                    data.append('MIC: ' + str(carga.mic_number))
                if self.print_crt and carga.crt_number:
                    data.append('CRT: ' + str(carga.crt_number))
                if carga.load_type == 'contenedor':
                    if self.print_container_number and carga.container_number:
                        contenedor += 'Nº de Contenedor: ' + str(carga.container_number)
                    if self.print_container_number and carga.container_number and carga.container_type:
                        contenedor += '   '
                    if self.print_container_size and carga.container_type:
                        contenedor += 'Tamaño de Contenedor: ' + str(carga.container_type.size)
                    if contenedor:
                        data.append(contenedor)
                if self.print_purchase_order and carga.purchase_order:
                    string += ' O/C: ' + str(carga.purchase_order)
                if self.print_delivery_order and carga.delivery_order:
                    string += ' Delivery Order: ' + str(carga.delivery_order)
                if self.print_booking and carga.booking:
                    string += ' Booking: ' + str(carga.booking)
                if self.print_ms_in_out and srv.mensaje_simplificado:
                    string += ' M/S: ' + str(srv.mensaje_simplificado)
                if self.print_dua:
                    if srv.dua_type == 'linea':
                        if not carga.multiple_dua:
                            if carga.dua_aduana and carga.dua_anio and carga.dua_numero:
                                string += ' DUA: ' + str(carga.dua_aduana) + '-' + str(
                                    carga.dua_anio) + '-' + str(carga.dua_numero)
                        if carga.multiple_dua:
                            dua = ''
                            for duas in carga.duas_ids:
                                if dua:
                                    dua += ' / '
                                    dua += str(duas.dua_aduana) + '-' + str(duas.dua_anio) + '-' + str(
                                        duas.dua_numero)
                                else:
                                    dua += str(duas.dua_aduana) + '-' + str(duas.dua_anio) + '-' + str(
                                        duas.dua_numero)
                            string += ' DUA: ' + dua
                        if self.print_gex and carga.gex_number:
                            string += ' GEX: ' + str(carga.gex_number)
                    if srv.dua_type == 'cabezal':
                        if srv.dua_aduana and srv.dua_anio and srv.dua_numero:
                            string += ' DUA: ' + str(srv.dua_aduana) + '-' + str(
                                srv.dua_anio) + '-' + str(srv.dua_numero)
                        if self.print_gex and srv.gex_number:
                            string += ' GEX: ' + str(srv.gex_number)
                if self.print_packages and carga.package:
                    string += '  ' + str(carga.package) + ' Bultos'
                if self.print_kg and carga.raw_kg:
                    string += '  ' + str(carga.raw_kg) + ' Kg'
                if self.print_volume and carga.volume:
                    string += '  ' + str(carga.volume) + ' Mt3'
                if string:
                    data.append(string)
                information.append(data)
            # Datos Producto
            for inv_line in self.invoice_line_ids:
                prod = inv_line.rt_service_product_id
                if prod.importe != 0:
                    if prod.product_id.name != 'Flete':
                        if self.print_invoice_product and prod.name:
                            prod_name = 'Referencia: ' + str(prod.name)
                            if prod.product_id.name == 'Verificación':
                                prod_name = 'Verificación aduanera en Midomux/Doraline'
                        else:
                            if prod.product_id:
                                prod_name = str(prod.product_id.name)
                    if prod.product_id.name == 'Flete':
                        if self.print_invoice_product and prod.name:
                            prod_name = 'Referencia: ' + str(prod.name)
                        else:
                            if inv_line.price_subtotal != 0:
                                prod_name = str(prod.product_id.name)
                            else:
                                prod_name = ''
                    price = inv_line.price_subtotal
                    prod_list.append((prod_name, price))

        return data_carpeta, information, prod_list


    def get_lines(self):
        ids = []
        for record in self:
            inv_lns = self.env['account.invoice.line']
            lines = inv_lns.search([('invoice_id', '=', record.id)])
        nombre = ''
        for line in lines:
            if nombre != line.product_id.name:
                ids.append(line.id)
                nombre = line.product_id.name

        lines = self.env['account.invoice.line'].search([('id', 'in', ids)])

        return lines

    def get_amount_taxed_by_22(self):
        iva22_id = self.env['account.tax.group'].search([('name', '=', 'IVA 22%')]).id
        if not iva22_id:
            raise Warning('IVA 22% tax group not found')
            return False
        for record in self:
            lines = record.get_lines()
            amount = 0
            for l in lines:
                for t in l.invoice_line_tax_ids:
                    if t.tax_group_id.id == iva22_id:
                        amount = amount + l.price_subtotal
            return amount

    def get_amount_taxed_by_10(self):
        iva10_id = self.env['account.tax.group'].search([('name', '=', 'IVA 10%')]).id
        if not iva10_id:
            raise Warning('IVA 10% tax group not found')
            return False
        for record in self:
            lines = record.get_lines()
            amount = 0
            for l in lines:
                for t in l.invoice_line_tax_ids:
                    if t.tax_group_id.id == iva10_id:
                        amount = amount + l.price_subtotal
            return amount
