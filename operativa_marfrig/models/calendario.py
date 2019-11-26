# -*- coding: utf-8 -*-
import logging

from odoo import api, fields, models
import ipdb

_logger = logging.getLogger(__name__)



class ServicioCalendario(models.Model):
    _inherit = "servicio.calendario"


    marfrig_id = fields.Many2one(comodel_name='marfrig.service.base', string='Carpeta Marfrig Relacionada')

    @api.onchange('partner_id')
    def _onchange_marfrig_id(self):
        domain = {}
        res = {}
        if self.partner_id:
            self.marfrig_id = False
            domain = {'marfrig_id': [('partner_invoice_id', 'in', self.partner_id.ids)]}
        else:
            domain = {'marfrig_id': [('id', 'in', False)]}
        if domain:
            res['domain'] = domain
        return res

