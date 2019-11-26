# -*- coding: utf-8 -*-
import logging

from odoo import api, exceptions, fields, models, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning
import ipdb

_logger = logging.getLogger(__name__)

class Regimenes(models.Model):
    _name = "regimenes"

    name = fields.Char(string='Regimen')

class AccountTax(models.Model):
    _inherit = "account.tax"

    regimen_ids = fields.Many2many('regimenes', string='Regimenes')