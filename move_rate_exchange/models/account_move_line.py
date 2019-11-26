# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import RedirectWarning, UserError, ValidationError


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    check_rate = fields.Boolean(help=u'Habilita el ingreso de la cotización de la moneda extranjera', string='Tasa de cambio manual')
    rate_exchange = fields.Float(help='Cotización de la moneda extranjera', string='Tasa de cambio')

    @api.onchange('check_rate', 'rate_exchange', 'amount_currency', 'currency_id')
    def _onchange_rate_exchange(self):
        for record in self:
            if record.check_rate and record.rate_exchange > 0:
                if not record.currency_id:
                    raise ValidationError('Es necesario ingresar previamente la moneda.')
                amount = record.amount_currency * record.rate_exchange
                record.debit = amount > 0 and amount or 0.0
                record.credit = amount < 0 and -amount or 0.0

    @api.onchange('check_rate')
    def _uncheck_rate_exchange(self):
        for record in self:
            if not record.check_rate:
                record.rate_exchange = 0.0

    @api.onchange('amount_currency', 'currency_id', 'account_id', 'check_rate')
    def _onchange_amount_currency(self):
        '''Recompute the debit/credit based on amount_currency/currency_id and date.
        However, date is a related field on account.move. Then, this onchange will not be triggered
        by the form view by changing the date on the account.move.
        To fix this problem, see _onchange_date method on account.move.
        '''
        for line in self:
            company_currency_id = line.account_id.company_id.currency_id
            amount = line.amount_currency
            if line.currency_id and company_currency_id and line.currency_id != company_currency_id:
                # Se considera tasa de cambio manual
                if line.check_rate:
                    amount = line.amount_currency * line.rate_exchange
                else:
                    amount = line.currency_id._convert(amount, company_currency_id, line.company_id, line.date or fields.Date.today())
                line.debit = amount > 0 and amount or 0.0
                line.credit = amount < 0 and -amount or 0.0

    ####################################################
    # Misc / utility methods
    ####################################################

    @api.model
    def _compute_amount_fields(self, amount, src_currency, company_currency):
        """ Helper function to compute value for fields debit/credit/amount_currency based on an amount and the currencies given in parameter"""
        amount_currency = False
        currency_id = False
        date = self.env.context.get('date') or fields.Date.today()
        company = self.env.context.get('company_id')
        company = self.env['res.company'].browse(company) if company else self.env.user.company_id
        if src_currency and src_currency != company_currency:
            amount_currency = amount
            # Se considera tasa de cambio manual
            if self.check_rate:
                amount = self.amount_currency * self.rate_exchange
            else:
                amount = src_currency._convert(amount, company_currency, company, date)
            currency_id = src_currency.id
        debit = amount > 0 and amount or 0.0
        credit = amount < 0 and -amount or 0.0
        return debit, credit, amount_currency, currency_id
