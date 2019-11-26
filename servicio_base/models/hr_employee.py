# -*- coding: utf-8 -*-
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)
import ipdb


class HrJob(models.Model):
    _inherit = 'hr.job'
    
    @api.multi
    @api.depends('name', 'x_studio_categora_mtss')
    def name_get(self):
        return [(rec.id, '%s - %s' % (rec.name, rec.x_studio_categora_mtss)) for rec in self]


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    hr_employee_id = fields.Many2one('hr.employee', 'Empleado', ondelete='cascade')




class AdmonitionType(models.Model):
    _name = 'admonition.type'
    _description = 'Tipo de Amonestación'

    name = fields.Char(string='Tipo')



class HrEmployeeVehicles(models.Model):
    _name = 'hr.employee.vehicles'
    _description = "Vehiculos del Empleado"

    hr_employee_id = fields.Many2one(comodel_name='hr.employee', string='Empleado', ondelete="cascade")
    name = fields.Char()
    attachment = fields.Many2many('ir.attachment')
    license_plate = fields.Char(string='Matricula')
    color = fields.Char()

class HrEmployeeAdmonition(models.Model):
    _name = 'hr.employee.admonition'
    _description = "Amonestaciónes"

    date_start = fields.Date('Fecha Inicio')
    date_end = fields.Date('Fecha FIn')
    hr_employee_id = fields.Many2one(comodel_name='hr.employee', string='Empleado', ondelete="cascade")
    admonition_type_id = fields.Many2one(comodel_name='admonition.type', string='Tipo')
    attachment = fields.Many2many('ir.attachment')


class HrEmployeeFamily(models.Model):
    _name = 'hr.employee.family'
    _description = 'Familiares del Empleado'

    name = fields.Char(string='Nombre')
    document = fields.Char(string='Documento')
    date_of_birth = fields.Date(string='Fecha de Nacimiento')
    relation_id = fields.Many2one('emergency.contact.relation', string='Parentezco')
    in_charge = fields.Selection([('si','Si'),('no','No')], string='¿A cargo?')
    hr_employee_id = fields.Many2one('hr.employee', 'Empleado', ondelete='cascade')


class EmergencyContactRelation(models.Model):
    _name = 'emergency.contact.relation'
    _description = 'Parentezco del Contacto'

    name = fields.Char(string='Nombre')



class EmergencyContact(models.Model):
    _name = 'emergency.contact'
    _description = 'Contactos de Emergencia'

    name = fields.Char(string='Nombre')
    relation_id = fields.Many2one('emergency.contact.relation', string='Parentezco')
    cel = fields.Char(string='Telefono')
    hr_employee_id = fields.Many2one('hr.employee', 'Empleado', ondelete='cascade')


class HrEmployeeAddressExt(models.Model):
    _name = 'hr.employee.address.ext'
    _description = 'Direcciones de Empleados'

    name = fields.Char('Nombre')
    country_id = fields.Many2one('res.country', 'País', ondelete='restrict')
    state_id = fields.Many2one("res.country.state", 'Departamento', ondelete='restrict')
    city_id = fields.Many2one('res.country.city', 'Ciudad')
    street = fields.Char('Calle')
    street2 = fields.Char('Esquina')
    hr_employee_id = fields.Many2one('hr.employee', 'Empleado', ondelete='cascade')

class HrMutalist(models.Model):
    _name = 'hr.mutalist'
    _description = 'Mutualista'

    name = fields.Char(string='Name')


class HrEmergency(models.Model):
    _name = 'hr.emergency'
    _description = 'Emergencia Médica'

    name = fields.Char(string='Name')


class HrAlergies(models.Model):
    _name = 'hr.alergies'
    _description = 'Alergias'

    name = fields.Char(string='Name')
    hr_employee_id = fields.Many2one('hr.employee', 'Empleado', ondelete='cascade')


class DocumentType(models.Model):
    _name = 'document.type'
    _description = 'Tipo de Documento'

    name = fields.Char(string='Tipo')


