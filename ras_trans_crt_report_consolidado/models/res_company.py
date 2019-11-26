# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details
from odoo import api, fields, models
import ipdb


class Company(models.Model):
    _inherit = "res.company"

    logo_crt = fields.Binary(string="Logo CRT", readonly=False)
    sello_empresa = fields.Binary(string="Sello", readonly=False)
    mic_logo = fields.Binary(string="Logo MIC")