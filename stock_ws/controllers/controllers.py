# -*- coding: utf-8 -*-
from odoo import http

# class StockWs(http.Controller):
#     @http.route('/stock_ws/stock_ws/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/stock_ws/stock_ws/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('stock_ws.listing', {
#             'root': '/stock_ws/stock_ws',
#             'objects': http.request.env['stock_ws.stock_ws'].search([]),
#         })

#     @http.route('/stock_ws/stock_ws/objects/<model("stock_ws.stock_ws"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('stock_ws.object', {
#             'object': obj
#         })