# -*- coding: utf-8 -*-
import logging

from odoo import api, exceptions, fields, models, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning
import ipdb

_logger = logging.getLogger(__name__)


class AccountInvoice(models.Model):
    _inherit = "account.invoice"



    @api.onchange('cash_rounding_id', 'invoice_line_ids', 'tax_line_ids')
    def _onchange_cash_rounding(self):
        # Drop previous cash rounding lines
        lines_to_remove = self.invoice_line_ids.filtered(lambda l: l.is_rounding_line)
        if lines_to_remove:
            self.invoice_line_ids -= lines_to_remove

        # Clear previous rounded amounts
        for tax_line in self.tax_line_ids:
            if tax_line.amount_rounding != 0.0:
                tax_line.amount_rounding = 0.0

        if self.cash_rounding_id and self.type in ('out_invoice', 'out_refund', 'in_invoice'):
            rounding_amount = self.cash_rounding_id.compute_difference(self.currency_id, self.amount_total)
            if not self.currency_id.is_zero(rounding_amount):
                if self.cash_rounding_id.strategy == 'biggest_tax':
                    # Search for the biggest tax line and add the rounding amount to it.
                    # If no tax found, an error will be raised by the _check_cash_rounding method.
                    if not self.tax_line_ids:
                        return
                    biggest_tax_line = None
                    for tax_line in self.tax_line_ids:
                        if not biggest_tax_line or tax_line.amount > biggest_tax_line.amount:
                            biggest_tax_line = tax_line
                    biggest_tax_line.amount_rounding += rounding_amount
                elif self.cash_rounding_id.strategy == 'add_invoice_line':
                    # Create a new invoice line to perform the rounding
                    rounding_line = self.env['account.invoice.line'].new({
                        'name': self.cash_rounding_id.name,
                        'invoice_id': self.id,
                        'account_id': self.cash_rounding_id.account_id.id,
                        'price_unit': rounding_amount,
                        'quantity': 1,
                        'is_rounding_line': True,
                        'sequence': 9999  # always last line
                    })

                    # To be able to call this onchange manually from the tests,
                    # ensure the inverse field is updated on account.invoice.
                    if not rounding_line in self.invoice_line_ids:
                        self.invoice_line_ids += rounding_line


    @api.multi
    def actualiza_estado_calendario(self, carpeta=None, estado=None):
        estados_obj = self.env['color.picker']
        calendario_obj = self.env['servicio.calendario']

        realizada_facturada = estados_obj.search([('name', '=', 'Carga Realizada y Facturada')])
        factura_rechazada = estados_obj.search([('name', '=', 'Factura Rechazada')])
        if carpeta:
            calendario = calendario_obj.search([('rt_service_id', '=', carpeta.id)])
            if calendario:
                if estado == 'Facturado':
                    calendario.color_pickier_id = realizada_facturada.id
                if estados_obj == 'Rechazado':
                    calendario.color_pickier_id = factura_rechazada.id

    @api.multi
    def update_suppliers(self, ps_ids, invoice):
        if invoice:
            for rec in invoice:
                rec.producto_ids += ps_ids
            for ps in ps_ids:
                if ps.rt_marfrig_product_id:
                    invoice.service_marfrig_ids += ps.rt_marfrig_product_id


    def delete_suppliers(self, ps_ids):
        self.write({'product_supplier_ids': [(3, ps_id) for ps_id in ps_ids]})

    @api.one
    @api.depends('product_supplier_ids.invoice_id')
    def _get_services(self):
        srv_ids = []
        for psrv in self.producto_ids:
            if psrv.rt_service_id and not psrv.rt_consol_product_id:
                if psrv.invoice_id and psrv.rt_service_product_id and psrv.rt_service_product_id.rt_service_id and psrv.rt_service_product_id.rt_service_id.id not in srv_ids:
                    srv_ids.append(psrv.rt_service_product_id.rt_service_id.id)
        if srv_ids:
            self.service_ids = [(5,)]
            self.service_ids = [(6, 0, srv_ids)]
        else:
            self.service_ids = [(5,)]

    def bind_service_product_supplier(self):
        if not isinstance(self._context, (dict,)):
            context = {}
        row = self
        if row.get_amount_available() <= 0:
            raise Warning('This Supplier Invoice not have available amount for add more Suppliers.')
        srv_prod_sup_obj = self.env['rt.service.product.supplier']
        srv_prod_sup_ids = srv_prod_sup_obj.search([
            '|',
            '|',
            '|',
            '|',
            '|',
            ('rt_service_product_id', '!=', False),
            ('rt_consol_product_id', '!=', False),
            ('rt_marfrig_product_id', '!=', False),
            ('rt_service_product_id.rt_service_id', '!=', False),
            ('rt_service_id', '!=', False),
            ('rt_deposito_product_id', '!=', False),
            ('amount', '>', 0),
            ('invoice_id', '=', False),
            ('supplier_id', '=', row.freighter_id.id)
        ])
        domain = [
            '|',
            '|',
            '|',
            '|',
            '|',
            ('rt_service_product_id', '!=', False),
            ('rt_consol_product_id', '!=', False),
            ('rt_marfrig_product_id', '!=', False),
            ('rt_service_product_id.rt_service_id', '!=', False),
            ('rt_service_id', '!=', False),
            ('rt_deposito_product_id', '!=', False),
            ('amount', '>', 0),
            ('invoice_id', '=', False),
            ('supplier_id', '=', row.freighter_id.id)
        ]
        if srv_prod_sup_ids:
            context = {}
            context['active_ids'] = srv_prod_sup_ids.ids
            context['search_default_filter_without_invoice'] = True
            context['search_default_supplier_id'] = row.freighter_id.id
            context['search_default_currency_id'] = row.currency_id.id
            context['tree_view_ref'] = 'ras_trans_supplier_invoice.rt_service_product_supplier_tree2'
            context['form_view_ref'] = 'ras_trans_supplier_invoice.rt_service_product_supplier_form2'
            context['close_form'] = True
            return {
                'name': _('Suppliers'),
                'view_type': 'form',
                'view_mode': 'tree',
                'res_model': 'rt.service.product.supplier',
                'view_id': False,
                'domain': domain,
                'context': context,
                'type': 'ir.actions.act_window',
            }
        else:
            raise Warning('Proveedores de Producto de Servicio no encontrado')

    @api.model
    def get_amount_available(self):
        _amount = self.amount_untaxed
        for line in self.producto_ids:
            _amount -= line.amount
        return _amount

    @api.model
    def get_invoice_name(self):
        return self.name_get()[0][1]

    rt_service_product_id = fields.Many2one('rt.service.productos', string='Servicio Asociado')
    rt_service_id = fields.Many2one('rt.service', string='Carpeta Asociada')
    service_ids = fields.Many2many('rt.service', 'rt_service_invoice_sup_rel', 'invoice_id', 'service_id', 'Services', compute="_get_services", copy=False)
    product_supplier_ids = fields.Many2many('rt.service.product.supplier', 'rt_service_supplier_invoice_rel', 'invoice_id', 'prod_sup_id', 'Service Product Suppliers', readonly=True, copy=False)
    producto_ids = fields.One2many('rt.service.product.supplier', 'invoice_id', string='Servicios')
    freighter_id = fields.Many2one(comodel_name='res.partner', string='Proveedor')

    @api.multi
    def name_get(self):
        TYPES = {
            'out_invoice': _('Factura'),
            'in_invoice': _('Factura Proveedor'),
            'out_refund': _('Nota de Crédito'),
            'in_refund': _('Nota de Crédito de Factura de Proveedor'),
        }
        result = []
        for inv in self:
            if inv.type == 'in_invoice':
                result.append((inv.id, "%s %s" % (inv.move_name or TYPES[inv.type], inv.partner_id.name or '')))
                result.append((inv.id, "%s %s" % (inv.move_name or TYPES[inv.type], inv.name or '')))
            result.append((inv.id, "%s %s" % (inv.move_name or TYPES[inv.type], inv.name or '')))
            # result.append((inv.id, "%s %s" % (inv.number or TYPES[inv.type], inv.name or '')))
        return result


    @api.multi
    def finalize_invoice_move_lines(self, move_lines):
        """ finalize_invoice_move_lines(move_lines) -> move_lines

            Hook method to be overridden in additional modules to verify and
            possibly alter the move lines to be created by an invoice, for
            special cases.
            :param move_lines: list of dictionaries with the account.move.lines (as for create())
            :return: the (possibly updated) final move_lines to create for this invoice
        """
        invoice_line_obj = self.env['account.invoice.line']
        for iml in move_lines:
            move_line = iml[2]
            invoice = invoice_line_obj.search([('invoice_id', '=', move_line['invoice_id'])])
            for inv in invoice:
                if inv.invoice_id.type == 'in_invoice':
                    move_line['vehicle_id'] = inv.vehicle_id.id
        return move_lines


    @api.multi
    def unlink(self):
        carpeta = False
        for invoice in self:

            if invoice.camion_id:
                for line in self.invoice_line_ids:
                    line.consolidado_service_product_id.invoiced_rejected = True
                    line.consolidado_service_product_id.invoiced = False
                    if line.tramo_facturado:
                        if line.tramo_facturado == 'national':
                            line.consolidado_service_product_id.tramo_nat = False
                        if line.tramo_facturado == 'international':
                            line.consolidado_service_product_id.tramo_inter = False
                self.camion_id.state = 'rejected'

            #Para servicio nacional / internacional
            for line in invoice.invoice_line_ids:
                if line.rt_service_product_id:
                    line.rt_service_product_id.invoiced = False
                    line.rt_service_product_id.invoiced_rejected = True
                    if line.tramo_facturado:
                        if line.tramo_facturado == 'national':
                            line.rt_service_product_id.tramo_nat = False
                        if line.tramo_facturado == 'international':
                                line.rt_service_product_id.tramo_inter = False
                if line.rt_service_product_ids:
                    for line_inv in line.rt_service_product_ids:
                        line_inv.invoiced = False
                        line_inv.invoiced_rejected = True
                        if line.tramo_facturado:
                            if line.tramo_facturado == 'national':
                                line_inv.tramo_nat = False
                            if line.tramo_facturado == 'international':
                                line_inv.tramo_inter = False

            if invoice.rt_service_id:
                carpeta = invoice.rt_service_id
                invoice.rt_service_id.state = 'invoice_rejected'

            #Para operativa de Deposito
            if invoice.deposito_operation_id:
                for depo in invoice.deposito_operation_id.deposito_srv_ids:
                    depo.invoiced = False
                    depo.invoiced_rejected = True

                invoice.deposito_operation_id.state = 'invoice_rejected'

        self.actualiza_estado_calendario(carpeta=carpeta, estado='Rechazado')

        return super(AccountInvoice, self).unlink()



