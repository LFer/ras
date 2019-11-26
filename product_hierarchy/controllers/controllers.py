# -*- coding: utf-8 -*-
from odoo import http

# class ProductHierarchy(http.Controller):
#     @http.route('/product_hierarchy/product_hierarchy/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/product_hierarchy/product_hierarchy/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('product_hierarchy.listing', {
#             'root': '/product_hierarchy/product_hierarchy',
#             'objects': http.request.env['product_hierarchy.product_hierarchy'].search([]),
#         })

#     @http.route('/product_hierarchy/product_hierarchy/objects/<model("product_hierarchy.product_hierarchy"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('product_hierarchy.object', {
#             'object': obj
#         })