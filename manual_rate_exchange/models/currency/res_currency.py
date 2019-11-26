# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError
import logging



_logger = logging.getLogger(__name__)
import  ipdb

class ResCurrency(models.Model):
    _inherit = 'res.currency'



    def _get_rates(self, company, date):
        dolares = 2
        currency_rates = super(ResCurrency, self)._get_rates(company, date)
        if self.env.context.get('value_check_rate') and self.env.context.get('value_rate_exchange'):
            key = list(currency_rates.keys())
            # currency_rates[key[0]] = 1.0 / self.env.context.get('value_rate_exchange')
            for k in key:
                if k == dolares:
                    currency_rates[k] = self.env.context.get('value_rate_exchange')
        return currency_rates

