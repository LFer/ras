# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import os
from io import StringIO
from odoo.modules import get_module_path


class RtServiceCrtConsolWzd(models.TransientModel):
    """
        Wizard to create a CRT Consolidated report
    """
    _name = "rt.service.crt.consol.wzd"
    _description = 'Consolidado Wizard'

    xls_name = fields.Char('File Name', size=128, copy=False)
    xls_file = fields.Binary('XLS File', copy=False)

    @api.multi
    def create_crt_report(self):
        self.ensure_one()

        # The report is emmitted only when active_ids are recieved from context
        active_ids = self.env.context.get('active_ids', False)
        if active_ids and isinstance(active_ids, (list,)):
            srv_obj = self.env['rt.service']

            # Reset wizard fields
            if self.xls_file or self.xls_name:
                self.write({'xls_file': False, 'xls_name': False})

            # Initialize workbook from template
            wb = srv_obj.init_workbook(filepath=os.path.join(get_module_path('ras_trans_crt_report'), 'xlsx_tpl', 'CRT.xlsx'))
            if not wb._sheets:
                return

            # Extract Service Products from services with id in active_ids
            product_ids = []
            for srv_row in srv_obj.browse(active_ids):
                for sp in srv_row.product_ids:
                    product_ids.append(sp)

            # Create certificate data values and fill a worsheet for each value created
            count = 0
            crt_data_values = srv_obj._create_crt_data(product_ids)
            for data_value in crt_data_values:
                count += 1
                ws = srv_obj.clone_worksheet(wb, wb._sheets[0], title="CRT"+str(count))
                srv_obj.fill_crt(data_value, ws)
                wb._sheets.append(ws)

            # Delete CRT template on first position
            if len(wb._sheets) > 1:
                wb.remove_sheet(wb._sheets[0])
                wb.active = 0
                xls_io = StringIO()
                wb.save(xls_io)
                self.write({'xls_file': base64.encodebytes(xls_io.getvalue()), 'xls_name': 'CRT_Consol'+'.xlsx'})
            else:
                raise ValidationError(_('Results not found, please check the CRT numbers of the selected services.'))

        return {
            'type': 'ir.actions.act_window',
            'name': _('CRT Consolidated Report'),
            'res_model': 'rt.service.crt.consol.wzd',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'res_id': self.id,
            'context': self.env.context
        }

    @api.multi
    def delete_crt_report(self):
        self.ensure_one()

        self.write({'xls_file': False, 'xls_name': False})
        return {
            'type': 'ir.actions.act_window',
            'name': _('CRT Consolidated Report'),
            'res_model': 'rt.service.crt.consol.wzd',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'res_id': self.id,
            'context': self.env.context
        }
