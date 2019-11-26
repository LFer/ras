# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
from odoo.osv import expression
import ipdb
from odoo.osv.expression import get_unaccent_wrapper
import re


class ResCountryCity(models.Model):
    _name = 'res.country.city'
    _description = 'Ciudades'

    name = fields.Char(string='Nombre')
    country_id = fields.Many2one('res.country', string='Pais')
    code = fields.Char(related='country_id.codigo_pais')
    state_id = fields.Many2one(comodel_name='res.country.state', string='Departamento')
    codigo_local = fields.Char(string='Cód. Loc.')

class CountryState(models.Model):
    _inherit = 'res.country.state'

    city_ids = fields.One2many('res.country.city', 'state_id', string='Ciudades')

class ResPartnerAddressExt(models.Model):
    _name = 'res.partner.address.ext'
    _description = 'Direcciones de Partners'

    name = fields.Char('Nombre Corto')
    street = fields.Char('Calle')
    street2 = fields.Char('Esquina')
    zip = fields.Char('C.P.', size=24, change_default=True)
    city_id = fields.Many2one('res.country.city', 'Ciudad')
    state_id = fields.Many2one("res.country.state", 'Estado', ondelete='restrict')
    country_id = fields.Many2one('res.country', 'País', ondelete='restrict')
    partner_id = fields.Many2one('res.partner', 'Empresa', ondelete='cascade')
    address_type = fields.Selection([
        ('load', 'Deposito'),
        ('otros','Otros'),
        ('beach_load', 'Playa de Contenedores Cargados'),
        ('beach_empty', 'Playa de Contenedores Vacíos'),
        ('invoice', u'Facturación'),
        ('tienda', u'Tienda'),
    ], 'Tipo de Depósito')
    opening = fields.Float('Apertura')
    closing = fields.Float('Cierre')
    rest = fields.Integer('Descanso')
    place_id = fields.Many2one('stock.warehouse', 'Depósito', required=False)
    deposit_number = fields.Char(string='Número de Depósito')
    aduana_id = fields.Many2one('fronteras', string='Aduana')
    parent_deposito_id = fields.Many2one(comodel_name='depositos', string='Deposito Relacionado')



class ResPartnerExpirationTypeDate(models.Model):
    _name = 'res.partner.expiration.type.date'
    _description = "Partner Expiration type date"
    _rec_name = 'exp_type_id'

    exp_type_id = fields.Many2one('res.partner.expiration.type', u'Tipo de expiración', required=True, ondelete="restrict")
    date = fields.Date('Date')
    partner_id = fields.Many2one('res.partner', 'Empresa', domain=[('driver', '=', True)], ondelete="cascade")


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.multi
    def _invoice_total_usd(self):
        if not self.ids:
            return True
        account_invoice_obj = self.env['account.invoice']
        partner_id = self.id

        search_params = [('partner_id', '=', partner_id), ('state', 'not in', ['draft', 'cancel']), ('type', '=', 'out_invoice')]

        partner_invoices = account_invoice_obj.search(search_params)
        currency_set = set([inv.currency_id.name for inv in partner_invoices])
        print(currency_set)
        if 'USD' in currency_set:
            self.only_usd = True
        if 'UYU' in currency_set:
            self.only_usd = False
        self.currency_id_usd = 2
        self.total_invoiced_usd = sum(invoice.amount_untaxed for invoice in partner_invoices)
        print(self.only_usd)

    only_usd = fields.Boolean(compute='_invoice_total_usd')
    currency_id_usd = fields.Many2one(comodel_name='res.currency', default=2)
    total_invoiced_usd = fields.Float(compute='_invoice_total_usd', string="Total Invoiced")
    address_ext_ids = fields.One2many('res.partner.address.ext', 'partner_id', u'Dirección')
    expenses_ids = fields.One2many('default.expenses', 'partner_parent_id', string='Gastos')
    exp_type_date_ids = fields.One2many('res.partner.expiration.type.date', 'partner_id', string=u'Expiración')
    social_reason = fields.Char(u'Razón Social', size=254)
    dispatcher = fields.Boolean('Despachante')
    freighter = fields.Boolean('Fletero')
    permissive = fields.Boolean('Permisado')
    dangers_loads = fields.Boolean('Carga Peligrosa')
    native_lic_number = fields.Integer(u'Número de Permiso Originario', size=20)
    native_lic_date = fields.Date('Fecha de Permiso Originario')
    comp_lic_number = fields.Integer(u'Número de Permiso Complementario', size=20)
    comp_lic_date = fields.Date('Fecha de Permiso Complementario')
    policy_number = fields.Integer(u'Número de Póliza de Seguros')
    ministries = fields.Boolean('MTOP')
    driver = fields.Boolean('Chofer')
    imo = fields.Boolean('IMO')
    user_id = fields.Many2one('res.partner', string='Salesperson',
                              help='The internal user in charge of this contact.', domain=[('seller', '=', True)])
    gen_of_message = fields.Boolean('Generador de Mensaje Simplificado')
    user_zf = fields.Boolean('Usuario ZF')
    remittent = fields.Boolean('Remitente')
    receiver = fields.Boolean('Destinatario')
    supplier_peons = fields.Boolean('Proveedor de Peones')
    supplier_hoist = fields.Boolean('Proveedor Montacargas')
    consignee = fields.Boolean('Consignatario')
    carrier = fields.Boolean('Porteador')
    where_paper = fields.Boolean('Donde quedan los papeles')
    load_agent = fields.Boolean('Agente de Carga')
    seller = fields.Boolean('Vendedor')
    deposito = fields.Boolean(u'Depósito')
    partner_seller_id = fields.Many2one('res.partner', 'Vendedor', domain=[('seller', '=', True)])
    documentacion = fields.Boolean(string=u'Documentación')
    is_ras_property = fields.Boolean('Es Propiedad de Ras Transport')
    playa = fields.Boolean(string='Playa de Contenedores')
    notificar = fields.Boolean(string='Notificar')
    name = fields.Char()
    fiscal = fields.Boolean()
    gestor = fields.Boolean('Gestor')


    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        if 'social_reason' in self._fields:
            args = args or []
            recs = self.browse()
            recs = self.search(['|', '|', '|', ('name', operator, name), ('social_reason', operator, name), ('vat', operator, name), ('ref', operator, name)] + args, limit=limit)
        return recs.name_get()

    # @api.multi
    # @api.depends('name', 'social_reason')
    # def name_get(self):
    #     return [(rec.id, '%s - %s' % (rec.name, rec.social_reason)) for rec in self]