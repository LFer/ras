# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
from odoo.osv import expression
import ipdb
from odoo.osv.expression import get_unaccent_wrapper
import re



class MarfrigResPartner(models.Model):
    _inherit = 'res.partner'

    es_marfrig = fields.Boolean('Es Marfrig?')