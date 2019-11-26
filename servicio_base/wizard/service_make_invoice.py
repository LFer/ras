# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo import api, fields, models, tools, SUPERUSER_ID, _
from odoo.exceptions import UserError, AccessError, ValidationError, Warning
from odoo.tools.safe_eval import safe_eval
from odoo.addons import decimal_precision as dp
import ipdb

class rt_service_advance_payment_inv(models.Model):
    _name = "rt.service.advance.payment.inv"
    _description = "Service Advance Payment Invoice"

    def comprobar_costos(self, carpeta=None):
        if carpeta:
            for carga in carpeta.carga_ids:
                for producto in carga.producto_servicio_ids:
                    if producto.product_type == 'terceros' and not producto.alquilado and producto.is_outgoing:
                        if not producto.supplier_id or not producto.valor_compra_currency_id or not producto.valor_compra:
                            raise Warning("No ha generado los costos para esta Carpeta. \n Revise el producto %s de la carga %s)" % (producto.name, producto.rt_carga_id.seq))
                        if not producto.supplier_ids:
                            raise Warning("No ha generado los costos para esta Carpeta. \n Revise el producto %s de la carga %s)" % (producto.name, producto.rt_carga_id.seq))

    @api.multi
    def create_invoices(self):
        """ create invoices for the active service """
        context = self._context.copy()
        srv_ids = context.get('active_ids', [])
        act_window = self.env['ir.actions.act_window']
        wizard = self
        carpeta = self.env['rt.service'].browse(srv_ids)
        if wizard.advance_payment_method == 'lines':
            # open the list view of service product to invoice
            res = act_window.for_xml_id('servicio_base', 'action_rt_service_product_tree2')
            # context
            _pay_method = self.fields_get(allfields=['advance_payment_method'], attributes=['selection'])
            res['context'] = {
                'search_default_uninvoiced': 1,
                'search_default_filter_currency': 1 if _pay_method and _pay_method.get('advance_payment_method', {}).get('selection', [('all',)])[0][0] == 'lines' else 0
            }
            # domain
            if srv_ids:
                if not res.get('domain', False) or not isinstance(res.get('domain', False), (list,)):
                    res['domain'] = []
                res['domain'].append(('rt_service_id', 'in', srv_ids))
                res['domain'].append(('invoiced', '=', False))
                res['domain'].append(('is_invoiced', '=', True))
            return res
        if wizard.advance_payment_method == 'percentage':
            return self.make_invoices()

        if wizard.advance_payment_method == 'all':
            carpeta = self.env['rt.service'].browse(srv_ids)
            return carpeta.facturar_carpeta(self.amount_nat, self.amount_inter, self.amount, self.advance_payment_method, self.group_by_product)

    rt_service_id = fields.Many2one(comodel_name='rt.service', string='Carpeta Relacionada')
    group_by_product = fields.Boolean('Agrupar por Producto')
    advance_payment_method = fields.Selection(selection=[('all', 'Facturar todos los Servicios'), ('percentage', 'Facturar un tramo'), ('lines', 'Algún servicio de la carpeta')], string='¿Qué desea facturar?', required=True, readonly=False)
    tramo_a_facturar = fields.Selection([('national', 'Nacional'), ('internacional', 'Internacional')], string='Tramo a Facturar')
    qtty = fields.Float('Quantity', digits=(16, 2), required=True)
    product_id = fields.Many2one('product.product', 'Advance Product', domain=[('type', '=', 'service')],help="""Select a product of type service which is called 'Advance Product'.You may have to create it and set it as a default value on this field.""")
    amount = fields.Float(string='% A facturar', digits= dp.get_precision('Account'), help="The amount to be invoiced in advance.")
    amount_nat = fields.Float(string='% A facturar Nacional', digits=dp.get_precision('Account'))
    amount_inter = fields.Float(string='% A facturar Internacional', digits=dp.get_precision('Account'))
    operation_type = fields.Selection([('national', 'Nacional'), ('international', 'Internacional')],
                                      string='Tipo de Servicio')

    @api.multi
    def actualiza_estado_calenario(self, carpeta=None, estado=None):
        estados_obj = self.env['color.picker']
        calendario_obj = self.env['servicio.calendario']

        realizada_facturada = estados_obj.search([('name', '=', 'Carga Realizada y Facturada')])
        factura_rechazada = estados_obj.search([('name', '=', 'Factura Rechazada')])
        if carpeta:
            calendarios = calendario_obj.search([('rt_service_id', '=', carpeta.id)])
            for calendario in calendarios:
                if estado == 'Facturado':
                    calendario.color_pickier_id = realizada_facturada.id

    def generar_costos(self, carpetas=None, regimen=None):
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
        regimen = regimen_map[regimen]
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
    @api.onchange('advance_payment_method')
    def get_regimen_oncha(self):
        ps_obj = self.env['rt.service']
        for rec in self:
            context = rec._context
            active_is = context.get('active_ids', [])
            for ps in ps_obj.browse(active_is):
                rec.operation_type = ps.operation_type

    @api.onchange('tramo_a_facturar')
    def onchange_tramo_a_facturar(self):
        if self.tramo_a_facturar:
            if self.tramo_a_facturar == 'national':
                self.amount = 40
            if self.tramo_a_facturar == 'internacional':
                self.amount = 60

    def calcular_diario(self, partner_id):
        journal_obj = self.env['account.journal']
        if partner_id.vat_type == '2' and partner_id.country_id.code == 'UY':
            # e-Factura
            journal_id = journal_obj.search([('code', '=', 'EF')]).id
        if (partner_id.vat_type == '4' and partner_id.country_id.code != 'UY') or partner_id.vat_type == '3':
            # e-Ticket
            journal_id = journal_obj.search([('code', '=', 'ET')]).id

        return journal_id

    def cargar_campos_impresion(self, partner, invoice):
        invoice.print_output_reference = partner.print_output_reference
        invoice.print_origin_destiny_grouped = partner.print_origin_destiny_grouped
        invoice.print_cont_grouped = partner.print_cont_grouped
        invoice.print_product_grouped = partner.print_product_grouped
        invoice.print_invoice_load = partner.print_invoice_load
        invoice.print_invoice_product = partner.print_invoice_product
        invoice.print_date_start = partner.print_date_start
        invoice.print_ms_in_out = partner.print_ms_in_out
        invoice.print_mic = partner.print_mic
        invoice.print_crt = partner.print_crt
        invoice.print_delivery_order = partner.print_delivery_order
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

    def get_regimen(self, lineas_producto):
        regimen = []
        regimen_to_return = ''
        if lineas_producto:
            for line in lineas_producto:
                if line.rt_service_id:
                    regimen.append(line.rt_service_id.regimen)
                    regimen_to_return = line.rt_service_id.regimen
                if line.regimen_excepcion:
                    regimen.append(line.regimen_excepcion)

        if len(set(regimen)) > 1:
            raise Warning('El conjunto de regimenes no puede ser mayor a 1, revise')

        return regimen_to_return

    @api.multi
    def facturar_regimen_transito_in(self, product_lines):
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
        if not product_lines:
            raise Warning('No se encontraron servicios facturables. Revise si la carga tiene servicios asociados')
        if product_lines:
            for line in product_lines:
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
    def facturar_regimen_transito_out(self, product_lines):
        account_obj = self.env['account.account']
        tax_obj = self.env['account.tax']
        carpeta_obj = self.env['rt.service']
        operation_taxes = {
            'exento': False,
            'asimilado': tax_obj.search([('name', '=', 'IVA Venta asimilado a exportación')]),
            'gravado': tax_obj.search([('name', '=', 'IVA Ventas (22%)')])
        }
        lineas = []
        if product_lines:
            for line in product_lines:
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
    def facturar_regimen_expo(self, product_lines):
        account_obj = self.env['account.account']
        tax_obj = self.env['account.tax']
        carpeta_obj = self.env['rt.service']
        operation_taxes = {
            'exento': False,
            'asimilado': tax_obj.search([('name', '=', 'IVA Venta asimilado a exportación')]),
            'gravado': tax_obj.search([('name', '=', 'IVA Ventas (22%)')])
        }
        lineas = []
        if product_lines:
            for line in product_lines:
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
    def facturar_regimen_impo(self, product_lines):
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
        if product_lines:
            for line in product_lines:
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


    @api.multi
    def make_invoices(self):
        inv_obj = self.env['account.invoice']
        if not self._context.get('active_ids'):
            return {'type': 'ir.actions.act_window_close'}
        product_service = self.env['rt.service.productos'].search([('rt_service_id', '=', self.rt_service_id.id), ('is_invoiced', '=',True), ('invoiced', '=', False)])
        #product_service = self.env['rt.service.productos'].browse([3445,3446])
        # journal_id = self.env['account.invoice'].default_get(['journal_id'])['journal_id']
        # if not journal_id:
        #     raise UserError(_('Please define an accounting sales journal for this company.'))
        operation_taxes = {'exento': False, 'asimilado': False, 'gravado': False}
        name = ''
        tax_obj = self.env['account.tax']
        account_obj = self.env['account.account']

        lineas = []
        regimen = self.get_regimen(product_service)
        regimees_nacionales = ['transit_nat', 'impo_nat', 'expo_nat', 'interno_plaza_nat', 'interno_fiscal_nat']
        if regimen in regimees_nacionales:
            raise Warning('No puede facturar un regimen nacional en tramos')
        if regimen == 'transit_inter_out':
            lineas, carpeta = self.facturar_regimen_transito_out(product_service)
        if regimen == 'transit_inter_in':
            lineas, carpeta = self.facturar_regimen_transito_in(product_service)
        if regimen == 'expo_inter':
            lineas, carpeta = self.facturar_regimen_expo(product_service)
        if regimen == 'impo_inter':
            lineas, carpeta = self.facturar_regimen_impo(product_service)

        journal_id = self.calcular_diario(product_service[0].rt_service_id.partner_invoice_id)

        invoice = inv_obj.create({
            'name': name or '',
            'origin': product_service[0].name,
            'type': 'out_invoice',
            'account_id': product_service[0].rt_service_id.partner_invoice_id.property_account_receivable_id.id,
            'partner_id': product_service[0].rt_service_id.partner_invoice_id.id,
            'journal_id': journal_id,
            #'comment': line.rt_service_id.delivery_order,
            'currency_id': product_service[0].currency_id.id,
            'fiscal_position_id': product_service[0].partner_invoice_id.property_account_position_id.id,
            'company_id': product_service[0].rt_service_id.company_id.id,
            'user_id': product_service[0].rt_service_id.user_id and product_service[0].rt_service_id.user_id.id,
            'rt_service_product_id': product_service[0].id,
            'rt_service_id': product_service[0].rt_service_id.id,
            'invoice_line_ids': lineas
        })

        product_service[0].invoices_ids += invoice
        product_service[0].rt_service_id.invoices_ids += invoice
        product_service[0].rt_service_id.state = 'progress'

        partner = product_service[0].rt_service_id.partner_invoice_id
        self.cargar_campos_impresion(partner, invoice)
        self.actualiza_estado_calenario(carpeta=carpeta, estado='Facturado')
        self.generar_costos(carpetas=carpeta, regimen=regimen)


        if self._context['open_invoices']:
            return {
                'domain': [('id', 'in', invoice.ids)],
                'name': 'Invoices',
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'account.invoice',
                'view_id': False,
                'views': [(self.env.ref('account.invoice_tree').id, 'tree'), (self.env.ref('account.invoice_form').id, 'form')],
                'context': "{'type':'out_invoice'}",
                'type': 'ir.actions.act_window'
            }
        else:
            return {'type': 'ir.actions.act_window_close'}
