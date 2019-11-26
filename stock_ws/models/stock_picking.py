# -*- coding: utf-8 -*-

from odoo import models, fields, api
from suds import WebFault
from suds.client import Client
from io import StringIO, BytesIO
import tempfile
import base64
import lxml.etree as et
from odoo.exceptions import UserError
import ipdb
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
import time
import datetime

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def genera_xml_firma(self):
        fch = time.strptime(self.date_done.strftime(DEFAULT_SERVER_DATE_FORMAT), DEFAULT_SERVER_DATE_FORMAT)
        fecha = "%4d-%02d-%02d" % (fch.tm_year, fch.tm_mon, fch.tm_mday)
        xml_firma = '<?xml version="1.0" encoding="UTF-8"?>\n'
        xml_firma += '<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:tem="http://tempuri.org/">\n'
        xml_firma += '   <soapenv:Header />\n'
        xml_firma += '   <soapenv:Body>\n'
        xml_firma += '      <tem:CrearRemito>\n'
        # xml_firma += '         <tem:IDCliente>prueba</tem:IDCliente>\n'
        # xml_firma += '         <tem:IdEmpresa>prueba</tem:IdEmpresa>\n'
        xml_firma += '         <tem:remito>\n'
        # xml_firma += '            <tem:Serie>prueba</tem:Serie>\n'
        xml_firma += '            <tem:Numero>10</tem:Numero>\n'
        xml_firma += '            <tem:Fecha>%s</tem:Fecha>\n' % '2019-08-15T00:00:00.000-03:00'
        xml_firma += '            <tem:DepoOrigenID>10</tem:DepoOrigenID>\n'
        xml_firma += '            <tem:DepoDestinoID>10</tem:DepoDestinoID>\n'
        xml_firma += '            <tem:Observaciones>prueba</tem:Observaciones>\n'
        xml_firma += '            <tem:LineasRemito>\n'
        xml_firma += '               <tem:LineaRemito>\n'
        # xml_firma += '                  <tem:Articulo>prueba</tem:Articulo>\n'
        xml_firma += '                  <tem:Cantidad>1</tem:Cantidad>\n'
        xml_firma += '               </tem:LineaRemito>\n'
        xml_firma += '            </tem:LineasRemito>\n'
        xml_firma += '         </tem:remito>\n'
        xml_firma += '         <tem:idTipoDocumento>10</tem:idTipoDocumento>\n'
        xml_firma += '      </tem:CrearRemito>\n'
        xml_firma += '   </soapenv:Body>\n'
        xml_firma += '</soapenv:Envelope>\n'

        return xml_firma

    @api.multi
    def action_send_pick(self):
        url_firmar = 'http://srv01.real2b.com:20501/IPointWSTest.asmx?WSDL'
        try:
            client = Client(url_firmar)
        except:
            raise UserError(u'¡ No se pudo conectar !''\n' u'Intente más tarde.')
        # xml_firma = self.genera_xml_firma()
        docargs = {
                'doc_ids': [self.id],
                'doc_model': 'stock.picking',
                'docs': self,
                }

        nombre_vista = 'stock_ws.CrearRemito'
        view = self.env.ref(nombre_vista)
        xml_firma = view.render_template(nombre_vista, docargs)
        now = datetime.datetime.now()

        sign_result = client.service.CrearRemito(xml_firma)
        return