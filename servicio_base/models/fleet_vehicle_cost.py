# -*- coding: utf-8 -*-
from odoo import fields, models, api,_
import ipdb
from odoo.exceptions import UserError, ValidationError

class FleetVehicleCost(models.Model):
    _inherit = 'fleet.vehicle.cost'
    _description = 'Cost related to a vehicle heredado para los costos'

    product_to_invoice = fields.Many2one(comodel_name='product.product', string='Producto Facturable')
    invoice_id = fields.Many2one(comodel_name='account.invoice', string='Factura Relacionada')
    inv_ref = fields.Char('Invoice Reference', size=64)
    vendor_id = fields.Many2one('res.partner', 'Vendor', domain="[('supplier','=',True)]")


class MakeInvoice(models.TransientModel):
    _name = 'fleet.vehicle.cost.make.invoice'
    _description = 'Create Mass Invoice (Fleet)'

    group = fields.Boolean('Group by partner invoice address')



    @api.multi
    def make_invoices(self):
        context = self._context.copy()
        fuel_ids = context.get('active_ids', [])
        inv_obj = self.env['account.invoice']
        if not self._context.get('active_ids'):
            return {'type': 'ir.actions.act_window_close'}

        cost_obj = self.env['fleet.vehicle.cost']
        fuel_ids = cost_obj.browse(fuel_ids)
        journal_id = self.env['account.journal'].search([('type', '=', 'purchase')], limit=1)
        tax_obj = self.env['account.tax']
        account_obj = self.env['account.account']

        lineas = []
        new_invoices = []
        line_dict = {}
        for line in fuel_ids:
            line_dict['name'] = line.product_to_invoice.name
            line_dict['account_id'] = line.product_to_invoice.property_account_expense_id.id
            line_dict['price_unit'] = line.amount
            line_dict['uom_id'] = line.product_to_invoice.uom_id.id
            line_dict['product_id'] = line.product_to_invoice.id
            line_dict['vehicle_id'] = line.vehicle_id.id
            line_dict['invoice_line_tax_ids'] = [(6, 0, [x.id for x in line.product_to_invoice.supplier_taxes_id])]
            lineas.append((0, 0, line_dict))

            invoice = inv_obj.create({
                'origin': line.name,
                'type': 'in_invoice',
                'account_id': line.vendor_id.property_account_payable_id.id,
                'partner_id': line.vendor_id.id,
                'journal_id': journal_id.id,
                'currency_id': journal_id.company_id.currency_id.id,
                'reference': line.inv_ref,
                #'fiscal_position_id': product_service.rt_service_id.partner_invoice_id.property_account_position_id.id,
                #'company_id': product_service.rt_service_id.company_id.id,
                #'user_id': product_service.rt_service_id.user_id and product_service.rt_service_id.user_id.id,
                'invoice_line_ids': lineas
            })

            #line.invoce_id = invoice.id
            line.write({'invoice_id': invoice.id})
            new_invoices.append(invoice.id)
            lineas = []
            line_dict = {}

        if context['open_invoices']:
            return {
                'domain': [('id', 'in', new_invoices)],
                'name': 'Invoices',
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'account.invoice',
                'view_id': False,
                'views': [(self.env.ref('account.invoice_supplier_tree').id, 'tree'),
                          (self.env.ref('account.invoice_supplier_form').id, 'form')],
                'context': "{'type':'in_invoice'}",
                'type': 'ir.actions.act_window'
            }
        else:
            return {'type': 'ir.actions.act_window_close'}