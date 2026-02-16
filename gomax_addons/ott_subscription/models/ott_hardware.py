import json 
import requests
import logging

from requests.auth import HTTPBasicAuth
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class OTTHardware(object):
    env = None

    def __new__(cls, env=None):
        if env:
            cls.env = env
        obj = super(OTTHardware, cls).__new__(cls)
        return obj
    
    def send_function(self, function, method, params=False):
        base_url = self.env['ir.config_parameter'].sudo().get_param('ott.url_ott')
        username = self.env['ir.config_parameter'].sudo().get_param('ott.user_ott')
        password = self.env['ir.config_parameter'].sudo().get_param('ott.password_ott')

        if not base_url or not username or not password:
            _logger.warning("OTT Hardware: Faltan parámentros de configuración.")
            return None
        url = base_url + function
        auth = HTTPBasicAuth(username, password)

        try:
            if params:
                if method == 'POST':
                    response = requests.post(url, params=params, auth=auth)
                    return json.loads(response.text)
            else:
                response = requests.get(url, auth=auth)
                return response
        except Exception as e:
            _logger.error("OTT Hardware: Error de conexión: {e}")
            return None
    
    def find_user(self, params):
        method = 'POST'
        function = 'find-user'
        parameters = {
            'login': params['login']
        }

        return self.send_function(function=function, method=method, params= parameters)

    def register_user(self, params):
        method = 'POST'
        function = 'register-user'
        parameters = {
            'partnerid': params['id'],
            'email': params['email'],
            'login': params['email'],
            'userPassword': params['password'],
        }

        response = self.send_function(function=function, method=method, params=parameters)

        if response['status'] and response['status'] == 1:
            return response
        
        message = "Error en el registro del usuario: %s" % (str(response))
        _logger.error(message)
        raise UserError(message)

    def modify_user(self, params):
        method = 'POST'
        function = 'modifyuser'
        parameters = {
            'userId': params['userId'],
            'userPassword': params['password'],
            'email': params['email'],
            'login': params['email']
        }

        response = self.send_function(function=function, method=method, params=parameters)

        if response['status'] and response['status'] == 1:
            return response
        
        message = "Error en la modificación del usuario: %s" %(str(response))
        _logger.error(message)
        raise UserError(message)
    
    def remove_user(self, params):
        method = 'POST'
        function = 'remove-user'
        parameters = {
            'userId': params['userId']
        }

        response = self.send_function(function=function, method=method, params=parameters)
        return response
    
    def suspend_user(self, params):
        method = 'POST'
        function = 'suspend-user'
        parameters = {
            'userId': params['userId']
        }
        
        response = self.send_function(function=function, method=method, params=parameters)
        return response

    def unsuspend_user(self, params):
        method = 'POST'
        function = 'unsuspend-user'
        parameters = {
            'userId': params['userId']
        }

        response = self.send_function(function=function, method=method, params=parameters)
        return response
    
    def get_user(self, params):
        method = 'POST'
        function = 'get-user'
        parameters = {
            'userId': params['userId']
        }

        response = self.send_function(function=function, method=method, params=parameters)
        return response
    
    def activate_user(self, params):
        method = 'POST'
        function = 'activate-user'
        parameters = {
            'partnerid': params['partnerid'],
            'userId': params['userId'],
            'services': params.get('service')
        }

        if params.get('date_start'):
            parameters['from'] = params['date_start']
        if params.get('date_end'):
            parameters['to'] = parameters['date_end']
        
        response = self.send_function(function=function, method=method, params=parameters)

        if response['status'] and response['status'] == 1:
            return response
        
        message = 'Error en la activación del usuario: %s' % (str(response))
        _logger.error(message)
        raise UserError(message)
    
    def deactivate_user(self, params):
        method = 'POST'
        function = 'deactivate-user'
        parameters = {
            'partnerid': params['partnerid'],
            'userId': params['userId'],
            'services': params['service'],
            'to': params['date_end'],
            'all': params['all']
        }

        response = self.send_function(function=function, method=method, params=parameters)
        if response['status'] and response['status'] == 1:
            return response
        
        message = 'Error en desactivar el usuario: %s' % (str(response))
        _logger.error(message)
        raise UserError(message)


    def get_user_services(self, params):
        method = 'POST'
        function = 'get-user-services'
        parameters = {
            'userId': params['userId']
        }
        
        response = self.send_function(function=function, method=method, params=parameters)
        
        if response['status'] and response['status'] == 1:
            return response
        
        message = 'Error en la activación de servicios: %s', (str(response))
        _logger.error(message)
        raise UserError(message)
    

    
    def get_pricelist(self):
        method = 'GET'
        function = 'get-pricelist'

        response = self.send_function(function=function, method=method)

        if not response:
            return {'pricelist': []}
        
        try:
            return response.json()
        except Exception as e:
            _logger.error("OTT Hardware: Error al leer JSON de pricelist: {e}")
            return {'pricelist': []}
    
    def activate_services(self, params):
        method = 'POST'
        function='activate-services'
        parameters = {
            'partnerid': str(params['partnerId']),
            # 'userId': params['ott_id'],
            'services': params.get('service'),
        }

        if params.get('date_start'):
            parameters['from'] = params['date_start'].strftime('%Y-%m-%d')
        
        if params.get('date_end'):
            parameters['to'] = params['date_end'].strftime('%Y-%m-%d')

        response = self.send_function(function=function, method=method, params=parameters)

        if response['status'] and response['status'] == 1:
            return response
        
        message = 'Error en la activación de servicio: %s'% (str(response))

        _logger.error(message)
        raise UserError(message)
    
    def deactivate_services(self, params):
        method = 'POST'
        function = 'deactivate-services'
        parameters = {
            'partnerid': params['partnerid'],
            'userId': params['ott_id'],
            'services': params['service'],
            'to': params['date_end']
        }

        response = self.send_function(function=function, method=method, params=parameters)

        if response['status'] and response['status'] == 1:
            return response
        
        message = "Error en al desactivación de servicios: %s" % (str(response))
        _logger.error(message) 
        raise UserError(message)
    