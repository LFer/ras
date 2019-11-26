# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.exceptions import AccessError
import ipdb


class Digest(models.Model):
    _inherit = 'digest.digest'

    # kpi_account_bank_cash = fields.Boolean('Bank & Cash Moves')
    kpi_servicio_nacional_internacional = fields.Boolean('Carpetas Nacional / Internacional Creadas')
    kpi_cantidad_contenedores = fields.Boolean('Contenedores Movidos')
    kpi_cantidad_contenedores_value = fields.Integer(compute='_compute_kpi_cantidad_contenedores')
    kpi_servicio_nacional_internacional_value = fields.Integer(compute='_compute_kpi_total_services_values')
    # kpi_account_bank_cash_value = fields.Monetary(compute='_compute_kpi_account_total_bank_cash_value')
    kpi_cantidad_contenedores_national = fields.Boolean('Contenedores Movidos Nacional')
    kpi_cantidad_contenedores_national_value = fields.Integer(compute='_compute_kpi_cantidad_contenedores_nacional')


    def _compute_kpi_total_services_values(self):
        for record in self:
            start, end, company = record._get_kpi_compute_parameters()
            # carpetas = self.env['rt.service'].read_group([
            carpetas = self.env['rt.service'].search_count([
                ('start_datetime', '>=', start),
                ('start_datetime', '<', end)])
                #('company_id', '=', company.id)], ['journal_id', 'amount'], ['journal_id'])
            # record.kpi_account_bank_cash_value = sum([account_move['amount'] for account_move in carpetas])
            record.kpi_servicio_nacional_internacional_value = carpetas

    def _compute_kpi_cantidad_contenedores(self):
        contenedor = 'contenedor'
        for record in self:
            start, end, company = record._get_kpi_compute_parameters()
            # carpetas = self.env['rt.service'].read_group([
            cargas = self.env['rt.service.carga'].search_count([
                ('start_datetime', '>=', start),
                ('start_datetime', '<', end),
                ('load_type', '=', contenedor)
            ])
                #('company_id', '=', company.id)], ['journal_id', 'amount'], ['journal_id'])
            # record.kpi_account_bank_cash_value = sum([account_move['amount'] for account_move in carpetas])
            record.kpi_cantidad_contenedores_value = cargas

    def compute_kpis_actions(self, company, user):
        res = super(Digest, self).compute_kpis_actions(company, user)
        res.update({'kpi_servicio_nacional_internacional': 'servicio_base.action_rt_service_nacional&menu_id=%s' % (self.env.ref('servicio_base.menu_service_root_nacional').id)})
        res.update({'kpi_cantidad_contenedores': 'servicio_base.action_rt_carga_naional&menu_id=%s' % (self.env.ref('servicio_base.carga_nacional_menu').id)})
        return res

    def _compute_kpi_cantidad_contenedores_nacional(self):
        contenedor = 'contenedor'
        national = 'national'
        for record in self:
            start, end, company = record._get_kpi_compute_parameters()
            # carpetas = self.env['rt.service'].read_group([
            cargas = self.env['rt.service.carga'].search_count([
                ('start_datetime', '>=', start),
                ('start_datetime', '<', end),
                ('operation_type', '=', national)
                ('load_type', '=', contenedor)
            ])
                #('company_id', '=', company.id)], ['journal_id', 'amount'], ['journal_id'])
            # record.kpi_account_bank_cash_value = sum([account_move['amount'] for account_move in carpetas])
            record.kpi_cantidad_contenedores_national_value = cargas