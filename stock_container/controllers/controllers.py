# -*- coding: utf-8 -*-
from odoo import http

# class StockContainer(http.Controller):
#     @http.route('/stock_container/stock_container/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/stock_container/stock_container/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('stock_container.listing', {
#             'root': '/stock_container/stock_container',
#             'objects': http.request.env['stock_container.stock_container'].search([]),
#         })

#     @http.route('/stock_container/stock_container/objects/<model("stock_container.stock_container"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('stock_container.object', {
#             'object': obj
#         })