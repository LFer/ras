# -*- coding: utf-8 -*-

from odoo import models, fields, api
import ipdb

class FleetVehicleCost(models.Model):
    _inherit = 'fleet.vehicle.cost'

    is_toll = fields.Boolean(string='Costo de Peaje')

    @api.model
    def create(self, values):
        context = self._context
        if 'deault_cost_subtype_id' in context:
            values['cost_subtype_id'] = context.get('deault_cost_subtype_id', False)
        fleet = super(FleetVehicleCost, self).create(values)
        return fleet

class FleetVehicle(models.Model):
    _inherit = 'fleet.vehicle'

    toll_count = fields.Integer(compute="_compute_count_toll", string='Services')




    @api.multi
    def act_show_toll_cost(self):
        """ This opens log view to view and add new log for this vehicle, groupby default to only show effective costs
            @return: the costs log view
        """
        cost_subtype_obj = self.env['fleet.service.type']
        cost_subtype = cost_subtype_obj.search([('name', '=', 'Peaje')], limit=1)
        toll = False
        if cost_subtype:
            toll = cost_subtype.id


        # cost_subtype_id
        self.ensure_one()
        copy_context = dict(self.env.context)
        copy_context.pop('group_by', None)
        res = self.env['ir.actions.act_window'].for_xml_id('fleet_fixed_costs', 'fleet_vehicle_fixed_action')
        res.update(
            context=dict(copy_context, default_vehicle_id=self.id, search_default_parent_false=True, default_is_toll=True, deault_cost_subtype_id=toll, is_from_toll=True),
            domain=[('vehicle_id', '=', self.id), ('is_toll', '=', True)]
        )
        return res

    def _compute_count_toll(self):
        Cost = self.env['fleet.vehicle.cost']
        cost_subtype_obj = self.env['fleet.service.type']
        cost_subtype = cost_subtype_obj.search([('name', '=', 'Peaje')], limit=1)
        for record in self:
            record.toll_count = Cost.search_count([('vehicle_id', '=', record.id), ('parent_id', '=', False), ('cost_subtype_id', '=', cost_subtype.id)])
        return