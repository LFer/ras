# -*- coding: utf-8 -*-
from odoo import fields, models, api,_
import ipdb
from odoo.exceptions import UserError, ValidationError, Warning
import ipdb

class ExpirationType(models.Model):
    _name = 'expiration.type'
    _description = "Expiration type"

    name = fields.Char('Nombre', required=True)

class DocumentType(models.Model):
    _name = 'document.type'
    _description = "Tipo de Documento"

    name = fields.Char('Nombre', required=True)


class ExpirationTypeDate(models.Model):
    _name = 'expiration.type.date'
    _description = "Expiration type date"
    _rec_name = 'exp_type_id'

    exp_type_id = fields.Many2one(comodel_name='expiration.type', string='Tipo de expiración', required=True,
                                  ondelete="restrict")
    date = fields.Date('Fecha')
    vehicle_id = fields.Many2one(comodel_name='fleet.vehicle', string='Vehículo',
                                 domain=[('vehicle_type', 'not in', ['hoist', 'container'])], ondelete="cascade")
    document_type_id = fields.Many2one(comodel_name='document.type', string='Tipo de Documento')
    attachment = fields.Many2many('ir.attachment')
    number = fields.Integer('Número')

class VehicleTypeSnub(models.Model):
    _name = 'vehicle.type.snub'
    _description = "Type of Snub"

    name = fields.Char('Nombre', required=True)


class VehicleAxis(models.Model):
    _name = 'vehicle.axis'
    _description = "Axis"

    name = fields.Char(string='Name', required=True)


class FleetVehicle(models.Model):
    _inherit = 'fleet.vehicle'
    _description = 'Information on a vehicle'
    _rec_name = 'nombre'

    rt_service_id = fields.Many2one(comodel_name='rt.service', string='Carpeta Relacionada')
    gps_type = fields.Selection([('nacional', 'Nacional'), ('inter', 'Internacional')], string='Tipo de Gps')
    license_plate = fields.Char('License Plate', required=False, help='License plate number of the vehicle (ie: plate number for a car)')
    vin_sn = fields.Char('Motor Number', help='Unique number written on the vehicle motor (VIN/SN number)')
    fletero_id = fields.Many2one('res.partner', 'Fletero', domain=[('freighter', '=', True)])
    driver_id = fields.Many2one('hr.employee', 'Chofer', help=u'Chofer del Vehículo')
    chassis_model = fields.Char(u'Número de Chasis')
    chassis_year = fields.Char(u'Año de fabricación del chasis')
    vehicle_type = fields.Selection([('truck', 'Camion'),  # Camión
                                     ('semi_tow', 'Semi-Remolque'),  # Semi remolque
                                     ('hoist', 'Montacarga'),  # Montacarga
                                     ('container', 'Contenedor'),  # Contenedor
                                     ('tractor', 'Tractor'),  # Tractor
                                     ('camioneta', 'Camioneta'),  # Camioneta
                                     ('elevator', 'Elevador'),  # Elevador
                                     ('stacker', 'Stacker'),  # Stacker
                                     ], u'Tipo de Vehículo', required=True, default='truck')
    crawl_capacity = fields.Float('Crawl capacity')
    imo = fields.Boolean('IMO')
    semi_tow_plate_id = fields.Many2one('fleet.vehicle', 'Semi-Tow licence plate', domain=[('vehicle_type', '=', 'semi_tow')])
    type_snub_id = fields.Many2one('vehicle.type.snub', 'Type of Snub')
    axis_qty_id = fields.Many2one('vehicle.axis', 'Quantity of axes')
    container_type = fields.Selection([('20', '20'),
                                       ('40', '40'),
                                       ('40 HC', '20 HC'),
                                       ('20 OT', '20 OT'),
                                       ('40 OT', '40 OT'),
                                       ('20 FR', '20 FR'),
                                       ('40 FR', '40 FR'),
                                       ('20 REEFER', '20 REEFER'),
                                       ('40 HC REEFER', '40 HC REEFER'),
                                       ('Other', 'Other')], string='Container Type')
    cont_ext_width = fields.Float('Ext Width')
    cont_ext_height = fields.Float('Ext Height')
    cont_ext_length = fields.Float('Ext Length')
    cont_int_width = fields.Float('Int Width')
    cont_int_height = fields.Float('Int Height')
    cont_int_length = fields.Float('Int Length')
    owner_code = fields.Char('Owner code', size=4)
    serial_number = fields.Integer('Serial number')
    autocontrol_number = fields.Integer('Autocontrol number')
    size = fields.Float('Size')
    type = fields.Char('Type', size=2)
    tare = fields.Float('Tare')
    payload = fields.Float('Payload')
    cu_cup = fields.Float('Volume')
    is_ras_property = fields.Boolean('¿Propio?', default=True)
    is_fletero = fields.Boolean('¿Fletero?')
    expenses_ids = fields.One2many('default.expenses', 'vehicle_parent_id', string='Expenses')
    exp_type_date_ids = fields.One2many('expiration.type.date', 'vehicle_id', string='Expiration')
    libreta = fields.Binary(string='Libreta')
    fecha_vencimiento_libreta = fields.Date(string='Vencimiento')
    codigo_contenedor_id = fields.Many2one(comodel_name='codigos.contenedores', string='Código de Contenedor')
    image_vehicle = fields.Binary(string="Logo vehiculo", readonly=False)
    name = fields.Char(compute="_compute_vehicle_name", store=False)
    operativa_nacional = fields.Boolean('Es Nacional')
    operativa_internacional = fields.Boolean('Es Internacional')
    chofer = fields.Char('Chofer')
    documento_chofer = fields.Char('Doc')
    mic_number = fields.Char(string='Numero MIC')
    attachment = fields.Many2many('ir.attachment')
    nombre = fields.Char()

    @api.depends('vehicle_type', 'license_plate')
    def _compute_vehicle_name(self):
        for record in self:
            record.name = record.vehicle_type + '-' + record.license_plate

    @api.multi
    @api.depends('nombre', 'license_plate')
    def name_get(self):
        for rec in self:
            pass
        return [(rec.id, '%s - %s' % (rec.brand_id.name, rec.license_plate)) for rec in self]

    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        recs = self.browse()
        recs = self.search([('license_plate', operator, name)] + args, limit=limit)
        return recs.name_get()

    @api.model
    def create(self,vals):
        if not vals.get('license_plate', False):
            vals['license_plate'] = 'N/A'
        return super(FleetVehicle, self).create(vals)

    @api.multi
    @api.onchange('vehicle_type','imo')
    def onchange_value_imo(self):
        return {}

    @api.multi
    @api.onchange('driver_id')
    def onchange_driver_id(self):
        domain = {}
        warning = {}
        res = {}
        employee_obj = self.env['hr.employee']
        driver = employee_obj.search([('category_ids.name', '=', 'Chofer')])
        domain = {'driver_id': [('id', 'in', driver.ids)]}
        if warning:
            res['warning'] = warning
        if domain:
            res['domain'] = domain
        return res

    def return_action_to_open(self):
        context = self.env.context.copy() or {}
        for key in context.copy().keys():
            if key.startswith('default_') or key.startswith('search_default_') or key == 'tree_view_ref' or key == 'form_view_ref' or key == 'search_view_ref':
                context.pop(key)
        return super(FleetVehicle, self).return_action_to_open()

    @api.multi
    def act_show_log_cost(self):
        context = self.env.context.copy() or {}
        for key in context.copy().keys():
            if key.startswith('default_') or key.startswith('search_default_') or key == 'tree_view_ref' or key == 'form_view_ref' or key == 'search_view_ref':
                context.pop(key)
        return super(FleetVehicle, self).act_show_log_cost()




