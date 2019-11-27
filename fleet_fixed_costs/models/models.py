# -*- coding: utf-8 -*-

from odoo import models, fields, api
import ipdb

class FleetVehicleCost(models.Model):
    _inherit = 'fleet.vehicle.cost'

    is_toll = fields.Boolean(string='Costo de Peaje')

class FleetVehicle(models.Model):
    _inherit = 'fleet.vehicle'

    toll_count = fields.Integer(compute="_compute_count_toll", string='Services')


    @api.multi
    def act_show_toll_cost(self):
        """ This opens log view to view and add new log for this vehicle, groupby default to only show effective costs
            @return: the costs log view
        """
        ipdb.set_trace()
        self.ensure_one()
        copy_context = dict(self.env.context)
        copy_context.pop('group_by', None)
        res = self.env['ir.actions.act_window'].for_xml_id('fleet_fixed_costs', 'fleet_vehicle_fixed_action')
        res.update(
            context=dict(copy_context, default_vehicle_id=self.id, search_default_parent_false=True),
            domain=[('vehicle_id', '=', self.id), ('is_toll', '=', True)]
        )
        return res

    def _compute_count_toll(self):
        # Odometer = self.env['fleet.vehicle.odometer']
        # LogFuel = self.env['fleet.vehicle.log.fuel']
        # LogService = self.env['fleet.vehicle.log.services']
        # LogContract = self.env['fleet.vehicle.log.contract']
        # Cost = self.env['fleet.vehicle.cost']
        # for record in self:
        #     record.odometer_count = Odometer.search_count([('vehicle_id', '=', record.id)])
        #     record.fuel_logs_count = LogFuel.search_count([('vehicle_id', '=', record.id)])
        #     record.service_count = LogService.search_count([('vehicle_id', '=', record.id)])
        #     record.contract_count = LogContract.search_count([('vehicle_id', '=', record.id),('state','!=','closed')])
        #     record.cost_count = Cost.search_count([('vehicle_id', '=', record.id), ('parent_id', '=', False)])
        return