import logging

from .ott_hardware import OTTHardware as oh
from odoo import models, fields, api


_logger = logging.getLogger(__name__)

class OTTService(models.Model):
    _name = 'ott.service'
    _description = 'OTT Service'

    @api.model
    def _selection_services(self):
        selection = []

        try:
            command = oh(self.env)
            json_response = command.get_pricelist()
            dicts = json_response.get('pricelist', [])
            
            for item in dicts:
                code = item.get('code')

                if code:
                    ott_tuple = (code, code)
                    selection.append(ott_tuple)
                    
        except Exception as e:
            _logger.error("OTT Service: Error al obtener la lista de servicios: %s" % (e))
            return []
            
        return selection
    
    service = fields.Selection(_selection_services, 'Servicio Hardware')
    description = fields.Char('Description')