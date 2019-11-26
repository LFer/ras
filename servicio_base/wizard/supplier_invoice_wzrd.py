# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
import ipdb
import functools
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning

class rt_supplier_invoice_wzd(models.TransientModel):
    _name = "rt.supplier.invoice.wzd"
    _description = "Make Supplier Invoice"

    @api.multi
    def bind_supplier_invoice_to_folder(self, product, invoice):
        for service in product:
            #Operativa nacional / Internacional
            if service.rt_service_id:
                service.rt_service_id.suppliers_invoices_ids += invoice
            #Operativa Consolidados
            if service.rt_consol_product_id:
                if service.rt_consol_product_id.camion_id.id:
                    service.rt_consol_product_id.camion_id.suppliers_invoices_ids += invoice
                elif service.rt_consol_product_id.rt_carga_id.id:
                    service.rt_consol_product_id.rt_carga_id.camion_id.suppliers_invoices_ids += invoice

            #Operativa Marfrig
            if service.rt_marfrig_product_id:
                service.rt_marfrig_product_id.mrf_srv_id.suppliers_invoices_ids += invoice

            # Operativa Deposito
            if service.rt_deposito_product_id:
                if service.rt_deposito_product_id.deposito_srv_id:
                    service.rt_deposito_product_id.deposito_srv_id.suppliers_invoices_ids  += invoice
                # service.rt_deposito_product_id.suppliers_invoices_ids += invoice


    def cmp_to_key(mycmp):
        'Convert a cmp= function into a key= function'

        class K:
            def __init__(self, obj, *args):
                self.obj = obj

            def __lt__(self, other):
                return mycmp(self.obj, other.obj) < 0

            def __gt__(self, other):
                return mycmp(self.obj, other.obj) > 0

            def __eq__(self, other):
                return mycmp(self.obj, other.obj) == 0

            def __le__(self, other):
                return mycmp(self.obj, other.obj) <= 0

            def __ge__(self, other):
                return mycmp(self.obj, other.obj) >= 0

            def __ne__(self, other):
                return mycmp(self.obj, other.obj) != 0

        return K

    def add_invoices(self):
        context = self._context
        context = context.copy()
        row = self
        if row.product_supplier_ids:
            _amount = row.amount_available
            srv_prod_sup_obj = self.env['rt.service.product.supplier']
            ps_ids = []
            ps_id_obj = []

            def _sort_cmp(x, y):
                if x.amount < y.amount:
                    return -1
                if x.amount == y.amount:
                    return 0
                return 1

            for ps in sorted(row.product_supplier_ids, key=functools.cmp_to_key(_sort_cmp)):
                if _amount <= 0:
                    raise Warning('Error' + '\n' + 'La factura %s no tiene importe suficiente para adicionar los proveedores seleccionados.' % (row.invoice_id.with_context(change_supplier_invoice_number=True).get_invoice_name()))
                if ps.amount < _amount:
                    _amount -= ps.amount
                else:
                    _rest = ps.amount - _amount
                    if _rest > 0:
                        ps.write({'amount': _amount})
                        srv_prod_sup_obj.browse(ps.id).copy(default={'amount': _rest, 'invoice_id': False, 'supplier_invoice_number': False})
                        _amount = 0
                ps_ids.append(ps.id)
                ps_id_obj.append(ps)
            if ps_ids:
                #srv_prod_sup_obj.write({'invoice_id': row.invoice_id.id})
                srv_prod_sup_obj.write({'invoice_id': row.invoice_id.id})


                self.env['account.invoice'].update_suppliers(srv_prod_sup_obj.browse(ps_ids), self.invoice_id)
                self.bind_supplier_invoice_to_folder(srv_prod_sup_obj.browse(ps_ids), self.invoice_id)

            context['active_ids'] = list(set(context['active_ids']) - set(ps_ids))
            if len(context.get('active_ids', [])) <= 1:
                return {'type': 'ir.actions.act_window_close'}
            return {
                'name': _('Add Supplier Invoice'),
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'rt.supplier.invoice.wzd',
                'view_id': False,
                'context': context,
                'type': 'ir.actions.act_window',
                'target': 'new',
                # 'res_id': row.id
            }

    @api.one
    @api.depends('invoice_id')
    def _get_number(self):
        if self.invoice_id:
            self.number = self.invoice_id.number
            self.amount_untaxed = self.invoice_id.amount_untaxed
            self.amount_available = self.invoice_id.get_amount_available()
        else:
            self.number = False
            self.amount_untaxed = False
            self.amount_available = False

    @api.onchange('partner_id')
    def _onchange_partner(self):
        if self.partner_id:
            ps_obj = self.env['rt.service.product.supplier']
            ps_ids = []
            for ps in ps_obj.browse(self.env.context['active_ids']):
                if ps.supplier_id.id == self.partner_id.id and ps.id not in ps_ids and ps.amount > 0 and not ps.invoice_id:
                    ps_ids.append(ps.id)
            if ps_ids:
                self.product_supplier_ids = [(6, 0, ps_ids)]
            else:
                self.product_supplier_ids = [(5,)]
            if self.invoice_id and (
                    not self.invoice_id.freighter_id or self.invoice_id.freighter_id.id != self.partner_id.id):
                self.invoice_id = False
            aci_ids = []
            domain = [('freighter_id', '=', self.partner_id.id), ('type', '=', 'in_invoice'),
                      ('state', 'in', ['open', 'paid', 'draft'])]
            for aci_row in self.env['account.invoice'].search(domain):
                if aci_row.get_amount_available() > 0:
                    aci_ids.append(aci_row.id)
            domain.append(('id', 'in', aci_ids))
            return {
                'domain': {'invoice_id': domain}
            }
        else:
            self.product_supplier_ids = [(5,)]
            self.invoice_id = False

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        _r = super(rt_supplier_invoice_wzd, self).fields_view_get(view_id=view_id, view_type='form', toolbar=toolbar, submenu=submenu)
        ps_obj = self.env['rt.service.product.supplier']
        acc_inv_obj = self.env['account.invoice']
        partner_ids = []
        context = self._context
        active_is = context.get('active_ids', [])
        for ps in ps_obj.browse(active_is):
            acc_inv_ids = []
            domain = [('freighter_id', '=', ps.supplier_id.id), ('type', '=', 'in_invoice'),
                      ('state', 'in', ['open', 'paid', 'draft'])]
            _ids = acc_inv_obj.search(domain)
            for aci_row in acc_inv_obj.browse(_ids.ids):
                if aci_row.get_amount_available() > 0:
                    partner_ids.append(ps.supplier_id.id)
            _r['fields']['partner_id']['domain'] = [('is_company', '=', True), ('supplier', '=', True), ('id', 'in', partner_ids)]

        return _r




    @api.model
    def default_get(self, fields):
        _r = super(rt_supplier_invoice_wzd, self).default_get(fields)
        ps_obj = self.env['rt.service.product.supplier']
        partner_ids = []
        context = self._context
        active_is = context.get('active_ids', [])

        for ps in ps_obj.browse(active_is):
            partner_ids.append(ps.supplier_id.id)

        if partner_ids and len(partner_ids) == 1:
            _r['partner_id'] = partner_ids[0]
            acc_inv_obj = self.env['account.invoice']
            acc_inv_ids = []
            domain = [('freighter_id', '=', partner_ids[0]), ('type', '=', 'in_invoice'),('state', 'in', ['open', 'paid', 'draft'])]
            _ids = acc_inv_obj.search(domain)
            for aci_row in acc_inv_obj.browse(_ids.ids):
                if aci_row.get_amount_available() > 0:
                    acc_inv_ids.append(aci_row.id)

            domain.append(('id', 'in', acc_inv_ids))

            acc_inv_ids = acc_inv_obj.search(domain)

            if acc_inv_ids and len(acc_inv_ids) == 1:
                _r['invoice_id'] = acc_inv_ids.id
        return _r

    partner_id = fields.Many2one('res.partner', 'Supplier', required=True, domain=[('is_company', '=', True), ('supplier', '=', True)])
    invoice_id = fields.Many2one('account.invoice', 'Invoice', required=True, domain=[('type', '=', 'in_invoice'), ('state', 'in', ['open', 'paid', 'draft'])])
    number = fields.Char('Invoice Number', compute='_get_number', readonly=True)
    amount_untaxed = fields.Float('Subtotal', compute='_get_number', readonly=True)
    amount_available = fields.Float('Subtotal Available', compute='_get_number', readonly=True)
    product_supplier_ids = fields.Many2many('rt.service.product.supplier', 'rt_service_supplier_invoice_rel_wzd', 'invoice_wzd_id', 'prod_sup_id', 'Service Product Suppliers', copy=False)
