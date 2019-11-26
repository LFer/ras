# -*- coding: utf-8 -*-
import logging

from odoo import api, fields, models

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    vehicle_id = fields.Many2one('fleet.vehicle', string='Matricula')