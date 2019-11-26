# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import ipdb
import odoo.addons.decimal_precision as dp
from odoo import api, fields, models
_logger = logging.getLogger(__name__)


class asociados_a_carpeta(models.Model):
    _name = "asociados.carpeta"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _description = "Remitentes"

    def _default_category(self):
        return self.env['res.partner.category'].browse(self._context.get('category_id'))


    type = fields.Selection(
        [('remitente', 'Remitente'),
         ('consignatario', 'Consignatario'),
         ('destinatario', 'Destinatario'),
         ('notificar', 'Notificar a'),
        ], string='Tipo de Asociado',
        )
    name = fields.Char(index=True, string='Nombre')
    street = fields.Char()
    city = fields.Char()
    state_id = fields.Many2one("res.country.state", string='State', ondelete='restrict')
    country_id = fields.Many2one('res.country', string='Country', ondelete='restrict')
    email = fields.Char()
    phone = fields.Char(string='Télefono')
    mobile = fields.Char(string='Celular')
    document_nro = fields.Char()
    active = fields.Boolean(default=True)
    image = fields.Binary("Image", attachment=True,help="This field holds the image used as avatar for this contact, limited to 1024x1024px", )
    category_id = fields.Many2many('res.partner.category', column1='partner_id',column2='category_id', string='Etiquetas', default=_default_category)
    color = fields.Integer(string='Color Index', default=0)
    image_small = fields.Binary("Small-sized image", attachment=True)
    image_medium = fields.Binary("Medium-sized image", attachment=True)
    vat = fields.Char(string='RUT')

asociados_a_carpeta()