class FleetVehicleModel(models.Model):
    _inherit = 'fleet.vehicle.model'

    image_model = fields.Binary(string="Logo", readonly=False)

    @api.onchange('brand_id')
    def _onchange_brand(self):
        return

class FleetVehicleModelBrand(models.Model):
    _inherit = 'fleet.vehicle.model.brand'

    image_brand = fields.Binary(string="Logo", readonly=False)


class FleetVehicleLogFuel(models.Model):
    _inherit = 'fleet.vehicle.log.fuel'

    product_to_invoice = fields.Many2one(comodel_name='product.product', string='Producto Facturable')
    invoice_id = fields.Many2one(comodel_name='account.invoice', string='Factura Relacionada')

    @api.onchange('liter', 'price_per_liter', 'amount')
    def _onchange_liter_price_amount(self):
        # need to cast in float because the value receveid from web client maybe an integer (Javascript and JSON do not
        # make any difference between 3.0 and 3). This cause a problem if you encode, for example, 2 liters at 1.5 per
        # liter => total is computed as 3.0, then trigger an onchange that recomputes price_per_liter as 3/2=1 (instead
        # of 3.0/2=1.5)
        # If there is no change in the result, we return an empty dict to prevent an infinite loop due to the 3 intertwine
        # onchange. And in order to verify that there is no change in the result, we have to limit the precision of the
        # computation to 2 decimal
        liter = float(self.liter)
        price_per_liter = float(self.price_per_liter)
        amount = float(self.amount)
        if liter > 0 and price_per_liter > 0 and round(liter * price_per_liter, 2) != amount:
            self.amount = round(liter * price_per_liter, 1)
        elif amount > 0 and liter > 0 and round(amount / liter, 2) != price_per_liter:
            self.price_per_liter = round(amount / liter, 1)
        elif amount > 0 and price_per_liter > 0 and round(amount / price_per_liter, 2) != liter:
            self.liter = round(amount / price_per_liter, 1)


