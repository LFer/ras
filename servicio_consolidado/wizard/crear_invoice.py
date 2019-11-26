# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _ , SUPERUSER_ID
from odoo.exceptions import UserError, ValidationError, Warning
import ipdb
from odoo.tools import float_is_zero, float_compare
from odoo.addons import decimal_precision as dp

class CrearFacturaWizard(models.Model):
    _name = 'crear.factura.wizard'
    _description = 'Asistente Crea Facturas Consolidados'

    name = fields.Char()
    group = fields.Boolean('Group by partner invoice address')
    camion_id = fields.Many2one('carpeta.camion', string='Camion')
    advance_payment_method = fields.Selection(
        selection=[('all', 'Facturar todos los Servicios'), ('percentage', 'Facturar un tramo'), ('lineas', 'Algún servicio del Consolidado')], string='¿Qué desea facturar?', required=True,
        readonly=False)
    tramo_a_facturar = fields.Selection([('national', 'Nacional'), ('internacional', 'Internacional')],
                                        string='Tramo a Facturar')
    amount = fields.Float(string='% A facturar', digits=dp.get_precision('Account'),
                          help="The amount to be invoiced in advance.")
    amount_nat = fields.Float(string='% A facturar Nacional', digits=dp.get_precision('Account'))
    amount_inter = fields.Float(string='% A facturar Internacional', digits=dp.get_precision('Account'))


    def check_if_all_is_invoiced(self):
        return


    @api.onchange('amount_inter', 'amount_nat')
    def onchange_amount_inter(self):
        for rec in self:
            if (rec.amount_nat and rec.amount_inter) != 0:
                if (rec.amount_inter + rec.amount_nat) != 100:
                    raise Warning('La suma de los % a facturar tiene que ser %100')
            if (rec.amount_nat or rec.amount_inter) > 100:
                raise Warning('No puede ingresar un número tan grande')

    def cargar_campos_impresion(self, partner, invoice):
        invoice.print_output_reference = partner.print_output_reference
        invoice.print_origin_destiny_grouped = partner.print_origin_destiny_grouped
        invoice.print_cont_grouped = partner.print_cont_grouped
        invoice.print_invoice_load = partner.print_invoice_load
        invoice.print_invoice_product = partner.print_invoice_product
        invoice.print_date_start = partner.print_date_start
        invoice.print_ms_in_out = partner.print_ms_in_out
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

    @api.multi
    def show_service_lines(self):
        # self = self.sudo(user=SUPERUSER_ID)
        context = self._context.copy()
        srv_ids = self._context.get('active_ids')
        act_window = self.sudo().env['ir.actions.act_window']
        wizard = self
        # open the list view of service product to invoice
        res = act_window.for_xml_id('servicio_consolidado', 'action_consolidado_servicio_tree')
        # context

        res['context'] = {
            'search_default_uninvoiced': 1,
        }
        products_obj = self.sudo().env['producto.servicio.camion']
        ids_guardadas = []
        camion = self.env[self._context.get('active_model')].browse(self._context.get('active_ids'))
        if camion.productos_servicios_camion_ids:
            ids_guardadas = camion.productos_servicios_camion_ids.ids
        for prod in camion.cargas_ids:
            for cg in prod.producto_servicio_carga_ids:
                ids_guardadas.append(cg.id)

        # domain
        if srv_ids:
            if not res.get('domain', False) or not isinstance(res.get('domain', False), (list,)):
                res['domain'] = []
            # res['domain'].append(('camion_id', 'in', srv_ids))
            res['domain'].append(('id', 'in', ids_guardadas))
            res['domain'].append(('invoiced', '=', False))
            res['domain'].append(('is_invoiced', '=', True))
        return res

    def get_regimen(self, lineas_producto):
        regimen = []
        regimen_to_return = ''
        if lineas_producto:
            for line in lineas_producto:
                if line.camion_id:
                    regimen.append(line.camion_id.regimen)
                    regimen_to_return = line.camion_id.regimen

                if line.rt_carga_id:
                    regimen.append(line.rt_carga_id.regimen)
                    regimen_to_return = line.rt_carga_id.regimen

        if len(set(regimen)) > 1:
            raise Warning('El conjunto de regimenes no puede ser mayor a 1, revise')

        return regimen_to_return

    @api.multi
    def facturar_regimen_transito_out(self, product_lines):
        account_obj = self.env['account.account']
        tax_obj = self.env['account.tax']
        camion_obj = self.env['carpeta.camion']
        operation_taxes = {
            'exento': False,
            'asimilado': tax_obj.search([('name', '=', 'IVA Venta asimilado a exportación')]),
            'gravado': tax_obj.search([('name', '=', 'IVA Ventas (22%)')])
        }
        lineas = []
        if product_lines:
            for line in product_lines:
                id_camion = line.camion_id.id
                id_carga_camion = line.rt_carga_id.camion_id.id
                camion = camion_obj.browse(id_camion if id_camion else id_carga_camion)
                account = account_obj.search([('code', '=', '41031005')])
                account_consol = account_obj.search([('code', '=', '41031009')])
                taxes = operation_taxes['asimilado']
                line_dict_inter = {}
                line_dict_nat = {}
                line_dict = {}
                if line.product_id.name == 'Flete':
                    #TRAMO INTERNACIONAL
                    line_dict_inter['name'] = line.name or ''#'TRAMO INTERNACIONAL'
                    line_dict_inter['account_id'] = account.id
                    line_dict_inter['price_unit'] = line.importe * self.amount_inter / 100
                    line_dict_inter['uom_id'] = line.product_id.uom_id.id
                    line_dict_inter['product_id'] = line.product_id.id
                    line_dict_inter['consolidado_service_product_id'] = line.id
                    line_dict_inter['invoice_line_tax_ids'] = [(6, 0, taxes.ids)]
                    lineas.append((0, 0, line_dict_inter))


                    #TRAMO NACIONAL
                    line_dict_nat['name'] = line.name or '' #'TRAMO NACIONAL'
                    line_dict_nat['account_id'] = account.id
                    line_dict_nat['price_unit'] = line.importe * self.amount_nat / 100
                    line_dict_nat['uom_id'] = line.product_id.uom_id.id
                    line_dict_nat['product_id'] = line.product_id.id
                    line_dict_nat['consolidado_service_product_id'] = line.id
                    line_dict_nat['invoice_line_tax_ids'] = [(6, 0, taxes.ids)]
                    lineas.append((0, 0, line_dict_nat))
                else:
                    line_dict['name'] = line.name or ''
                    line_dict['account_id'] = account_consol.id
                    line_dict['price_unit'] = line.importe
                    line_dict['uom_id'] = line.product_id.uom_id.id
                    line_dict['product_id'] = line.product_id.id
                    line_dict['consolidado_service_product_id'] = line.id
                    line_dict['invoice_line_tax_ids'] = [(6, 0, taxes.ids)]
                    lineas.append((0, 0, line_dict))
                # Facturado
                line.invoiced = True
                line.invoiced_rejected = False

        return lineas, camion

    @api.multi
    def facturar_regimen_transito_in(self, product_lines):
        account_obj = self.env['account.account']
        tax_obj = self.env['account.tax']
        camion_obj = self.env['carpeta.camion']
        operation_taxes = {
            'exento': False,
            'asimilado': tax_obj.search([('name', '=', 'IVA Venta asimilado a exportación')]),
            'gravado': tax_obj.search([('name', '=', 'IVA Ventas (22%)')])
        }
        lineas = []
        if product_lines:
            for line in product_lines:
                id_camion = line.camion_id.id
                id_carga_camion = line.rt_carga_id.camion_id.id
                camion = camion_obj.browse(id_camion if id_camion else id_carga_camion)
                account = account_obj.search([('code', '=', '41031005')])
                account_consol = account_obj.search([('code', '=', '41031009')])
                taxes = operation_taxes['asimilado']
                line_dict_inter = {}
                line_dict_nat = {}
                line_dict = {}
                if line.product_id.name == 'Flete':
                    # TRAMO INTERNACIONAL
                    line_dict_inter['name'] = line.name or ''#'TRAMO INTERNACIONAL'
                    line_dict_inter['account_id'] = account.id
                    line_dict_inter['price_unit'] = line.importe * self.amount_inter / 100
                    line_dict_inter['uom_id'] = line.product_id.uom_id.id
                    line_dict_inter['product_id'] = line.product_id.id
                    line_dict_inter['consolidado_service_product_id'] = line.id
                    line_dict_inter['invoice_line_tax_ids'] = [(6, 0, taxes.ids)]
                    lineas.append((0, 0, line_dict_inter))

                    # TRAMO NACIONAL
                    line_dict_nat['name'] = line.name or '' #'TRAMO NACIONAL'
                    line_dict_nat['account_id'] = account.id
                    line_dict_nat['price_unit'] = line.importe * self.amount_nat / 100
                    line_dict_nat['uom_id'] = line.product_id.uom_id.id
                    line_dict_nat['product_id'] = line.product_id.id
                    line_dict_nat['consolidado_service_product_id'] = line.id
                    line_dict_nat['invoice_line_tax_ids'] = [(6, 0, taxes.ids)]
                    lineas.append((0, 0, line_dict_nat))
                else:
                    line_dict['name'] = line.name or ''
                    line_dict['account_id'] = account_consol.id
                    line_dict['price_unit'] = line.importe
                    line_dict['uom_id'] = line.product_id.uom_id.id
                    line_dict['product_id'] = line.product_id.id
                    line_dict['consolidado_service_product_id'] = line.id
                    line_dict['invoice_line_tax_ids'] = [(6, 0, taxes.ids)]
                    lineas.append((0, 0, line_dict))
                # Facturado
                line.invoiced = True
                line.invoiced_rejected = False

        return lineas, camion

    @api.multi
    def facturar_regimen_expo(self, product_lines):
        account_obj = self.env['account.account']
        tax_obj = self.env['account.tax']
        camion_obj = self.env['carpeta.camion']
        operation_taxes = {
            'exento': False,
            'asimilado': tax_obj.search([('name', '=', 'IVA Venta asimilado a exportación')]),
            'gravado': tax_obj.search([('name', '=', 'IVA Ventas (22%)')])
        }
        lineas = []
        if product_lines:
            for line in product_lines:
                id_camion = line.camion_id.id
                id_carga_camion = line.rt_carga_id.camion_id.id
                camion = camion_obj.browse(id_camion if id_camion else id_carga_camion)
                account = account_obj.search([('code', '=', '41031005')])
                account_consol = account_obj.search([('code', '=', '41031009')])
                taxes = operation_taxes['asimilado']
                line_dict_inter = {}
                line_dict_nat = {}
                line_dict = {}
                if line.product_id.name == 'Flete':
                    # TRAMO INTERNACIONAL
                    line_dict_inter['name'] = line.name or ''#'TRAMO INTERNACIONAL'
                    line_dict_inter['account_id'] = account.id
                    line_dict_inter['price_unit'] = line.importe * self.amount_inter / 100
                    line_dict_inter['uom_id'] = line.product_id.uom_id.id
                    line_dict_inter['product_id'] = line.product_id.id
                    line_dict_inter['consolidado_service_product_id'] = line.id
                    line_dict_inter['invoice_line_tax_ids'] = [(6, 0, taxes.ids)]
                    lineas.append((0, 0, line_dict_inter))

                    # TRAMO NACIONAL
                    line_dict_nat['name'] = line.name or '' #'TRAMO NACIONAL'
                    line_dict_nat['account_id'] = account.id
                    line_dict_nat['price_unit'] = line.importe * self.amount_nat / 100
                    line_dict_nat['uom_id'] = line.product_id.uom_id.id
                    line_dict_nat['product_id'] = line.product_id.id
                    line_dict_nat['consolidado_service_product_id'] = line.id
                    line_dict_nat['invoice_line_tax_ids'] = [(6, 0, taxes.ids)]
                    lineas.append((0, 0, line_dict_nat))
                else:
                    line_dict['name'] = line.name or ''
                    line_dict['account_id'] = account_consol.id
                    line_dict['price_unit'] = line.importe
                    line_dict['uom_id'] = line.product_id.uom_id.id
                    line_dict['product_id'] = line.product_id.id
                    line_dict['consolidado_service_product_id'] = line.id
                    line_dict['invoice_line_tax_ids'] = [(6, 0, taxes.ids)]
                    lineas.append((0, 0, line_dict))
                # Facturado
                line.invoiced = True
                line.invoiced_rejected = False

        return lineas, camion

    @api.multi
    def facturar_regimen_impo(self, product_lines):
        if self.advance_payment_method == 'all':
            raise Warning('No se puede facturar entera una IMPO')
        account_obj = self.env['account.account']
        tax_obj = self.env['account.tax']
        camion_obj = self.env['carpeta.camion']
        operation_taxes = {
            'exento': False,
            'asimilado': tax_obj.search([('name', '=', 'IVA Venta asimilado a exportación')]),
            'gravado': tax_obj.search([('name', '=', 'IVA Ventas (22%)')])
        }

        lineas = []
        por_tramos = 'percentage'
        todos_los_servicios = 'all'

        if product_lines:
            for line in product_lines:
                id_camion = line.camion_id.id
                id_carga_camion = line.rt_carga_id.camion_id.id
                camion = camion_obj.browse(id_camion if id_camion else id_carga_camion)
                account = account_obj.search([('code', '=', '41031005')])
                account_consol = account_obj.search([('code', '=', '41031009')])
                taxes = operation_taxes['asimilado']
                line_dict = {}
                if self.advance_payment_method == por_tramos:
                    # TRAMO INTERNACIONAL
                    if self.tramo_a_facturar == 'internacional':
                        if line.tramo_inter:
                            raise Warning('Ya se facturo el tramo internacional')
                        else:
                            taxes = operation_taxes['asimilado']
                            account = account_obj.search([('code', '=', '41031005')])
                            if line.product_id.name == 'Flete':
                                line_dict['name'] = line.name or ''#'TRAMO INTERNACIONAL'
                                line_dict['account_id'] = account.id
                                line_dict['price_unit'] = line.importe * self.amount / 100
                                line_dict['uom_id'] = line.product_id.uom_id.id
                                line_dict['tramo_facturado'] = 'international'
                                line_dict['product_id'] = line.product_id.id
                                line_dict['consolidado_service_product_id'] = line.id
                                line_dict['invoice_line_tax_ids'] = [(6, 0, taxes.ids)]
                                lineas.append((0, 0, line_dict))
                                line.tramo_inter = True
                                if line.tramo_inter and line.tramo_nat:
                                    # Facturado
                                    line.invoiced = True
                                    line.invoiced_rejected = False
                            else:
                                line_dict['name'] = line.name or ''
                                line_dict['account_id'] = account_consol.id
                                line_dict['price_unit'] = line.importe
                                line_dict['uom_id'] = line.product_id.uom_id.id
                                line_dict['product_id'] = line.product_id.id
                                line_dict['consolidado_service_product_id'] = line.id
                                line_dict['invoice_line_tax_ids'] = [(6, 0, taxes.ids)]
                                lineas.append((0, 0, line_dict))
                                # Facturado
                                line.invoiced = True
                                line.invoiced_rejected = False

                    # TRAMO NACIONAL
                    if self.tramo_a_facturar == 'national':
                        if line.tramo_nat:
                            raise Warning('Ya se facturo el tramo nacional')
                        else:
                            taxes = operation_taxes['gravado']
                            account = account_obj.search([('code', '=', '41031005')])
                            if line.product_id.name == 'Flete':
                                line_dict['name'] = line.name or '' #'TRAMO NACIONAL'
                                line_dict['account_id'] = account.id
                                line_dict['price_unit'] = line.importe * self.amount / 100
                                line_dict['uom_id'] = line.product_id.uom_id.id
                                line_dict['tramo_facturado'] = 'national'
                                line_dict['product_id'] = line.product_id.id
                                line_dict['consolidado_service_product_id'] = line.id
                                line_dict['invoice_line_tax_ids'] = [(6, 0, taxes.ids)]
                                lineas.append((0, 0, line_dict))
                                line.tramo_nat = True
                                if line.tramo_nat and line.tramo_inter:
                                    # Facturado
                                    line.invoiced = True
                                    line.invoiced_rejected = False
                            else:
                                line_dict['name'] = line.name or ''
                                line_dict['account_id'] = account.id
                                line_dict['price_unit'] = line.importe
                                line_dict['uom_id'] = line.product_id.uom_id.id
                                line_dict['product_id'] = line.product_id.id
                                line_dict['consolidado_service_product_id'] = line.id
                                line_dict['invoice_line_tax_ids'] = [(6, 0, taxes.ids)]
                                lineas.append((0, 0, line_dict))
                                # Facturado
                                line.invoiced = True
                                line.invoiced_rejected = False

                if self.advance_payment_method == todos_los_servicios:
                    #Me ahora, me fijo si el producto es de terceros y si tiene el costo generado.
                    #De no tenerlo... ¿Tiro error o lo cargo automatico?
                    #Voy a intentar cargarlo automatico....
                    line_dict['name'] = line.name or ''
                    line_dict['account_id'] = account.id
                    line_dict['price_unit'] = line.importe
                    line_dict['uom_id'] = line.product_id.uom_id.id
                    line_dict['product_id'] = line.product_id.id
                    line_dict['consolidado_service_product_id'] = line.id
                    line_dict['invoice_line_tax_ids'] = [(6, 0, taxes.ids)]
                    lineas.append((0, 0, line_dict))
                    # Facturado
                    line.invoiced = True
                    line.invoiced_rejected = False

        return lineas, camion

    def checkear_costos(self, productos=None):
        if not productos:
             return
        if productos:
            for prod in productos:
                if prod.product_type == 'terceros':
                    if prod.supplier_id and prod.valor_compra_currency_id and prod.valor_compra:
                        if not prod.supplier_ids:
                            prod.add_supplier_to_product_line()
                            print('se añadio costo usando la funcion checkear_costos')
                        if prod.supplier_ids:
                            for sup in prod.supplier_ids:
                                if not sup.consol_id or not sup.rt_consol_product_id or not sup.output_reference or not sup.product_id:
                                    raise Warning('No se cargo bien alguno de los campos de la linea de costo \n Produdto: %s, Referencia: %s Carga: %s' % (sup.rt_consol_product_id.name, sup.rt_consol_product_id.product_id.name, sup.rt_consol_product_id.rt_carga_id.name if sup.rt_consol_product_id.name else 'N/A'))
                                else:
                                    continue



    @api.multi
    def create_invoices(self):
        context = self._context.copy()
        inv_obj = self.env['account.invoice']
        account_obj = self.env['account.account']
        camion_obj = self.env['carpeta.camion']
        account = False
        if not self._context.get('active_ids'):
            return {'type': 'ir.actions.act_window_close'}
        products_obj = self.env['producto.servicio.camion']
        ids_guardadas = []
        for srv in self.camion_id.productos_servicios_camion_ids:
            if srv.is_invoiced and not srv.invoiced:
                ids_guardadas.append(srv.id)

        for prod in self.camion_id.cargas_ids:
            for cg in prod.producto_servicio_carga_ids:
                if cg.is_invoiced and not cg.invoiced:
                    ids_guardadas.append(cg.id)

        product_service = products_obj.browse(ids_guardadas)
        regimen = self.get_regimen(product_service)
        journal_id = self.env['account.invoice'].default_get(['journal_id'])['journal_id']
        tax_obj = self.env['account.tax']
        if not journal_id:
            raise UserError(_('Please define an accounting sales journal for this company.'))
        operation_taxes = {
            'exento': False,
            'asimilado': tax_obj.search([('name', '=', 'IVA Venta asimilado a exportación')]),
            'gravado': tax_obj.search([('name', '=', 'IVA Ventas (22%)')])
        }
        lineas = []
        self.checkear_costos(productos=product_service)
        if regimen == 'transit_inter_out':
            lineas, camion = self.facturar_regimen_transito_out(product_service)
        if regimen == 'transit_inter_in':
            lineas, camion = self.facturar_regimen_transito_in(product_service)
        if regimen == 'expo_inter':
            lineas, camion = self.facturar_regimen_expo(product_service)
        if regimen == 'impo_inter':
            lineas, camion = self.facturar_regimen_impo(product_service)

        if not lineas:
            raise Warning('No se encontraron lineas')

        journal_id = self.calcular_diario(camion.partner_invoice_id)

        invoice = inv_obj.create({
            'name': camion.name or '',
            'origin': camion.name,
            'type': 'out_invoice',
            'account_id': camion.partner_invoice_id.property_account_receivable_id.id,
            'partner_id': camion.partner_invoice_id.id,
            'journal_id': journal_id,
            'currency_id': camion.currency_id.id,
            'fiscal_position_id': camion.partner_invoice_id.property_account_position_id.id,
            'company_id': camion.company_id.id,
            'user_id': camion.user_id.user_id.id,
            'camion_id': camion.id,
            'invoice_line_ids': lineas
        })

        for prod in product_service:
            invoice.consolidado_service_product_id = prod.id

        camion.state = 'inprocess'
        camion.invoices_ids = invoice

        partner = camion.partner_invoice_id
        self.cargar_campos_impresion(partner, invoice)

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