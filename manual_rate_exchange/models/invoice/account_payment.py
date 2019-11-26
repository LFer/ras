from odoo import models, fields, api
from odoo.exceptions import ValidationError
import logging



_logger = logging.getLogger(__name__)


class AccountPayment(models.Model):
    _inherit = 'account.payment'


    check_rate = fields.Boolean(help='Cantidad de unidades de la moneda base con respecto a la moneda extranjera', string='Tasa de cambio manual')
    rate_exchange = fields.Float(help='Cantidad de unidades de la moneda base con respecto a la moneda extranjera', string='Tasa de cambio')
    local_currency_price = fields.Float(string='Precio en moneda local')

    @api.onchange('amount', 'rate_exchange')
    def currency_price(self):
        self.local_currency_price = self.rate_exchange * self.amount

