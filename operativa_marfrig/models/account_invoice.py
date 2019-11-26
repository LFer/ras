# -*- coding: utf-8 -*-
import logging

from odoo import api, exceptions, fields, models, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning
import ipdb

_logger = logging.getLogger(__name__)


class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    marfrig_operation_id = fields.Many2one('marfrig.service.base', string='Carpeta Marfrig Asociada')
    service_marfrig_ids = fields.One2many('marfrig.service.products', 'invoice_id', 'Services')


