# -*- coding: utf-8 -*-
import json, logging, requests
from odoo import http, api, exceptions, fields
from odoo.http import request, Response
from werkzeug.exceptions import BadRequest

_logger = logging.getLogger(__name__)
class OTTController(http.Controller):

    #busca el codigo de la giftcard
    @http.route('/ott/get_check_giftcard', type='json', auth='api_key', methods=['POST'], csrf=False)
    def get_check_giftcard(self, **kwargs):
        try:
            # Leer JSON manualmente
            body = json.loads(request.httprequest.data.decode('utf-8'))

            code = body.get('code')
            if not code:
                return {
                    'status': False,
                    'message': 'Debe enviar un código'
                }

            OTTGiftCard = request.env['gift.card']
            return OTTGiftCard.get_check_giftcard(code)

        except Exception as e:
            return {
                'status': False,
                'message': f'Error: {str(e)}'
            }



    @http.route('/ott/create_giftcard_partner', type='json', auth='api_key', methods=['POST'], csrf=False)
    def create_giftcard_partner(self, **kw):
        print('create_giftcard_partner')
        env = request.env
        Partner = env['res.partner']
        Country = env['res.country']
        OTTGiftCard = env['gift.card']

        country_ec = Country.search([('code', '=', 'EC')], limit=1)
        partner_data = request.httprequest.get_json()

        email = partner_data.get('email')
        name = partner_data.get('name')
        second_name = partner_data.get('second_name')
        giftcard_code = partner_data.get('giftcard_code')

        # Validación de campos obligatorios
        if not email or not name:
            raise BadRequest('El nombre y el correo son obligatorios')

        # Buscar giftcard disponible
        giftcard = OTTGiftCard.search([('code', '=', giftcard_code), ('state', '=', False)], limit=1)
        if not giftcard:
            return {'status': False, 'message': 'La giftcard no existe o ya fue activada'}

        # Buscar partner existente
        existing_partner = Partner.search([('email', '=', email)], limit=1)

        try:
            if existing_partner and giftcard:
                # Buscar todas las suscripciones del partner
                subscriptions = env['subscription.package'].search([('partner_id', '=', existing_partner.id)])

                # Contar suscripciones activas (In Progress)
                active_subscriptions = subscriptions.filtered(lambda s: s.stage_id.name == 'In Progress')

                # Partner ya tiene una suscripción activa
                if active_subscriptions:
                    return {'status': False, 'message': 'Este usuario ya posee una cuenta activa.'}

                # Buscar partner sin suscripción (equivalente a partner_without_contract)
                partner_without_subscription = Partner.search([
                    ('id', 'not in', env['subscription.package'].search([]).mapped('partner_id.id')),
                    ('email', '=', email)
                ])

                # Si no hay contrato activo, pero existe partner
                if len(partner_without_subscription) > 0 or subscriptions.filtered(lambda s: s.stage_id.name in ['Draft', 'Closed']):
                    # Validar campos opcionales del body (si existen)
                    fields = [name, email]
                    for field in fields:
                        if not field:
                            raise BadRequest('Request Incorrecto')

                    # Eliminar giftcard_code del diccionario para retornar solo datos del partner
                    del partner_data['giftcard_code']

                    return {
                        'partner_id': existing_partner.id,
                        'partner': partner_data,
                        'giftcard_code': giftcard_code
                    }

            elif giftcard:
                fields = [name, email]
                for field in fields:
                    if not field:
                        raise BadRequest('Request Incorrecto')

                # Crear partner
                partner = Partner.create({
                    'name': name,
                    'email': email,
                    'country_id': country_ec.id if country_ec else False,
                })

                # Eliminamos giftcard_code del diccionario
                del partner_data['giftcard_code']

                return {
                    'partner_id': partner.id,
                    'giftcard_code': giftcard_code
                }
            
            else:
                return {'status':False, 'message': "error"}
        except Exception as e:
            return {'status': False, 'message': str(e)}


    @http.route('/ott/activate_giftcard', type='json', auth='api_key', methods=['POST'], csrf=False)
    def activate_giftcard(self, **kw):
        data = request.httprequest.get_json()

        giftcard_code = data.get('giftcard_code')
        email = data.get('email')
        name = data.get('name')

        if not giftcard_code or not email:
            raise BadRequest("Debe enviar giftcard_code y email")

        Partner = request.env['res.partner']
        GiftCard = request.env['gift.card']
        Subscription = request.env['subscription.package']
        Plan = request.env['subscription.package.plan']
        SubscriptionLine = request.env['subscription.package.product.line']
        OTTAccount = request.env['ott.account']

        # 1. Buscar o crear partner
        partner = Partner.sudo().search([('email', '=', email)], limit=1)
        if not partner:
            partner = Partner.sudo().create({'name': name or email, 'email': email})

        # 2. Buscar giftcard
        giftcard = GiftCard.sudo().search([('code', '=', giftcard_code)], limit=1)
        if not giftcard:
            return {'status': False, 'message': 'La giftcard no existe'}

        if giftcard.state:
            return {'status': False, 'message': 'La giftcard ya está activa'}

        # 3. Validar suscripciones activas
        active_subs = Subscription.sudo().search([
            ('partner_id', '=', partner.id),
            ('stage_id.name', '=', 'In Progress')
        ])
        if active_subs:
            return {'status': False, 'message': 'El usuario ya posee una suscripción activa'}

        # 4. Obtener plan por defecto
        default_plan = Plan.sudo().search([], limit=1)
        if not default_plan:
            return {'status': False, 'message': 'No existen planes para crear la suscripción'}

        # 5. Gestionar Cuenta OTT
        ott_account = OTTAccount.sudo().search([('ott_account_email', '=', email)], limit=1)
        if not ott_account:
            ott_account = OTTAccount.sudo().create({
                'ott_account_email': email,
                'ott_account_password': 'provisional_password'
            })
        
        # Sincronización con hardware (con manejo de errores para evitar cortes)
        try:
            ott_account.sudo().gather_ott_account()
        except Exception as e:
            _logger.warning(f"Error preventivo en sincronización OTT: {str(e)}")

        # 6. Obtener producto y tarifa directamente de la giftcard (YA CARGADOS DESDE LA ORDEN)
        # Usamos el product_id que calculamos en el modelo gift.card
        product = giftcard.product_id 
        rate_template = giftcard.rate_template_id

        if not product:
            return {'status': False, 'message': 'La giftcard no tiene un producto vinculado'}
        
        # Identificamos el tipo desde la plantilla
        ott_type = giftcard.template_id.ott_type_selection or 'base'

        # 7. Crear la suscripción
        try:
            subscription_vals = {
                'partner_id': partner.id,
                'plan_id': default_plan.id,
                'franchise_id': giftcard.franchise_id.id,
                'is_ott_managed': True,
                'ott_account_id': ott_account.id,
                'ott_reference': f'OTT/{partner.name}'[:64],
            }

            subscription = Subscription.sudo().create(subscription_vals)
            
            # 8. Crear línea de suscripción
            line_vals = {
                'subscription_id': subscription.id,
                'product_id': product.id,
                'product_qty': 1,
                'unit_price': product.list_price,
                'ott_start_date': fields.Date.context_today(request.env.user),
                'ott_type': ott_type,
                'rate_template_id': rate_template.id if rate_template else False,
            }
            
            SubscriptionLine.sudo().create(line_vals)

            # Confirmar suscripción si existe el método
            if hasattr(subscription, 'action_confirm'):
                subscription.sudo().action_confirm()
            
            subscription.sudo().button_start_date()

            # 10. Activar giftcard
            giftcard.sudo().write({
                'state': True,
                'sale_state': 'active',
                'res_partner': partner.id
            })

            return {
                'status': True,
                'message': f'Giftcard de tipo {ott_type} activada exitosamente',
                'subscription_id': subscription.id,
                'partner_id': partner.id,
                'partner_email': partner.email,
                'giftcard_code': giftcard.code,
                'plan_id': default_plan.id
            }

        except Exception as e:
            request.env.cr.rollback()
            return {'status': False, 'message': f"Error en la activación: {str(e)}"}
        
    @http.route('/ott/products', type='http', auth='api_key', methods=['GET'], csrf=False)
    def get_products(self, **kw):
        print('get_products')

        partner_id = None
        if kw.get('partner_id'):
            partner_id = int(kw.get('partner_id'))

        Product = request.env['product.product']

        result = Product.get_ott_products(partner_id=partner_id)

        # MISMO ordenamiento
        for k in result.keys():
            l_ord = sorted(
                result[k],
                key=lambda x: x['rank_product']
            )
            result[k] = [x for x in l_ord]

        # MISMA respuesta
        response = request.make_response(json.dumps(result), [
                ('Content-Type', 'application/manifest+json'),
        ])

        return response

    @http.route('/ott/recom_programming', type='http', auth='api_key', methods=['GET'], csrf=False)
    def get_recom_programming(self, **kw):
        print('get_recom_programming')
        result = request.env['ott.recommended.programming'].sudo().get_active_programming_data()
        return request.make_response(json.dumps(result), [
            ('Content-Type', 'application/json'),
        ])

    @http.route('/ott/get_partner', type='http', auth='api_key', methods=['GET'])
    def get_partner(self, **kw):
        _logger.info('get_partner')
        partner = None

        try:
            pid = int(kw.get('partner_id'))
            partner = request.env['res.partner'].search([('id', '=', pid)], limit=1)
        except Exception as e:
            _logger.error(f'Error al buscar partner: {str(e)}')
            return request.make_response(json.dumps({
                'status': False,
                'message': f'Error al buscar partner: {str(e)}'}),
                [('Content-Type', 'application/json')])
        
        if partner:
            partner_data = {
                'partner_id': partner.id,
                'country_id': partner.country_id.id if partner.country_id else None,
                'name': partner.name if partner.name else '',
                'vat': partner.vat if partner.vat else '',
                'street': partner.street if partner.street else '',
                'email': partner.email if partner.email else '',
                'phone': partner.phone if partner.phone else None,
                'mobile': partner.mobile if partner.mobile else None,
                'middleware_password': partner.middleware_password if partner.middleware_password else '',
            }
            response = request.make_response(json.dumps(partner_data),
                                             [('Content-Type', 'application/manifest+json'),
                                              ])
            return response
        else:
            return request.make_response(json.dumps({
                'status': False, 
                'message': f'Usuario con ID {kw.get("partner_id")} no encontrado'}), 
                [('Content-Type', 'application/json')])
        
    @http.route('/ott/get_background_home', type='http', auth='api_key', methods=['GET'])
    def get_background_home(self, **kw):

        result = request.env['ott.background.home'].sudo().get_background()
        return request.make_response(json.dumps(result),
                                     [('Content-Type', 'application/manifest+json'),
                                      ])
    
    @http.route('/ott/get_active_channels', type='http', auth='api_key', methods=['GET'])
    def get_active_channels(self, **kw):
        result = request.env['ott.channel'].sudo().get_active_channels()
        return request.make_response(json.dumps(result),
                                     [('Content-Type', 'application/manifest+json'),
                                    ])
    