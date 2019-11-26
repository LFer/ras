# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
import odoo.addons.decimal_precision as dp
import ipdb

tipos_operativa = [
    ('impo_nat', 'IMPO Nacional'),
    ('impo_inter', 'IMPO Internacional'),
    ('expo_nat', 'EXPO Nacional'),
    ('expo_inter', 'EXPO Internacional'),
    ('transit_nat', 'Transito Nacional'),
    ('transit_inter', 'Transito Internacional'),
    ('interno_plaza_nat', 'Interno Plaza Nacional'),
    ('interno_fiscal_nat', 'Interno Fiscal Nacional'),

]

class Pricelist(models.Model):
    _inherit = "product.pricelist"
    _description = "Pricelist"
    _order = "sequence asc, id desc"

    def _get_default_item_ids(self):
        ProductPricelistItem = self.env['product.pricelist.item']
        vals = ProductPricelistItem.default_get(list(ProductPricelistItem._fields))
        vals.update(compute_price='fixed')
        return [[0, False, vals]]
        #return False

    #item_ids = fields.One2many('product.pricelist.item', 'pricelist_id', 'Pricelist Items', copy=True, default=_get_default_item_ids)
    item_ids = fields.One2many('product.pricelist.item', 'pricelist_id', 'Pricelist Items', copy=True)
    country_ids = fields.Many2many('res.partner')
    es_generica = fields.Boolean(string='Tarifa Generica')
    partner_id = fields.Many2one(comodel_name='res.partner', string='Cliente')



