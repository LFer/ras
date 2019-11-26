# -*- coding: utf-8 -*-
from odoo import http

# class CalendarioContenedores(http.Controller):
#     @http.route('/calendario_contenedores/calendario_contenedores/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/calendario_contenedores/calendario_contenedores/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('calendario_contenedores.listing', {
#             'root': '/calendario_contenedores/calendario_contenedores',
#             'objects': http.request.env['calendario_contenedores.calendario_contenedores'].search([]),
#         })

#     @http.route('/calendario_contenedores/calendario_contenedores/objects/<model("calendario_contenedores.calendario_contenedores"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('calendario_contenedores.object', {
#             'object': obj
#         })