from odoo import models, fields, api
from odoo.exceptions import ValidationError
import logging



_logger = logging.getLogger(__name__)


class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    local_currency_price = fields.Float(string='Precio en moneda local')
    rate_exchange = fields.Float(related='invoice_id.rate_exchange')
    currency_id = fields.Many2one('res.currency', related='invoice_id.currency_id')


    @api.onchange('rate_exchange','price_unit','quantity')
    def account_invoice_line(self):
        if self.invoice_id.check_rate and self.invoice_id.rate_exchange:
            self.local_currency_price = self.quantity*self.price_unit*self.invoice_id.rate_exchange