class MakeInvoice(models.TransientModel):
    _name = 'fleet.vehicle.log.fuel.make.invoice'
    _description = 'Create Mass Invoice (Fleet)'

    group = fields.Boolean('IVA Incluido', help='Marque esta casilla si el precio por litro informado incluye IVA ')



    @api.multi
    def make_invoices(self):
        context = self._context.copy()
        fuel_ids = context.get('active_ids', [])
        inv_obj = self.env['account.invoice']
        if not self._context.get('active_ids'):
            return {'type': 'ir.actions.act_window_close'}
        fuel_obj = self.env['fleet.vehicle.log.fuel']
        fuel_logs = fuel_obj.browse(fuel_ids)
        journal_id = self.env['account.journal'].search([('type', '=', 'purchase')], limit=1)
        tax_obj = self.env['account.tax']
        account_obj = self.env['account.account']
        cuenta = account_obj.search([('code', '=', '54011004')])
        if self.group:
            taxes = tax_obj.search([('name', '=', 'IVA Combustibles')])
        lineas = []
        new_invoices = []
        line_dict = {}


        for line in fuel_logs:
            if line.invoice_id:
                raise Warning('Uno de los registros ya esta facturado')
            price_per_liter = round(line.price_per_liter / 1.22 if self.group else line.price_per_liter, 5)
            liters = round(line.liter, 3)
            line_dict['name'] = line.product_to_invoice.name
            # line_dict['account_id'] = line.product_to_invoice.property_account_expense_id.id
            line_dict['account_id'] = cuenta.id
            line_dict['price_unit'] = price_per_liter
            line_dict['quantity'] = liters
            line_dict['uom_id'] = line.product_to_invoice.uom_id.id
            line_dict['product_id'] = line.product_to_invoice.id
            line_dict['vehicle_id'] = line.vehicle_id.id
            # line_dict['invoice_line_tax_ids'] = [(6, 0, [x.id for x in line.product_to_invoice.supplier_taxes_id])]
            line_dict['invoice_line_tax_ids'] = [(6, 0, taxes.ids)] if self.group else False

            lineas.append((0, 0, line_dict))

            invoice = inv_obj.create({
                'origin': line.name if line.name else '/',
                'type': 'in_invoice',
                'account_id': line.vendor_id.property_account_payable_id.id,
                'partner_id': line.vendor_id.id,
                'journal_id': journal_id.id,
                'currency_id': journal_id.company_id.currency_id.id,
                'reference': line.inv_ref,
                'date_invoice': line.date,
                #'fiscal_position_id': product_service.rt_service_id.partner_invoice_id.property_account_position_id.id,
                #'company_id': product_service.rt_service_id.company_id.id,
                #'user_id': product_service.rt_service_id.user_id and product_service.rt_service_id.user_id.id,
                'invoice_line_ids': lineas
            })
            rounding_account = 1497
            rounding_line = []
            for inv_line in invoice.invoice_line_ids:
                if line.amount != inv_line.price_total:
                    #Si el total de la factura es mayor al total tengo que restar
                    if inv_line.price_total > line.amount:
                        rounding_amount = round(line.amount - inv_line.price_total, 2)
                        rounding_line = self.env['account.invoice.line'].new({
                            'name': self.cash_rounding_id.name,
                            'invoice_id': invoice.id,
                            'account_id': self.cash_rounding_id.account_id.id,
                            'price_unit': rounding_amount,
                            'quantity': 1,
                            'is_rounding_line': True,
                            'sequence': 9999  # always last line
                        })
                    #tengo qe sumar
                    else:
                        rounding_amount = round(line.amount - inv_line.price_total, 2)
                        rounding_line = self.env['account.invoice.line'].new({
                            'name': 'Redondeo',
                            'invoice_id': invoice.id,
                            'account_id': rounding_account,
                            'price_unit': rounding_amount,
                            'quantity': 1,
                            'is_rounding_line': True,
                            'sequence': 9999  # always last line
                        })


            invoice.invoice_line_ids += rounding_line
            #line.invoce_id = invoice.id
            line.write({'invoice_id': invoice.id})
            new_invoices.append(invoice.id)
            lineas = []
            line_dict = {}

        if context['open_invoices']:
            return {
                'domain': [('id', 'in', new_invoices)],
                'name': 'Invoices',
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'account.invoice',
                'view_id': False,
                'views': [(self.env.ref('account.invoice_supplier_tree').id, 'tree'),
                          (self.env.ref('account.invoice_supplier_form').id, 'form')],
                'context': "{'type':'in_invoice'}",
                'type': 'ir.actions.act_window'
            }
            # return {
            #     'domain': [('id', 'in', invoice.ids)],
            #     'name': 'Invoices',
            #     'view_type': 'form',
            #     'view_mode': 'tree,form',
            #     'res_model': 'account.invoice',
            #     'view_id': False,
            #     'views': [(self.env.ref('account.invoice_tree').id, 'tree'), (self.env.ref('account.invoice_form').id, 'form')],
            #     'context': "{'type':'out_invoice'}",
            #     'type': 'ir.actions.act_window'
            # }
        else:
            return {'type': 'ir.actions.act_window_close'}



class FleetVehicleAssignationLog(models.Model):
    _inherit = "fleet.vehicle.assignation.log"
    _order = "date_start"

    driver_id = fields.Many2one('hr.employee', string="Chofer", required=True)
