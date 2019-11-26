# -*- coding: utf-8 -*-
import logging

from odoo import api, exceptions, fields, models, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning
import ipdb

_logger = logging.getLogger(__name__)


class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    deposito_operation_id = fields.Many2one('deposito.service.base', string='Carpeta Deposito Asociada')
    service_deposito_ids = fields.One2many('deposito.service.base', 'invoice_id', 'Services')

class AccountInvoiceLine(models.Model):
    _inherit = "account.invoice.line"

    product_deposito_srv_id = fields.Many2one('deposito.service.products', string='Servicio Deposito Asociado')
