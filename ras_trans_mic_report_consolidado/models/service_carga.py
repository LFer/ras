# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details
from odoo import api, fields, models
import ipdb
from odoo.exceptions import UserError, RedirectWarning, Warning


class CarpetaCamion(models.Model):
    _inherit = "carpeta.camion"

    def create_mic_report(self):
        data = {}
        report_action = self.env.ref('ras_trans_mic_report_consolidado.mic_report').report_action([], data=data)
        for carga in self.cargas_ids:
            if not carga.crt_number:
                raise Warning('Es necesario tener el numero de CRT para genera el reporte MIC y no tiene Numero de CRT la Carga %s' % carga.name)

        return report_action