class HrEmplyeeDocuments(models.Model):
    _name = 'hr.emplyee.documents'
    _description = "Documentos del empleado"

    date = fields.Date('Fecha Vencimiento')
    hr_employee_id = fields.Many2one(comodel_name='hr.employee', string='Empleado', ondelete="cascade")
    document_type_id = fields.Many2one(comodel_name='document.type', string='Tipo de Documento')
    attachment = fields.Many2many('ir.attachment')
    name = fields.Integer('Número')


class HrEmployee(models.Model):
    _inherit = "hr.employee"
    _rec_name = 'name_gen'

    @api.depends('first_name', 'second_name', 'first_surname', 'second_surname')
    @api.onchange('first_name', 'second_name', 'first_surname', 'second_surname')
    def _generate_name(self):
        res = ""
        for rec in self:
            res += rec.first_name + " " if rec.first_name else ""
            res += rec.second_name + " " if rec.second_name else ""
            res += rec.first_surname + " " if rec.first_surname else ""
            res += rec.second_surname + " " if rec.second_surname else ""
            rec.name_gen = res
            rec.name = res

    name_gen = fields.Char(string="Nombre autogenerado")
    first_name = fields.Char(string="Primer Nombre", required=True)
    second_name = fields.Char(string="Segundo Nombre", size=20)
    first_surname = fields.Char(string="Primer Apellido" ,size=20, required=True)
    second_surname = fields.Char(string="Segundo Apeliido", size=20)

    address_ext_ids = fields.One2many('hr.employee.address.ext', 'hr_employee_id', u'Dirección')
    mutualist_id = fields.Many2one('hr.mutalist', string='Mutualista')
    emergency_id = fields.Many2one('hr.emergency', string='Emergencia')
    alergies_ids = fields.One2many('hr.alergies', 'hr_employee_id', string='Alergias')
    emergency_contacs_ids = fields.One2many('emergency.contact', 'hr_employee_id', 'Contactos de Emergencia')
    bank_account_ids = fields.One2many('res.partner.bank', 'hr_employee_id', string='Bancos')
    telfono_personal = fields.Char(string='Teléfono Personal')


    cedula_identidad = fields.Binary(string='Cedula de Identidad')
    cedula_identidad_vencimiento = fields.Date(string='Vencimiento')
    libreta_conducir = fields.Binary(string='Libreta de conducir')
    libreta_conducir_vencimiento = fields.Date(string='Vencimiento')
    carnet_salud = fields.Binary(string='Carné de salud')
    carnet_salud_vencimiento = fields.Date(string='Vencimiento')
    cargas_pesadas = fields.Binary(string='Cargas Pesadas')
    cargas_pesadas_vencimiento = fields.Date(string='Vencimiento')
    formulario_dgi = fields.Binary(string='Formulario 3100', help='Formulario 3100 para alta DGI')
    formulario_dgi_vencimiento = fields.Date(string='Vencimiento')
    formulario_snis = fields.Binary(string='Formulario SNIS', help='Formulario SNIS para alta BPS')
    formulario_snis_vencimiento = fields.Date(string='Vencimiento')
    acceso_puerto = fields.Binary(string='Acceso a puerto')
    acceso_puerto_vencimiento = fields.Date(string='Vencimiento')
    hr_employee_family_ids = fields.One2many('hr.employee.family', 'hr_employee_id', string='Familiares')
    hr_employee_document_ids = fields.One2many('hr.emplyee.documents', 'hr_employee_id', string='Documentos')
    hr_employee_admonition_ids = fields.One2many('hr.employee.admonition', 'hr_employee_id', string='Amonestaciónes')
    hr_employee_vehicles_ids = fields.One2many('hr.employee.vehicles', 'hr_employee_id', string='Vehiculo del Empleado')
    revisa_cargas = fields.Boolean()
    revisa_costos = fields.Boolean()
    revisa_comisiones = fields.Boolean(string='Revisor reportes viajes')


