# -*- coding: utf-8 -*-
import logging

from odoo import api, fields, models
import ipdb

_logger = logging.getLogger(__name__)

class ColorPicker(models.Model):
    _name = "color.picker"
    _description = "Colores"

    name = fields.Char(string='Name')


class ServicioCalendario(models.Model):
    _name = "servicio.calendario"
    _description = "Calendario de Servcios"

    def _get_default_state(self):
        color_obj = self.env['color.picker']
        all_colors = color_obj.search([])
        if len(all_colors) > 1:
            return all_colors[0].id
        return False

    name = fields.Char(string='Ref')
    start = fields.Datetime('Inicio', required=True, help="Start date of an event, without time for full days events")
    stop = fields.Datetime('Stop', required=True, help="Stop date of an event, without time for full days events")
    rt_service_id = fields.Many2one(comodel_name='rt.service', string='Carpeta Relacionada')
    partner_id = fields.Many2one(comodel_name='res.partner', string='Cliente')
    duration = fields.Float('Duration')
    allday = fields.Boolean('All Day', default=False)
    html_field = fields.Html(string='Info', readonly=True)
    color_pickier_id = fields.Many2one('color.picker', 'Estado', default=_get_default_state)
    operation_type = fields.Selection([('national', 'Nacional'), ('international', 'Internacional')],string='Tipo de Servicio')
    #marfrig_operation_id = fields.Many2one('marfrig.service.base', string='Carpeta Marfrig Asociada')
    notas = fields.Text(string='Notas')
    attach_notas = fields.Many2many(comodel_name='ir.attachment', relation='calendario_attach_notas', column1='calendario_id', column2='attach_cont_id')
    load_type = fields.Selection([('bulk', 'Bulk-Carga Suelta'), ('contenedor', 'Contenedor'), ('liquido_granel', u'Granel Líquido'),('solido_granel', u'Granel Solido')], string='Tipo de Carga')

    @api.multi
    @api.depends('allday', 'start', 'stop')
    def _compute_dates(self):
        for record in self:
            if record.allday and record.start and record.stop:
                record.start_date = record.start.date()
                record.start_datetime = False
                record.stop_date = record.stop.date()
                record.stop_datetime = False
                record.duration = 0.0
            else:
                record.start_date = False
                record.start_datetime = record.start
                record.stop_date = False
                record.stop_datetime = record.stop
                record.duration = self._get_duration(record.start, record.stop)

    @api.multi
    @api.depends('rt_service_id')
    def get_info_from_nodes(self):
        dua = ''
        table = ''
        table += '<table style="width:100%;">'
        table += '<thead style="border: thin solid gray;">'
        table += '<tr style="border: thin solid gray;">'
        table += '<th style="border: thin solid gray; text-align: center">Nro Contenedor</th>'
        table += '<th style="border: thin solid gray; text-align: center">DUA</th>'
        table += '<th style="border: thin solid gray; text-align: center">Matricula</th>'
        table += '<th style="border: thin solid gray; text-align: center">Chofer</th>'
        table += '<th style="border: thin solid gray; text-align: center">Fletero</th>'
        table += '</tr style="border: thin solid gray;">'
        table += '</thead>'
        table += '<tbody>'
        for srv in self.env['rt.service.productos'].search([('rt_service_id', '=', self.rt_service_id.id)]):
            if srv.rt_service_id.dua_type == 'cabezal':
                carpeta = self.rt_service_id
                dua = str(carpeta.dua_aduana) + '-' + str(carpeta.dua_anio) + '-' + str(carpeta.dua_numero)
            nro_contenedor = srv.rt_carga_id.container_number if srv.rt_carga_id.container_number else 'N/A'
            table += '<tr style="border: thin solid gray;">'
            table += '<td style="border: thin solid gray;text-align:center;"````>%(dep)s</td>' % {'dep': nro_contenedor} # Numero de Contenedor
            table += '<td style="border: thin solid gray;text-align:center;"````>%(dep)s</td>' % {'dep': dua}  # DUA
            table += '<td style="border: thin solid gray;text-align:center;"````>%(dep)s</td>' % {'dep': srv.vehicle_id.license_plate if srv.vehicle_id else 'N/A'}  # MATRICULA
            table += '<td style="border: thin solid gray;text-align:center;"````>%(dep)s</td>' % {'dep': srv.driver_id.name if srv.driver_id.name else 'N/A'}  # Chofer
            table += '<td style="border: thin solid gray;text-align:center;"````>%(dep)s</td>' % {'dep': srv.chofer if srv.chofer else 'N/A'}  # Fletero

        table += '</tr>'

        table += '</tbody>'
        table += '</table>'
        self.html_field = table
