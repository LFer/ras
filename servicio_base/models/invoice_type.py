# -*- coding: utf-8 -*-
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class rt_invoice_type(models.Model):
    _name = "rt.invoice.type"
    _description = "Tipo de Facturacion"

    name = fields.Char(string=u'Tipo de Facturación')


