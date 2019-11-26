# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError, Warning
import ipdb
from odoo.addons import decimal_precision as dp
import itertools

class MakeInvoice(models.TransientModel):
    _name = 'rt.service.product.make.invoice'
    _description = 'Create Mass Invoice (repair)'


    group = fields.Boolean('Group by partner invoice address')
    group_by_product = fields.Boolean('Agrupar por Producto')
    amount_nat = fields.Float(string='% A facturar Nacional', digits=dp.get_precision('Account'))
    amount_inter = fields.Float(string='% A facturar Internacional', digits=dp.get_precision('Account'))
    advance_payment_method = fields.Selection(
        selection=[('all', 'Facturar Servicios Seleccionados'), ('percentage', 'Facturar un tramo')], string='¿Qué desea facturar?', required=True,
        readonly=False)
    tramo_a_facturar = fields.Selection([('national', 'Nacional'), ('internacional', 'Internacional')],
                                        string='Tramo a Facturar')
    amount = fields.Float(string='% A facturar', digits=dp.get_precision('Account'),
                          help="The amount to be invoiced in advance.")
    regimen = fields.Selection([('transit_nat', '80 - Transito Nacional'),
                              ('impo_nat', '10 - IMPO Nacional'),
                              ('expo_nat', '40 - EXPO Nacional'),
                              ('interno_plaza_nat', 'Interno Plaza Nacional'),
                              ('interno_fiscal_nat', 'Interno Fiscal Nacional'),
                              ('transit_inter_in', '80 - Transito Internacional Ingreso'),
                              ('transit_inter_out', '80 - Transito Internacional Salida'),
                              ('impo_inter', '10 - IMPO Internacional'),
                              ('expo_inter', '40 - EXPO Internacional')])
    operation_type = fields.Selection([('national', 'Nacional'), ('international', 'Internacional')],
                                      string='Tipo de Servicio')

    @api.multi
    def actualiza_estado_calendario(self, carpeta=None, estado=None):
        estados_obj = self.env['color.picker']
        calendario_obj = self.env['servicio.calendario']

        realizada_facturada = estados_obj.search([('name', '=', 'Carga Realizada y Facturada')])
        factura_rechazada = estados_obj.search([('name', '=', 'Factura Rechazada')])
        if carpeta:
            calendarios = calendario_obj.search([('rt_service_id', '=', carpeta.id)])
            for calendario in calendarios:
                if estado == 'Facturado':
                    calendario.color_pickier_id = realizada_facturada.id

    @api.multi
    @api.onchange('group', 'advance_payment_method')
    def get_regimen_oncha(self):
        ps_obj = self.env['rt.service.productos']
        for rec in self:
            if not rec.group:
                context = rec._context
                active_is = context.get('active_ids', [])
                for ps in ps_obj.browse(active_is):
                    rec.regimen = ps.regimen
                    rec.operation_type = ps.operation_type
                    if ps.pricelist_id:
                        rec.amount_nat = ps.pricelist_id.invoice_nat_per
                        rec.amount_inter = ps.pricelist_id.invoice_int_per
                    else:
                        rec.amount_nat = 40
                        rec.amount_inter = 60

    def cargar_campos_impresion(self, partner, invoice):
        invoice.print_output_reference = partner.print_output_reference
        invoice.print_origin_destiny_grouped = partner.print_origin_destiny_grouped
        invoice.print_cont_grouped = partner.print_cont_grouped
        invoice.print_product_grouped = partner.print_product_grouped
        invoice.print_invoice_load = partner.print_invoice_load
        invoice.print_invoice_product = partner.print_invoice_product
        invoice.print_date_start = partner.print_date_start
        invoice.print_ms_in_out = partner.print_ms_in_out
        invoice.print_delivery_order = partner.print_delivery_order
        invoice.print_mic = partner.print_mic
        invoice.print_crt = partner.print_crt
        invoice.print_consignee = partner.print_consignee
        invoice.print_purchase_order = partner.print_purchase_order
        invoice.print_origin_destiny = partner.print_origin_destiny
        invoice.print_container_number = partner.print_container_number
        invoice.print_container_size = partner.print_container_size
        invoice.print_booking = partner.print_booking
        invoice.print_gex = partner.print_gex
        invoice.print_sender = partner.print_sender
        invoice.print_dua = partner.print_dua
        invoice.print_packages = partner.print_packages
        invoice.print_kg = partner.print_kg
        invoice.print_volume = partner.print_volume
        invoice.print_extra_info = partner.print_extra_info
        invoice.show_extra_info = partner.show_extra_info

    def calcular_diario(self, partner_id):
        journal_obj = self.env['account.journal']
        if partner_id.vat_type == '2' and partner_id.country_id.code == 'UY':
            # e-Factura
            journal_id = journal_obj.search([('code', '=', 'EF')]).id
        if (partner_id.vat_type == '4' and partner_id.country_id.code != 'UY') or partner_id.vat_type == '3':
            # e-Ticket
            journal_id = journal_obj.search([('code', '=', 'ET')]).id

        return journal_id

    def calcular_delivery_order(self, productos):
        delivery_order = ''
        carga_anterior = 0
        for prod in productos:
            if prod.rt_carga_id:
                carga = prod.rt_carga_id
                if carga.id != carga_anterior and carga.delivery_order:
                    delivery_order += carga.delivery_order + '\n'
                carga_anterior = carga.id
        return delivery_order

    def get_regimen(self, lineas_producto):
        regimen = []
        regimen_to_return = ''
        if lineas_producto:
            for line in lineas_producto:
                if line.regimen_excepcion:
                    regimen.append(line.regimen_excepcion)
                    regimen_to_return = line.regimen_excepcion
                else:
                    regimen.append(line.rt_service_id.regimen)
                    regimen_service = line.rt_service_id.regimen
            if not regimen_to_return:
                regimen_to_return = regimen_service
        if len(set(regimen)) > 1:
            raise Warning('El conjunto de regimenes no puede ser mayor a 1, revise')

        return regimen_to_return

    @api.multi
    def facturar_regimen_transito_in(self, product_service):
        if self.advance_payment_method == 'all':
            raise Warning('No se puede facturar entera una IMPO')
        account_obj = self.env['account.account']
        tax_obj = self.env['account.tax']
        carpeta_obj = self.env['rt.service']
        operation_taxes = {
            'exento': False,
            'asimilado': tax_obj.search([('name', '=', 'IVA Venta asimilado a exportación')]),
            'gravado': tax_obj.search([('name', '=', 'IVA Ventas (22%)')])
        }

        lineas = []
        for line in product_service:
            id_carpeta = line.rt_service_id.id
            carpeta = carpeta_obj.browse(id_carpeta)
            account = account_obj.search([('code', '=', '41031007')])
            taxes = operation_taxes['asimilado']
            line_dict = {}
            if self.advance_payment_method == 'percentage':
                # TRAMO INTERNACIONAL
                if self.tramo_a_facturar == 'internacional':
                    if line.tramo_inter:
                        raise Warning('Ya se facturo el tramo internacional')
                    else:
                        taxes = operation_taxes['asimilado']
                        account = account_obj.search([('code', '=', '41031007')])
                        if line.product_id.name == 'Flete':
                            line_dict['name'] = line.name or ''  # 'TRAMO INTERNACIONAL'
                            line_dict['account_id'] = account.id
                            line_dict['price_unit'] = line.importe * self.amount / 100
                            line_dict['uom_id'] = line.product_id.uom_id.id
                            line_dict['tramo_facturado'] = 'international'
                            line_dict['product_id'] = line.product_id.id
                            line_dict['rt_service_product_id'] = line.id
                            line_dict['invoice_line_tax_ids'] = [(6, 0, taxes.ids)]
                            lineas.append((0, 0, line_dict))
                            line.tramo_inter = True
                            if line.tramo_inter and line.tramo_nat:
                                # Facturado
                                line.invoiced = True
                        else:
                            line_dict['name'] = line.name or ''
                            line_dict['account_id'] = account.id
                            line_dict['price_unit'] = line.importe
                            line_dict['uom_id'] = line.product_id.uom_id.id
                            line_dict['product_id'] = line.product_id.id
                            line_dict['rt_service_product_id'] = line.id
                            line_dict['invoice_line_tax_ids'] = [(6, 0, taxes.ids)]
                            lineas.append((0, 0, line_dict))
                            # Facturado
                            line.invoiced = True

                # TRAMO NACIONAL
                if self.tramo_a_facturar == 'national':
                    if line.tramo_nat:
                        raise Warning('Ya se facturo el tramo nacional')
                    else:
                        taxes = operation_taxes['gravado']
                        account = account_obj.search([('code', '=', '41031008')])
                        if line.product_id.name == 'Flete':
                            line_dict['name'] = line.name or ''  # 'TRAMO NACIONAL'
                            line_dict['account_id'] = account.id
                            line_dict['price_unit'] = line.importe * self.amount / 100
                            line_dict['uom_id'] = line.product_id.uom_id.id
                            line_dict['tramo_facturado'] = 'national'
                            line_dict['product_id'] = line.product_id.id
                            line_dict['rt_service_product_id'] = line.id
                            line_dict['invoice_line_tax_ids'] = [(6, 0, taxes.ids)]
                            lineas.append((0, 0, line_dict))
                            line.tramo_nat = True
                            if line.tramo_nat and line.tramo_inter:
                                # Facturado
                                line.invoiced = True
                        else:
                            line_dict['name'] = line.name or ''
                            line_dict['account_id'] = account.id
                            line_dict['price_unit'] = line.importe
                            line_dict['uom_id'] = line.product_id.uom_id.id
                            line_dict['product_id'] = line.product_id.id
                            line_dict['rt_service_product_id'] = line.id
                            line_dict['invoice_line_tax_ids'] = [(6, 0, taxes.ids)]
                            lineas.append((0, 0, line_dict))
                            # Facturado
                            line.invoiced = True

            else:
                line_dict['name'] = line.name or ''
                line_dict['account_id'] = account.id
                line_dict['price_unit'] = line.importe
                line_dict['uom_id'] = line.product_id.uom_id.id
                line_dict['product_id'] = line.product_id.id
                line_dict['rt_service_product_id'] = line.id
                line_dict['invoice_line_tax_ids'] = [(6, 0, taxes.ids)]
                lineas.append((0, 0, line_dict))
                # Facturado
                line.invoiced = True

        return lineas, carpeta

    @api.multi
    def facturar_regimen_transito_out(self, product_service):
        account_obj = self.env['account.account']
        tax_obj = self.env['account.tax']
        carpeta_obj = self.env['rt.service']
        operation_taxes = {
            'exento': False,
            'asimilado': tax_obj.search([('name', '=', 'IVA Venta asimilado a exportación')]),
            'gravado': tax_obj.search([('name', '=', 'IVA Ventas (22%)')])
        }
        lineas = []
        for line in product_service:
            id_carpeta = line.rt_service_id.id
            carpeta = carpeta_obj.browse(id_carpeta)
            account_nat = account_obj.search([('code', '=', '41031006')])
            account_inter = account_obj.search([('code', '=', '41031005')])
            taxes = operation_taxes['asimilado']
            line_dict_inter = {}
            line_dict_nat = {}
            line_dict = {}
            if line.product_id.name == 'Flete':
                # TRAMO INTERNACIONAL
                line_dict_inter['name'] = line.name or ''#'TRAMO INTERNACIONAL'
                line_dict_inter['account_id'] = account_inter.id
                line_dict_inter['price_unit'] = line.importe * self.amount_inter / 100
                line_dict_inter['uom_id'] = line.product_id.uom_id.id
                line_dict_inter['product_id'] = line.product_id.id
                line_dict_inter['rt_service_product_id'] = line.id
                line_dict_inter['invoice_line_tax_ids'] = [(6, 0, taxes.ids)]
                lineas.append((0, 0, line_dict_inter))

                # TRAMO NACIONAL
                line_dict_nat['name'] = line.name or '' #'TRAMO NACIONAL'
                line_dict_nat['account_id'] = account_nat.id
                line_dict_nat['price_unit'] = line.importe * self.amount_nat / 100
                line_dict_nat['uom_id'] = line.product_id.uom_id.id
                line_dict_nat['product_id'] = line.product_id.id
                line_dict_nat['rt_service_product_id'] = line.id
                line_dict_nat['invoice_line_tax_ids'] = [(6, 0, taxes.ids)]
                lineas.append((0, 0, line_dict_nat))
            else:
                line_dict['name'] = line.name or ''
                line_dict['account_id'] = account_inter.id
                line_dict['price_unit'] = line.importe
                line_dict['uom_id'] = line.product_id.uom_id.id
                line_dict['product_id'] = line.product_id.id
                line_dict['rt_service_product_id'] = line.id
                line_dict['invoice_line_tax_ids'] = [(6, 0, taxes.ids)]
                lineas.append((0, 0, line_dict))
            # Facturado
            line.invoiced = True

        return lineas, carpeta

    @api.multi
    def facturar_regimen_expo(self, product_service):
        account_obj = self.env['account.account']
        tax_obj = self.env['account.tax']
        carpeta_obj = self.env['rt.service']
        operation_taxes = {
            'exento': False,
            'asimilado': tax_obj.search([('name', '=', 'IVA Venta asimilado a exportación')]),
            'gravado': tax_obj.search([('name', '=', 'IVA Ventas (22%)')])
        }
        lineas = []
        for line in product_service:
            id_carpeta = line.rt_service_id.id
            carpeta = carpeta_obj.browse(id_carpeta)
            account_inter = account_obj.search([('code', '=', '41031001')])
            account_nat = account_obj.search([('code', '=', '41031002')])
            taxes = operation_taxes['asimilado']
            line_dict_inter = {}
            line_dict_nat = {}
            line_dict = {}
            if line.product_id.name == 'Flete':
                # TRAMO INTERNACIONAL
                line_dict_inter['name'] = line.name or ''#'TRAMO INTERNACIONAL'
                line_dict_inter['account_id'] = account_inter.id
                line_dict_inter['price_unit'] = line.importe * self.amount_inter / 100
                line_dict_inter['uom_id'] = line.product_id.uom_id.id
                line_dict_inter['product_id'] = line.product_id.id
                line_dict_inter['rt_service_product_id'] = line.id
                line_dict_inter['invoice_line_tax_ids'] = [(6, 0, taxes.ids)]
                lineas.append((0, 0, line_dict_inter))

                # TRAMO NACIONAL
                line_dict_nat['name'] = line.name or '' #'TRAMO NACIONAL'
                line_dict_nat['account_id'] = account_nat.id
                line_dict_nat['price_unit'] = line.importe * self.amount_nat / 100
                line_dict_nat['uom_id'] = line.product_id.uom_id.id
                line_dict_nat['product_id'] = line.product_id.id
                line_dict_nat['rt_service_product_id'] = line.id
                line_dict_nat['invoice_line_tax_ids'] = [(6, 0, taxes.ids)]
                lineas.append((0, 0, line_dict_nat))
            else:
                line_dict['name'] = line.name or ''
                line_dict['account_id'] = account_inter.id
                line_dict['price_unit'] = line.importe
                line_dict['uom_id'] = line.product_id.uom_id.id
                line_dict['product_id'] = line.product_id.id
                line_dict['rt_service_product_id'] = line.id
                line_dict['invoice_line_tax_ids'] = [(6, 0, taxes.ids)]
                lineas.append((0, 0, line_dict))
            # Facturado
            line.invoiced = True

        return lineas, carpeta

    @api.multi
    def facturar_regimen_impo(self, product_service):
        if self.advance_payment_method == 'all':
            raise Warning('No se puede facturar entera una IMPO')
        account_obj = self.env['account.account']
        tax_obj = self.env['account.tax']
        carpeta_obj = self.env['rt.service']
        operation_taxes = {
            'exento': False,
            'asimilado': tax_obj.search([('name', '=', 'IVA Venta asimilado a exportación')]),
            'gravado': tax_obj.search([('name', '=', 'IVA Ventas (22%)')])
        }

        lineas = []
        for line in product_service:
            id_carpeta = line.rt_service_id.id
            carpeta = carpeta_obj.browse(id_carpeta)
            account = account_obj.search([('code', '=', '41031003')])
            taxes = operation_taxes['asimilado']
            line_dict = {}
            if self.advance_payment_method == 'percentage':
                # TRAMO INTERNACIONAL
                if self.tramo_a_facturar == 'internacional':
                    if line.tramo_inter:
                        raise Warning('Ya se facturo el tramo internacional')
                    else:
                        taxes = operation_taxes['asimilado']
                        account = account_obj.search([('code', '=', '41031003')])
                        if line.product_id.name == 'Flete':
                            line_dict['name'] = line.name or ''#'TRAMO INTERNACIONAL'
                            line_dict['account_id'] = account.id
                            line_dict['price_unit'] = line.importe * self.amount / 100
                            line_dict['uom_id'] = line.product_id.uom_id.id
                            line_dict['tramo_facturado'] = 'international'
                            line_dict['product_id'] = line.product_id.id
                            line_dict['rt_service_product_id'] = line.id
                            line_dict['invoice_line_tax_ids'] = [(6, 0, taxes.ids)]
                            lineas.append((0, 0, line_dict))
                            line.tramo_inter = True
                            if line.tramo_inter and line.tramo_nat:
                                # Facturado
                                line.invoiced = True
                        else:
                            line_dict['name'] = line.name or ''
                            line_dict['account_id'] = account.id
                            line_dict['price_unit'] = line.importe
                            line_dict['uom_id'] = line.product_id.uom_id.id
                            line_dict['product_id'] = line.product_id.id
                            line_dict['rt_service_product_id'] = line.id
                            line_dict['invoice_line_tax_ids'] = [(6, 0, taxes.ids)]
                            lineas.append((0, 0, line_dict))
                            # Facturado
                            line.invoiced = True

                # TRAMO NACIONAL
                if self.tramo_a_facturar == 'national':
                    if line.tramo_nat:
                        raise Warning('Ya se facturo el tramo nacional')
                    else:
                        taxes = operation_taxes['gravado']
                        account = account_obj.search([('code', '=', '41031004')])
                        if line.product_id.name == 'Flete':
                            line_dict['name'] = line.name or '' #'TRAMO NACIONAL'
                            line_dict['account_id'] = account.id
                            line_dict['price_unit'] = line.importe * self.amount / 100
                            line_dict['uom_id'] = line.product_id.uom_id.id
                            line_dict['tramo_facturado'] = 'national'
                            line_dict['product_id'] = line.product_id.id
                            line_dict['rt_service_product_id'] = line.id
                            line_dict['invoice_line_tax_ids'] = [(6, 0, taxes.ids)]
                            lineas.append((0, 0, line_dict))
                            line.tramo_nat = True
                            if line.tramo_nat and line.tramo_inter:
                                # Facturado
                                line.invoiced = True
                        else:
                            line_dict['name'] = line.name or ''
                            line_dict['account_id'] = account.id
                            line_dict['price_unit'] = line.importe
                            line_dict['uom_id'] = line.product_id.uom_id.id
                            line_dict['product_id'] = line.product_id.id
                            line_dict['rt_service_product_id'] = line.id
                            line_dict['invoice_line_tax_ids'] = [(6, 0, taxes.ids)]
                            lineas.append((0, 0, line_dict))
                            # Facturado
                            line.invoiced = True

            else:
                line_dict['name'] = line.name or ''
                line_dict['account_id'] = account.id
                line_dict['price_unit'] = line.importe
                line_dict['uom_id'] = line.product_id.uom_id.id
                line_dict['product_id'] = line.product_id.id
                line_dict['rt_service_product_id'] = line.id
                line_dict['invoice_line_tax_ids'] = [(6, 0, taxes.ids)]
                lineas.append((0, 0, line_dict))
                # Facturado
                line.invoiced = True

        return lineas, carpeta

    def _group_by_product(self, product_service=None):
        lista_prod = []
        for producto in product_service:
            existe = False
            if lista_prod:
                for product_name in lista_prod:

                    if producto.product_id.name == product_name[0]:
                        existe = True
                        product_name[1][1] += producto.importe
                        product_name[1][2].append(producto.id)
            if not lista_prod or not existe:
                lista_prod.append([producto.product_id.name, [producto, producto.importe, [producto.id]]])

        return lista_prod

    def poner_facturado_los_productos(self, productos=None):
        if productos:
            for prod in productos:
                prod.invoiced = True

    def generar_costos(self, carpetas=None):
        """
        Recorre las cargas, recorre los servicios.
        Si es de terceros, gastos y tiene proveedor y moneda y valor de compra
        Crea el objeto de costo
        :return:
        """
        regimen_map = {
            'transit_nat': 'Transito Nacional',
            'impo_nat': 'IMPO Nacional',
            'expo_nat': 'EXPO Nacional',
            'interno_plaza_nat': 'Interno Plaza Nacional',
            'interno_fiscal_nat': 'Interno Fiscal Nacional',
            'transit_inter_in': 'Transito Internacional Ingreso',
            'transit_inter_out': 'Transito Internacional Salida',
            'impo_inter': 'IMPO Internacional',
            'expo_inter': 'EXPO Internacional',
        }
        regimen = regimen_map[self.regimen]
        regimen_obj = self.env['regimenes']
        regimen_id = regimen_obj.search([('name', '=', regimen)])
        tax_obj = self.env['account.tax']
        taxes = tax_obj.search([('regimen_ids', 'in', regimen_id.ids)])
        cost_obj = self.env['rt.service.product.supplier']
        for carpeta in carpetas:
            for carga in carpeta.carga_ids:
                for producto in carga.producto_servicio_ids:
                    if producto.product_type == 'terceros' and producto.is_outgoing:
                        if producto.supplier_id:
                            if producto.valor_compra:
                                if producto.valor_compra_currency_id:
                                    if producto.supplier_ids:
                                        for prod in producto.supplier_ids:
                                            if not prod.invoice_id:
                                                prod.unlink()
                                    """
                                    aca va ir todo el codigo supongo
                                    """
                                    line_dict = {}
                                    line_dict['ref'] = carpeta.name
                                    line_dict['supplier_id'] = producto.supplier_id.id
                                    line_dict['currency_id'] = producto.valor_compra_currency_id.id
                                    line_dict['amount'] = producto.valor_compra
                                    line_dict['price_subtotal'] = float(producto.valor_compra * (1 + (taxes.amount / 100)))
                                    line_dict['rt_service_id'] = carpeta.id
                                    line_dict['rt_service_product_id'] = producto.id
                                    line_dict['service_state'] = carpeta.state
                                    line_dict['tax_ids'] = [(6, 0, taxes.ids)]
                                    line_dict['service_date'] = producto.start
                                    line_dict['tack_id'] = producto.get_tack_id()
                                    line_dict['dua'] = producto.get_dua()
                                    line_dict['mic'] = producto.get_mic()
                                    line_dict['crt'] = producto.get_crt()
                                    line_dict['origin_id'] = producto.origin_id.id
                                    line_dict['destiny_id'] = producto.destiny_id.id
                                    line_dict['product_id'] = producto.product_id.id
                                    line_dict['output_reference'] = producto.name
                                    line_dict['partner_invoice_id'] = producto.partner_invoice_id.id
                                    # lineas.append((0, 0, line_dict))
                                    result = cost_obj.create(line_dict)
                                    print('aca va el codigo')
                                else:
                                    raise Warning('No tiene importe')
                            else:
                                raise Warning('No tiene moneda')


                        else:
                            raise Warning('No tiene Proveedor')

    @api.multi
    def make_invoices(self):
        inv_obj = self.env['account.invoice']

        if not self._context.get('active_ids'):
            return {'type': 'ir.actions.act_window_close'}
        product_service = self.env['rt.service.productos'].browse(self._context.get('active_ids'))
        regimen = self.get_regimen(product_service)
        self.regimen = regimen
        tax_obj = self.env['account.tax']
        account_obj = self.env['account.account']
        operation_taxes = {
                           'exento': False,
                           'asimilado': tax_obj.search([('name', '=', 'IVA Venta asimilado a exportación')]),
                           'gravado': tax_obj.search([('name', '=', 'IVA Ventas (22%)')])
        }

        lineas = []
        carpeta = False
        if self.group_by_product:
            original_product_service = product_service
            product_service = self._group_by_product(product_service=product_service)
        for line in product_service:
            if self.group_by_product:
                precio = line[1][1]
                ids = line[1][2]
                line = line[1][0]
            if line.operation_type == 'national':
                carpeta = line.rt_service_id
                if line.regimen == 'impo_nat':
                    taxes = operation_taxes['gravado']
                    account = account_obj.search([('code', '=', '41012001')])
                    line_dict = {}
                    line_dict['name'] = line.name
                    line_dict['account_id'] = account.id
                    line_dict['uom_id'] = line.product_id.uom_id.id
                    line_dict['product_id'] = line.product_id.id
                    if self.group_by_product:
                        line_dict['price_unit'] = precio
                        line_dict['rt_service_product_ids'] = [(4, id) for id in ids]
                    else:
                        line_dict['price_unit'] = line.importe
                        line_dict['rt_service_product_id'] = line.id
                    line_dict['invoice_line_tax_ids'] = [(6, 0, taxes.ids)]
                    lineas.append((0, 0, line_dict))
                    #Facturado
                    line.invoiced = True

                if line.regimen == 'expo_nat':
                    taxes = operation_taxes['asimilado']
                    account = account_obj.search([('code', '=', '41013001')])
                    line_dict = {}
                    line_dict['name'] = line.name
                    line_dict['account_id'] = account.id
                    line_dict['uom_id'] = line.product_id.uom_id.id
                    line_dict['product_id'] = line.product_id.id
                    if self.group_by_product:
                        line_dict['price_unit'] = precio
                        line_dict['rt_service_product_ids'] = [(4, id) for id in ids]
                    else:
                        line_dict['price_unit'] = line.importe
                        line_dict['rt_service_product_id'] = line.id
                    line_dict['invoice_line_tax_ids'] = [(6, 0, taxes.ids)]
                    lineas.append((0, 0, line_dict))
                    #Facturado
                    line.invoiced = True

                if line.regimen == 'interno_plaza_nat':
                    taxes = operation_taxes['gravado']
                    account = account_obj.search([('code', '=', '41012001')])
                    line_dict = {}
                    line_dict['name'] = line.name
                    line_dict['account_id'] = account.id
                    line_dict['uom_id'] = line.product_id.uom_id.id
                    line_dict['product_id'] = line.product_id.id
                    if self.group_by_product:
                        line_dict['price_unit'] = precio
                        line_dict['rt_service_product_ids'] = [(4, id) for id in ids]
                    else:
                        line_dict['price_unit'] = line.importe
                        line_dict['rt_service_product_id'] = line.id
                    line_dict['invoice_line_tax_ids'] = [(6, 0, taxes.ids)]
                    lineas.append((0, 0, line_dict))
                    #Facturado
                    line.invoiced = True

                if line.regimen == 'interno_fiscal_nat':
                    taxes = operation_taxes['asimilado']
                    account = account_obj.search([('code', '=', '41012002')])
                    line_dict = {}
                    line_dict['name'] = line.name
                    line_dict['account_id'] = account.id
                    line_dict['uom_id'] = line.product_id.uom_id.id
                    line_dict['product_id'] = line.product_id.id
                    if self.group_by_product:
                        line_dict['price_unit'] = precio
                        line_dict['rt_service_product_ids'] = [(4, id) for id in ids]
                    else:
                        line_dict['price_unit'] = line.importe
                        line_dict['rt_service_product_id'] = line.id
                    line_dict['invoice_line_tax_ids'] = [(6, 0, taxes.ids)]
                    lineas.append((0, 0, line_dict))
                    # Facturado
                    line.invoiced = True

                if line.regimen == 'transit_nat':
                    taxes = operation_taxes['asimilado']
                    account = account_obj.search([('code', '=', '41013002')])
                    line_dict = {}
                    line_dict['name'] = line.name
                    line_dict['account_id'] = account.id
                    line_dict['uom_id'] = line.product_id.uom_id.id
                    line_dict['product_id'] = line.product_id.id
                    if self.group_by_product:
                        line_dict['price_unit'] = precio
                        line_dict['rt_service_product_ids'] = [(4, id) for id in ids]
                    else:
                        line_dict['price_unit'] = line.importe
                        line_dict['rt_service_product_id'] = line.id
                    line_dict['invoice_line_tax_ids'] = [(6, 0, taxes.ids)]
                    lineas.append((0, 0, line_dict))
                    #Facturado
                    line.invoiced = True

                self.actualiza_estado_calendario(carpeta=carpeta, estado='Facturado')

            if line.operation_type == 'international':
                carpeta = line.rt_service_id

        if line.operation_type == 'international':
            carpeta = line.rt_service_id
            if regimen == 'transit_inter_out':
                lineas, carpeta = self.facturar_regimen_transito_out(product_service)
                self.actualiza_estado_calendario(carpeta=carpeta, estado='Facturado')
            if regimen == 'transit_inter_in':
                lineas, carpeta = self.facturar_regimen_transito_in(product_service)
                self.actualiza_estado_calendario(carpeta=carpeta, estado='Facturado')
            if regimen == 'expo_inter':
                lineas, carpeta = self.facturar_regimen_expo(product_service)
                self.actualiza_estado_calendario(carpeta=carpeta, estado='Facturado')
            if regimen == 'impo_inter':
                lineas, carpeta = self.facturar_regimen_impo(product_service)
                self.actualiza_estado_calendario(carpeta=carpeta, estado='Facturado')

        journal_id = self.calcular_diario(line.rt_service_id.partner_invoice_id)
        if self.group_by_product:
            delivery_order = self.calcular_delivery_order(original_product_service)
        else:
            delivery_order = self.calcular_delivery_order(product_service)

        if not lineas:
            raise Warning('No se crearon lineas \n Contacte el departamento técnico')
        invoice = inv_obj.create({
            'name': line.rt_service_id.partner_invoice_id.name or '',
            'origin': line.name,
            'type': 'out_invoice',
            'account_id': line.rt_service_id.partner_invoice_id.property_account_receivable_id.id,
            'partner_id': line.rt_service_id.partner_invoice_id.id,
            'journal_id': journal_id,
            'comment': delivery_order,
            'currency_id': line.currency_id.id,
            'fiscal_position_id': line.rt_service_id.partner_invoice_id.property_account_position_id.id,
            'company_id': line.rt_service_id.company_id.id,
            'user_id': line.rt_service_id.user_id and line.rt_service_id.user_id.id,
            'rt_service_product_id': line.id,
            'rt_service_id': line.rt_service_id.id,
            'invoice_line_ids': lineas
        })

        line.invoices_ids += invoice
        line.rt_service_id.invoices_ids += invoice
        line.rt_service_id.state = 'progress'

        partner = line.rt_service_id.partner_invoice_id
        self.cargar_campos_impresion(partner, invoice)

        self.actualiza_estado_calendario(carpeta=carpeta, estado='Facturado')
        self.generar_costos(carpetas=carpeta)

        if self.group_by_product:
            self.poner_facturado_los_productos(productos=original_product_service)

        if self._context['open_invoices']:
            return {
                'domain': [('id', 'in', invoice.ids)],
                'name': 'Invoices',
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'account.invoice',
                'view_id': False,
                'views': [(self.env.ref('account.invoice_tree').id, 'tree'),
                          (self.env.ref('account.invoice_form').id, 'form')],
                'context': "{'type':'out_invoice'}",
                'type': 'ir.actions.act_window'
            }
        else:
            return {'type': 'ir.actions.act_window_close'}


