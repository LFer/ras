# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError
import logging



_logger = logging.getLogger(__name__)



class AccountInvoiceC(models.Model):
    
    _inherit = 'account.invoice'


    check_rate = fields.Boolean(help='Cantidad de unidades de la moneda base con respecto a la moneda extranjera', string='Tasa de cambio manual')
    rate_exchange = fields.Float(help='Cantidad de unidades de la moneda base con respecto a la moneda extranjera', string='Tasa de cambio')

    @api.onchange('check_rate')
    def line_ids_invoice(self):
        if self.check_rate == False:
            for data in self.invoice_line_ids:
                data.local_currency_price = None
        else:
            for data in self.invoice_line_ids:
                data.local_currency_price = data.quantity*data.price_unit * self.rate_exchange

    @api.onchange('rate_exchange')
    def update_local_currency(self):
        for data in self.invoice_line_ids:
            data.local_currency_price=data.quantity*data.price_unit * self.rate_exchange













