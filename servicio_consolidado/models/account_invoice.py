# -*- coding: utf-8 -*-
import logging

from odoo import api, exceptions, fields, models, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning
import ipdb

_logger = logging.getLogger(__name__)


class AccountInvoice(models.Model):
    _inherit = "account.invoice"


    consolidado_service_product_id = fields.Many2one('producto.servicio.camion', string='Servicio Asociado')
    camion_id = fields.Many2one('carpeta.camion', string='Camion Asociado')
    # service_consolidado_ids = fields.Many2many('carpeta.camion', 'rt_service_consol_invoice_sup_rel', 'invoice_id', 'rt_service_product_id', 'Services',
    #                                copy=False)
    service_consolidado_ids = fields.One2many('carpeta.camion', 'invoice_id', 'Services')

    @api.multi
    def actualiza_estado_calenario(self, carpeta=None, estado=None):
        estados_obj = self.env['color.picker']
        calendario_obj = self.env['servicio.calendario']

        realizada_facturada = estados_obj.search([('name', '=', 'Carga Realizada y Facturada')])
        factura_rechazada = estados_obj.search([('name', '=', 'Factura Rechazada')])
        if carpeta:
            calendario = calendario_obj.search([('rt_service_id', '=', carpeta.id)])
            if calendario:
                if estado == 'Facturado':
                    calendario.color_pickier_id = realizada_facturada.id
                if estados_obj == 'Rechazado':
                    calendario.color_pickier_id = factura_rechazada.id

    @api.multi
    def action_invoice_cancel(self):
        cost_obj = self.env['rt.service.product.supplier']
        carpeta = False
        #Estamos en una operativa de Consolidados
        if self.camion_id:
            for line in self.invoice_line_ids:
                line.consolidado_service_product_id.invoiced_rejected = True
                line.consolidado_service_product_id.invoiced = False
                if line.tramo_facturado:
                    if line.tramo_facturado == 'national':
                        line.consolidado_service_product_id.tramo_nat = False
                    if line.tramo_facturado == 'international':
                        line.consolidado_service_product_id.tramo_inter = False
            self.camion_id.state = 'rejected'

        #Estamos en operativa nacional-internacional
        if self.rt_service_id:
            carpeta = self.rt_service_id
            for invoice in self:
                for line in invoice.invoice_line_ids:
                    if line.rt_service_product_id:
                        linea_costo = cost_obj.search([('rt_service_product_id', '=', line.rt_service_product_id.id)])
                        if linea_costo and linea_costo.invoice_id:
                            raise Warning('La factura contiene una linea con costo ascociado a una factura de proveedor')
                        line.rt_service_product_id.invoiced = False
                        line.rt_service_product_id.invoiced_rejected = True
                        if line.tramo_facturado:
                            if line.tramo_facturado == 'national':
                                line.rt_service_product_id.tramo_nat = False
                            if line.tramo_facturado == 'international':
                                line.rt_service_product_id.tramo_inter = False
                    if line.rt_service_product_ids:
                        for line_inv in line.rt_service_product_ids:
                            line_inv.invoiced = False
                            line_inv.invoiced_rejected = True
                            if line.tramo_facturado:
                                if line.tramo_facturado == 'national':
                                    line_inv.tramo_nat = False
                                if line.tramo_facturado == 'international':
                                    line_inv.tramo_inter = False

                if invoice.rt_service_id:
                    invoice.rt_service_id.state = 'invoice_rejected'

        #Estamos en la operativa de marfrig
        if self.marfrig_operation_id:
            for invoice in self:
                for line in invoice.service_marfrig_ids:
                    line.invoiced = False
                    line.invoiced_rejected = True
                if invoice.marfrig_operation_id:
                    invoice.marfrig_operation_id.state = 'invoice_rejected'

        # Para operativa de Deposito
        if self.deposito_operation_id:
            for depo in self.deposito_operation_id.deposito_srv_ids:
                depo.invoiced = False
                depo.invoiced_rejected = True

            self.deposito_operation_id.state = 'invoice_rejected'

        self.actualiza_estado_calenario(carpeta=carpeta, estado='Rechazado')

        return self.filtered(lambda inv: inv.state != 'cancel').action_cancel()

class AccountInvoiceLine(models.Model):
    _inherit = "account.invoice.line"

    consolidado_service_product_id = fields.Many2one('producto.servicio.camion', string='Servicio Asociado')




