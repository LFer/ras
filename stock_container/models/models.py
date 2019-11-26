# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo import api, fields, models, tools, SUPERUSER_ID, _
from odoo.exceptions import UserError, AccessError, ValidationError, Warning
from odoo.tools.safe_eval import safe_eval
from odoo.addons import decimal_precision as dp
import ipdb

class DistribuyePaquetesWizard(models.Model):
    _name = "distribuye.paquetes.wizard"
    _description = "Asistente para distribuicion de Paquetes"


    @api.multi
    def distribuir_paquetes(self):
        paquetes_por_batch = 2
        context = self._context.copy()
        paquete_obj = self.env['product.template']
        paquetes_ids = context.get('active_ids', [])
        paquetes = paquete_obj.browse(paquetes_ids)
        if len(paquetes_ids) % paquetes_por_batch != 0:
            raise Warning('No se pudo separar entre 18 paquetes')

        #Necesitamos armar listas de 18 paquetes por batch
        #Para probar vamos hacer batches de 5 productos
        paquetes_lista = [paquetes_ids[i:i + paquetes_por_batch] for i in range(0, len(paquetes_ids), paquetes_por_batch)]

        #Iteramos sobre los paquetes y vamos creando los remitos
        picking_obj = self.env['stock.picking']
        # partner_renner = self.env['res.partner'].search([('name', '=', 'Lojas Renner Uruguay')])






        ipdb.set_trace()

        #Por cada conjunto de paquetes creo un remito de salida
        for pq in paquetes_lista:
            for prod in paquete_obj.browse(pq):
                picking_type = self.sudo().env['stock.picking.type'].search([('code', '=', 'outgoing'), ('name', '=', 'Órdenes de entrega')], limit=1).id

                if not picking_type:
                    picking_type = 2

                cabezal_location_id = self.env['stock.location'].browse(88)

                cabezal_location_dest_id = self.env['stock.location'].search([('name', '=', 'Customers'), ('usage', '=', 'customer')])

                stock_move_lines = []
                lines = {}
                lines['name'] = '/'
                lines['location_id'] = cabezal_location_dest_id.id
                lines['location_dest_id'] = cabezal_location_dest_id.id
                # lines['date'] = prod.date
                lines['product_id'] = prod.id
                lines['product_uom_qty'] = 1
                lines['product_uom'] = prod.uom_id.id
                # lines['x_studio_po'] = prod.x_studio_po
                # lines['x_studio_embarque'] = prod.x_studio_embarque
                # lines['x_studio_mic'] = prod.x_studio_mic
                # lines['x_studio_crt'] = prod.x_studio_crt
                stock_move_lines.append((0, 0, lines))

                pick = picking_obj.create({
                    # 'partner_id': partner_renner.id,
                    'picking_type_id': picking_type,
                    'location_id': cabezal_location_id.id,
                    'location_dest_id': cabezal_location_dest_id.id,
                    # 'scheduled_date': self.scheduled_date,
                    'move_ids_without_package': stock_move_lines,


                })





        return