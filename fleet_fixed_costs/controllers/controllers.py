# -*- coding: utf-8 -*-
from odoo import http

# class FleetFixedCosts(http.Controller):
#     @http.route('/fleet_fixed_costs/fleet_fixed_costs/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/fleet_fixed_costs/fleet_fixed_costs/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('fleet_fixed_costs.listing', {
#             'root': '/fleet_fixed_costs/fleet_fixed_costs',
#             'objects': http.request.env['fleet_fixed_costs.fleet_fixed_costs'].search([]),
#         })

#     @http.route('/fleet_fixed_costs/fleet_fixed_costs/objects/<model("fleet_fixed_costs.fleet_fixed_costs"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('fleet_fixed_costs.object', {
#             'object': obj
#         })