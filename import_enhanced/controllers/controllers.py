# -*- coding: utf-8 -*-
from odoo import http

# class ImportEnhanced(http.Controller):
#     @http.route('/import_enhanced/import_enhanced/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/import_enhanced/import_enhanced/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('import_enhanced.listing', {
#             'root': '/import_enhanced/import_enhanced',
#             'objects': http.request.env['import_enhanced.import_enhanced'].search([]),
#         })

#     @http.route('/import_enhanced/import_enhanced/objects/<model("import_enhanced.import_enhanced"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('import_enhanced.object', {
#             'object': obj
#         })