# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api

class FacturaCarga(models.Model):
    _name = 'rt.service.factura.carga'
    _description = "Carga Factura"

    rt_carga_id = fields.Many2one(comodel_name='rt.service.carga', string='Carga', ondelete="cascade")
    remitente_id = fields.Many2one(comodel_name='asociados.carpeta', string='Remitente', domain="[('type', '=','remitente')]")
    partner_remitente_id = fields.Many2one(comodel_name='res.partner', string='P.Remitente', domain=[('remittent', '=', True)])
    consigantario_id = fields.Many2one(comodel_name='asociados.carpeta', string='Consignatario', domain="[('type', '=','consignatario')]")
    partner_consigantario_id = fields.Many2one(comodel_name='res.partner', string='P.Consignatario', domain=[('consignee', '=', True)])
    destinatario_id = fields.Many2one(comodel_name='asociados.carpeta', string='Destinatario', domain="[('type', '=','destinatario')]")
    partner_destinatario_id = fields.Many2one(comodel_name='res.partner', string='P.Destinatario', domain=[('receiver', '=', True)])
    partner_notificar_id = fields.Many2one(comodel_name='res.partner', string='P.Notificar', domain=[('notificar','=', True)])
    notificar_id = fields.Many2one(comodel_name='asociados.carpeta', string='Notificar',domain="[('type', '=','notificar')]")
    invoice_description = fields.Text(string='Descripción')
    invoice_list = fields.Char(string='NºFactura')
    market_value = fields.Float(string='Valor')
    market_value_desc = fields.Text(string='Valor de la mercaderia en texto')
    market_value_currency_id = fields.Many2one(string='Moneda', comodel_name='res.currency')
    ncm = fields.Char(string='NCM')
    market_origin = fields.Char(string='Origen')
    attachment = fields.Many2many(comodel_name='ir.attachment', relation='fac_carga_attach_fac', column1='fac_id', column2='att_id', string="Attendees")

    @api.onchange('destinatario_id')
    def invisible_en_transito(self):
        for rec in self:
            rec.consigantario_id = rec.destinatario_id
            rec.notificar_id = rec.destinatario_id

    @api.onchange('partner_destinatario_id')
    def invisible_en_transito(self):
        for rec in self:
            rec.partner_consigantario_id = rec.partner_destinatario_id
            rec.partner_notificar_id = rec.partner_destinatario_id
