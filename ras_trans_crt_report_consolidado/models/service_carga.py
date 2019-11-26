# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details
from odoo import api, fields, models
import ipdb
from odoo.exceptions import UserError, RedirectWarning, Warning

class CargaCamion(models.Model):
    _inherit = "carga.camion"

    def create_crt_report(self):
        data = {}
        report_action = self.env.ref('ras_trans_crt_report_consolidado.crt_report').report_action([], data=data)
        return report_action

class CarpetaCamion(models.Model):
    _inherit = "carpeta.camion"

    def create_crt_report_paraguay(self):
        data = {}
        report_action = self.env.ref('ras_trans_crt_report_consolidado.paraguay').report_action([], data=data)

        return report_action