class AccountInvoiceLine(models.Model):
    _inherit = "account.invoice.line"

    vehicle_id = fields.Many2one('fleet.vehicle', string='Matricula')
    tramo_facturado = fields.Selection([('national', 'Nacional'), ('international', 'Internacional')], string='Tramo Facturado')
    rt_service_product_id = fields.Many2one('rt.service.productos', string='Servicio Asociado')
    rt_service_product_ids = fields.One2many('rt.service.productos', 'invoice_line_id', string='Servicios Asociado')


class AccountInvoiceRefund(models.TransientModel):
    """Credit Notes"""

    _inherit = "account.invoice.refund"

    @api.multi
    def actualiza_estado_calendario(self, carpeta=None, estado=None):
        estados_obj = self.env['color.picker']
        calendario_obj = self.env['servicio.calendario']

        realizada_facturada = estados_obj.search([('name', '=', 'Carga Realizada y Facturada')])
        factura_rechazada = estados_obj.search([('name', '=', 'Factura Rechazada')])
        if carpeta:
            calendario = calendario_obj.search([('rt_service_id', '=', carpeta.id)])
            if calendario:
                if estado == 'Facturado':
                    calendario.color_pickier_id = realizada_facturada.id
                if estados_obj == 'Rechazado':
                    calendario.color_pickier_id = factura_rechazada.id
    @api.multi
    def invoice_refund(self):
        data_refund = self.read(['filter_refund'])[0]['filter_refund']
        context = dict(self._context or {})
        active_id = context.get('active_id', False)
        carpeta = False
        if active_id:
            inv = self.env['account.invoice'].browse(active_id)
            if inv:
                for invoice in inv:

                    # Estamos en una operativa de Consolidados
                    if invoice.camion_id:
                        for line in invoice.invoice_line_ids:
                            line.consolidado_service_product_id.invoiced_rejected = True
                            line.consolidado_service_product_id.invoiced = False
                            if line.tramo_facturado:
                                if line.tramo_facturado == 'national':
                                    line.consolidado_service_product_id.tramo_nat = False
                                if line.tramo_facturado == 'international':
                                    line.consolidado_service_product_id.tramo_inter = False
                        invoice.camion_id.state = 'rejected'

                    #Para servicio nacional / internacional
                    if invoice.rt_service_id:
                        for line in invoice.invoice_line_ids:
                            if line.rt_service_product_id:
                                line.rt_service_product_id.invoiced = False
                                line.rt_service_product_id.invoiced_rejected = True
                                if line.tramo_facturado:
                                    if line.tramo_facturado == 'national':
                                        line.rt_service_product_id.tramo_nat = False
                                    if line.tramo_facturado == 'international':
                                        line.rt_service_product_id.tramo_inter = False
                        if invoice.rt_service_id:
                            carpeta = invoice.rt_service_id
                            invoice.rt_service_id.state = 'invoice_rejected'

                    #Para operativa de Deposito
                    if invoice.deposito_operation_id:
                        for depo in invoice.deposito_operation_id.deposito_srv_ids:
                            depo.invoiced = False
                            depo.invoiced_rejected = True

                        invoice.deposito_operation_id.state = 'invoice_rejected'

                self.actualiza_estado_calendario(carpeta=carpeta, estado='Rechazado')
        return self.compute_refund(data_refund)