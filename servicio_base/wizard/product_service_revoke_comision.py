# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError, Warning
import ipdb
from odoo.addons import decimal_precision as dp
import itertools

class RevokeComision(models.TransientModel):
    _name = 'rechazar.comision'
    _description = 'Rechzar Comision'

    rt_service_product_id = fields.Many2one(comodel_name='rt.service.productos')
    motivo = fields.Text(string='Motivo')



    @api.multi
    def rechazar_correcion_comision(self):
        for rec in self.rt_service_product_id:
            if not self.motivo:
                raise Warning('Debe ingresar el motivo del rechazo')
            rec.estado_comision = 'correcion_rechazada'

        body = u"Motivo Rechazo de Solicitud: %s" % self.motivo
        message = rec.message_post(body=body, message_type='notification', subtype=None, parent_id=False)

        message_carpeta = rec.rt_service_id.message_post(body=body, message_type='notification', subtype=None, parent_id=False)


        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        base_url += '/web?#id=%s&action=935&model=%s&view_type=form&menu_id=%s' % (rec.id, rec._name, rec._name)
        message_body = 'El usuario %s ha rechazado una solicitud de  corrección de Comisión para el siguiente documento ' % self.env['res.users'].browse(self._context['uid']).name
        message_body += '<br/>'
        message_body += 'Motivo: %s' % self.motivo
        message_body += '<br/>'
        message_body += "<a href='%s' > Haga click aquí para ver </a>" % base_url
        odoobot = "odoobot@example.com"
        user_to_notify = rec.user_comision_id.login
        mail = self.env['mail.mail']
        mail_data = {'subject': 'Solicitud de Corrección de Comisión Rechazada: ' + self.motivo,
                     'email_from': odoobot,
                     'email_to': user_to_notify,
                     'body_html': message_body,
                     }
        mail_out = mail.create(mail_data)
        mail_out.send()

        return True

class RevokeCost(models.TransientModel):
    _name = 'rechazar.costo'
    _description = 'Rechzar Costo'

    rt_service_product_id = fields.Many2one(comodel_name='rt.service.productos')
    motivo = fields.Text(string='Motivo')



    @api.multi
    def rechazar_correcion_costo(self):
        for rec in self.rt_service_product_id:
            if not self.motivo:
                raise Warning('Debe ingresar el motivo del rechazo')
            rec.estado_comision = 'correcion_rechazada'

        body = u"Motivo Rechazo de Solicitud: %s" % self.motivo
        message = rec.message_post(body=body, message_type='notification', subtype=None, parent_id=False)

        message_carpeta = rec.rt_service_id.message_post(body=body, message_type='notification', subtype=None, parent_id=False)


        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        base_url += '/web?#id=%s&action=935&model=%s&view_type=form&menu_id=%s' % (rec.id, rec._name, rec._name)
        message_body = 'Su solicitud de corrección de costo para el siguiente documento ha sido rechazada ' % self.env['res.users'].browse(self._context['uid']).name
        message_body += '<br/>'
        message_body += 'Motivo: %s' % self.motivo
        message_body += '<br/>'
        message_body += "<a href='%s' > Haga click aquí para ver </a>" % base_url
        odoobot = "odoobot@example.com"
        user_to_notify = rec.user_cost_id.login
        mail = self.env['mail.mail']
        mail_data = {'subject': 'Solicitud de corrección de costo rechazada: ' + self.motivo,
                     'email_from': odoobot,
                     'email_to': user_to_notify,
                     'body_html': message_body,
                     }
        mail_out = mail.create(mail_data)
        mail_out.send()

        return True


class RevokeCarga(models.TransientModel):
    _name = 'rechazar.correcion.carga'
    _description = 'Rechzar Correcion Carga'

    rt_carga_id = fields.Many2one(comodel_name='rt.service.carga')
    motivo = fields.Text(string='Motivo')



    @api.multi
    def rechazar_correcion_carga(self):
        for rec in self.rt_carga_id:
            if not self.motivo:
                raise Warning('Debe ingresar el motivo del rechazo')
            rec.estado_comision = 'correcion_rechazada'

        body = u"Motivo rechazo de solicitud: %s" % self.motivo
        message = rec.message_post(body=body, message_type='notification', subtype=None, parent_id=False)

        message_carpeta = rec.rt_service_id.message_post(body=body, message_type='notification', subtype=None, parent_id=False)

        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        base_url += '/web?#id=%s&action=935&model=%s&view_type=form&menu_id=%s' % (rec.id, rec._name, rec._name)
        message_body = 'Su solicitud de corrección de costo para el siguiente documento ha sido rechazada ' % self.env['res.users'].browse(self._context['uid']).name
        message_body += '<br/>'
        message_body += 'Motivo: %s' % self.motivo
        message_body += '<br/>'
        message_body += "<a href='%s' > Haga click aquí para ver </a>" % base_url
        odoobot = "odoobot@example.com"
        user_to_notify = rec.user_correction_id.login
        mail = self.env['mail.mail']
        mail_data = {'subject': 'Solicitud de corrección de carga rechazada: ' + self.motivo,
                     'email_from': odoobot,
                     'email_to': user_to_notify,
                     'body_html': message_body,
                     }
        mail_out = mail.create(mail_data)
        mail_out.send()

        return True