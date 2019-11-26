# -*- coding: utf-8 -*-
from odoo import http

# class AccountReportsCustom(http.Controller):
#     @http.route('/account_reports_custom/account_reports_custom/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/account_reports_custom/account_reports_custom/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('account_reports_custom.listing', {
#             'root': '/account_reports_custom/account_reports_custom',
#             'objects': http.request.env['account_reports_custom.account_reports_custom'].search([]),
#         })

#     @http.route('/account_reports_custom/account_reports_custom/objects/<model("account_reports_custom.account_reports_custom"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('account_reports_custom.object', {
#             'object': obj
#         })