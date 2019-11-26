# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api

class BillOfLandingCarga(models.Model):
    _name = 'rt.service.bill.of.landing.carga'
    _description = "Bill Of Landing Factura"

    rt_carga_id = fields.Many2one(comodel_name='rt.service.carga', string='Carga', ondelete="cascade")
    remitente_id = fields.Many2one(comodel_name='asociados.carpeta', string='Remitente',
                                   domain="[('type', '=','remitente')]")
    partner_remitente_id = fields.Many2one(comodel_name='res.partner', string='P.Remitente',
                                           domain=[('remittent', '=', True)])
    consigantario_id = fields.Many2one(comodel_name='asociados.carpeta', string='Consignatario',
                                       domain="[('type', '=','consignatario')]")
    partner_consigantario_id = fields.Many2one(comodel_name='res.partner', string='P.Consignatario',
                                               domain=[('consignee', '=', True)])
    partner_notificar_id = fields.Many2one(comodel_name='res.partner', string='P.Notificar',
                                           domain=[('notificar', '=', True)])
    notificar_id = fields.Many2one(comodel_name='asociados.carpeta', string='Notificar',
                                   domain="[('type', '=','notificar')]")
    package = fields.Integer(string='Bultos')
    load_presentation = fields.Many2one(comodel_name='catalogo.tipo.bulto', string=u'Tipo de bultos')
    ncm = fields.Char(string='NCM')
    raw_kg = fields.Float(string='Kg Bruto')
    container_number = fields.Char(string=u'Número de contenedor', size=13)
    container_type = fields.Many2one(comodel_name='fleet.vehicle', string='Tipo de Contenedor',
                                     domain=[('vehicle_type', '=', 'container')])
    seal_number = fields.Char(string='Número de precinto', size=32)
    bl_number = fields.Char(string="Numero de BL")
    attachment = fields.Many2many(comodel_name='ir.attachment', relation='bl_carga_attach_fac', column1='bl_id', column2='att_id')