class ProductPricelistItem(models.Model):
    _inherit = "product.pricelist.item"
    _description = "Pricelist Item"
    _order = "applied_on, min_quantity desc, categ_id desc, id"
    _rec_name = "nombre"

    name = fields.Char(
        'Name', compute='_get_pricelist_item_name_price',
        help="Explicit rule name for this pricelist line.")

    nombre = fields.Char(string='Nombre')

    partner_id = fields.Many2one(comodel_name='res.partner', string='Cliente')
    currency_id = fields.Many2one(comodel_name='res.currency', string='Currency', readonly=False)
    active = fields.Boolean(string='Activo', default=True)
    regimen = fields.Selection(tipos_operativa, string="Regimen")
    load_type = fields.Selection([('bulk', 'Bulk'), ('contenedor', 'Contenedor'), ('horas', u'Horas')], string='Tipo de Carga')
    horas_espera = fields.Selection([('si', 'Si'), ('no', 'No')], string='Horas de Espera')
    horas_libres = fields.Float(string='Horas Libres')
    sale_price = fields.Float(string='Precio de Venta')
    comision_chofer = fields.Float(string='Comisión Chofer')
    comision_vendedor = fields.Float(string='Comisión Vendedor')
    container_size = fields.Float(string='Tamaño de Contenedor')
    kg_from = fields.Float(string='Hasta Kg')
    kg_to = fields.Float(string='Peso desde Kg')
    volumen_desde = fields.Float(string='Volumen Desde')
    volumen_hasta = fields.Float(string='Volumen Hasta')
    pcurrency_id = fields.Many2one(comodel_name='res.currency', string='Moneda')

    #Campos Nuevos
    sequence = fields.Integer('Secuencia',
                              required=True,
                              help="Da el orden en que se verifican los elementos de la lista de precios."
                                   " La evaluación otorga la mayor prioridad a la secuencia más baja y se detiene"
                                   " tan pronto como se encuentra un elemento coincidente.",
                              default=0)
    hours_from = fields.Float('Hours From')
    hours_to = fields.Float('Hours To')
    wage_from = fields.Float('Wage From')
    wage_to = fields.Float('Wage To')
    mt3_from = fields.Float('MT3 From')
    mt3_to = fields.Float('MT3 To')
    size_from = fields.Float('Size From')
    size_to = fields.Float('Size To')
    wait_hours_currency_id = fields.Many2one('res.currency', 'Moneda')
    wait_hours_from = fields.Float("Waiting hours From")
    wait_hours_to = fields.Float("Horas Libres")
    package_from = fields.Float('Bultos Desde')
    package_to = fields.Float('Bultos Hasta')
    wait_value = fields.Float("Value of Wait Time")
    origin_dir = fields.Many2one(comodel_name='res.partner.address.ext',  string='Origen', ondelete='restrict')
    destiny_dir = fields.Many2one(comodel_name='res.partner.address.ext',  string='Destino', ondelete='restrict')
    km_from = fields.Float('Km From')
    km_to = fields.Float('Km To')
    description = fields.Text('Additional information')
    comision_vendedor_currency_id = fields.Many2one('res.currency', 'Moneda')
    comision_chofer_currency_id = fields.Many2one('res.currency', 'Moneda')
    aduana_origen_id = fields.Many2one('fronteras', 'Aduana Origen')
    aduana_destino_id = fields.Many2one('fronteras', 'Aduana Destino')
    partner_seller_id = fields.Many2one(comodel_name='res.partner', string='Vendedor', domain=[('seller', '=', True)])
    action_type_id = fields.Many2one('tipo.accion', string="Tipo de Acción")
    invoice_int_per = fields.Integer(string='% Tramo Internacional', default=60)
    invoice_nat_per = fields.Integer(string='% Tramo Nacional', default=40)
    product_id = fields.Many2one(comodel_name='product.product', string='Servicio', domain=[('product_tmpl_id.type', '=', 'service'), ('sale_ok', '=', True)], required=False, change_default=True, ondelete='restrict')
    expenses_ids = fields.One2many('default.expenses', 'pricelist_item_parent_id', string='Productos Asociados', copy=True)
    productos_asociados_ids = fields.One2many('default.expenses', 'pricelist_parent_id', string='Productos Asociados', copy=True)

    #Almacenaje por periodo por tiempo
    recurring_rule_count = fields.Integer(string="End After", default=1)
    recurring_rule_type = fields.Selection([('daily', 'Dia(s)'), ('weekly', 'Semana(l)'),
                                            ('monthly', 'Mes(es)'), ('yearly', 'Año(s)'), ],
                                           string='Recurrencia', required=True,
                                           help="Invoice automatically repeat at specified interval",
                                           default='monthly', track_visibility='onchange')
    recurring_interval = fields.Integer(string="Repetir a cada", help="Repeat every (Days/Week/Month/Year)", required=True, default=1, track_visibility='onchange')
    recurring_rule_type_readonly = fields.Selection(
        string="Recurrence Unit",
        related='recurring_rule_type', readonly=True, track_visibility=False)

    recurring_rule_boundary = fields.Selection([('unlimited', 'Forever'), ('limited', 'Fixed')], string='Duration', default='unlimited')
    load_presentation = fields.Many2one(comodel_name='catalogo.tipo.bulto', string=u'Unidad')


    @api.one
    @api.depends('categ_id', 'product_tmpl_id', 'product_id', 'compute_price', 'fixed_price', \
        'pricelist_id', 'percent_price', 'price_discount', 'price_surcharge')
    def _get_pricelist_item_name_price(self):
        if self.categ_id:
            self.name = _("Category: %s") % (self.categ_id.name)
        elif self.product_tmpl_id:
            self.name = self.product_tmpl_id.name
        elif self.product_id:
            self.name = self.product_id.display_name.replace('[%s]' % self.product_id.code, '')
        else:
            self.name = _("All Products")

        if self.compute_price == 'fixed':
            self.price = ("%s %s") % (self.fixed_price, self.pricelist_id.currency_id.name)
        elif self.compute_price == 'percentage':
            self.price = _("%s %% discount") % (self.percent_price)
        else:
            self.price = _("%s %% discount and %s surcharge") % (self.price_discount, self.price_surcharge)
        self.name = self.nombre
    @api.onchange('regimen')
    def _onchange_product_id(self):
        res = {}
        domain = {}
        address_obj = self.env['res.partner.address.ext']
        partner_id = self.partner_id.id
        address_type = 'load'
        if self.regimen in ('impo_nat','impo_inter'):
            destiny_addrs = address_obj.search([('partner_id', '=', partner_id), ('address_type', '=', address_type)])
            if len(destiny_addrs) > 1:
                destiny = destiny_addrs.ids
                domain = {'destiny_dir': [('id', 'in', destiny)]}

        if self.regimen in ('expo_nat', 'expo_inter'):
            origin_addrs = address_obj.search([('partner_id', '=', partner_id), ('address_type', '=', address_type)])
            if len(origin_addrs) > 1:
                origin = origin_addrs.ids
                domain = {'origin_dir': [('id', 'in', origin)]}

        if domain:
            res['domain'] = domain

        return res

    @api.multi
    @api.depends('name', 'sequence')
    def name_get(self):
        return [(rec.id, '%s - %s' % (rec.sequence, rec.name)) for rec in self]

    @api.multi
    def write(self, vals):
        res = super(ProductPricelistItem, self).write(vals)
        # self._toggle_create_website_menus(vals)
        return res

    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        recs = self.browse()
        recs = self.search(['|',('nombre', operator, name), ('sequence', operator, name)] + args, limit=limit)
        return recs.name_get()