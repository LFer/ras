# -*- coding: utf-8 -*-
from odoo import http

# class ProductOwner(http.Controller):
#     @http.route('/product_owner/product_owner/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/product_owner/product_owner/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('product_owner.listing', {
#             'root': '/product_owner/product_owner',
#             'objects': http.request.env['product_owner.product_owner'].search([]),
#         })

#     @http.route('/product_owner/product_owner/objects/<model("product_owner.product_owner"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('product_owner.object', {
#             'object': obj
#         })