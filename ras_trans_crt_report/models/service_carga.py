# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details
from odoo import api, fields, models
import ipdb

class rt_service_carga(models.Model):
    _inherit = "rt.service.carga"

    def create_crt_report(self):
        data = {}
        report_action = self.env.ref('ras_trans_crt_report.crt_report').report_action([], data=data)
        return report_action
