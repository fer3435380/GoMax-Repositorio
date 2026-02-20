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
        # 1. LEER BODY DE POSTMAN
        data = request.httprequest.get_json()
        giftcard_code = data.get('giftcard_code')
        ott_email = data.get('email') # Este correo solo será para el servicio OTT

        if not giftcard_code or not ott_email:
            raise BadRequest("Debe enviar giftcard_code y email en el body")

        GiftCard = request.env['gift.card']
        Subscription = request.env['subscription.package']
        Plan = request.env['subscription.package.plan']
        SubscriptionLine = request.env['subscription.package.product.line']
        OTTAccount = request.env['ott.account']

        # 2. BUSCAR GIFTCARD EN ODOO
        giftcard = GiftCard.sudo().search([('code', '=', giftcard_code)], limit=1)
        if not giftcard:
            return {'status': False, 'message': 'La giftcard no existe'}

        # ---------------------------------------------------------
        # 3. EXTRAER EL CLIENTE DE LA ORDEN DE VENTA (El dueño legal)
        # ---------------------------------------------------------
        partner_suscripcion = giftcard.sale_order_id.partner_id
        
        if not partner_suscripcion:
            return {'status': False, 'message': 'La orden de venta de esta giftcard no tiene un cliente asignado.'}

        if giftcard.sale_state == 'cancel':
            return {'status': False, 'message': 'Esta giftcard pertenece a una orden cancelada y no puede ser utilizada.'}

        if giftcard.state:
            return {'status': False, 'message': 'La giftcard ya está activa'}

        today = fields.Date.context_today(request.env.user)
        if giftcard.template_id.end_date and giftcard.template_id.end_date < today:
            return {'status': False, 'message': 'El código es válido, pero la promoción de esta giftcard ya ha caducado.'}
        
        ott_account = OTTAccount.sudo().search([('ott_account_email', '=', ott_email)], limit=1)

        active_subs = Subscription.sudo().search([
            ('ott_account_id.ott_account_email', '=', ott_email),
            ('stage_id.name', '=', 'In Progress')
        ])
        if active_subs:
            return {'status': False, 'message': 'El usuario ya posee una suscripción activa'}

        default_plan = Plan.sudo().search([], limit=1)
        if not default_plan:
            return {'status': False, 'message': 'No existen planes para crear la suscripción'}

        # ---------------------------------------------------------
        # 4. GESTIONAR LA CUENTA OTT CON EL CORREO DE POSTMAN
        # ---------------------------------------------------------

        if not ott_account:
            ott_account = OTTAccount.sudo().create({
                'ott_account_email': ott_email,
                'ott_account_password': 'provisional_password'
            })
        
        try:
            ott_account.sudo().gather_ott_account()
        except Exception as e:
            _logger.warning(f"Error preventivo en sincronización OTT: {str(e)}")

        # ---------------------------------------------------------
        # 5. CREAR LA SUSCRIPCIÓN UNITARIA
        # ---------------------------------------------------------
        try:
            subscription = Subscription.sudo().create({
                'partner_id': partner_suscripcion.id, # -> Se asigna al cliente de la orden
                'plan_id': default_plan.id,
                'franchise_id': giftcard.franchise_id.id,
                'is_ott_managed': True,
                'reference_code': f"GIF{giftcard.sale_order_id.name}",
                'ott_account_id': ott_account.id,     # -> Se asigna la cuenta OTT de Postman
                'ott_reference': f'OTT/{ott_email}'[:64],
            })
            
            # Heredar combo de la orden
            order_lines = giftcard.sale_order_id.order_line.filtered(lambda l: l.ott_type in ['base', 'extra', 'event'])
            
            if not order_lines:
                raise Exception("La orden de venta de la giftcard no tiene productos válidos.")

            for line in order_lines:

                if line.rate_template_id.rate_type == "normal":
                    SubscriptionLine.sudo().create({
                        'subscription_id': subscription.id,
                        'product_id': line.product_id.id,
                        'product_qty': line.product_uom_qty,
                        'unit_price': line.price_unit, 
                        'ott_start_date': today,
                        'ott_type': line.ott_type,
                        'ott_permanence': line.ott_permanence.id,
                        'rate_template_id': line.rate_template_id.id if line.rate_template_id else False,
                    })
                elif line.rate_template_id.rate_type == "special":
                    SubscriptionLine.sudo().create({
                        'subscription_id': subscription.id,
                        'product_id': line.product_id.id,
                        'product_qty': line.product_uom_qty,
                        'unit_price': line.price_unit, 
                        'ott_start_date': line.rate_template_id.rate_start_date,
                        'ott_end_date': line.rate_template_id.rate_end_date,
                        'ott_type': line.ott_type,
                        'ott_permanence': line.ott_permanence.id,
                        'rate_template_id': line.rate_template_id.id if line.rate_template_id else False,
                    })
                else:
                    SubscriptionLine.sudo().create({
                        'subscription_id': subscription.id,
                        'product_id': line.product_id.id,
                        'product_qty': line.product_uom_qty,
                        'unit_price': line.price_unit, 
                        'ott_start_date': today,
                        'ott_type': line.ott_type,
                        'ott_permanence': line.ott_permanence.id,
                        'rate_template_id': line.rate_template_id.id if line.rate_template_id else False,
                    })

            if hasattr(subscription, 'action_confirm'):
                subscription.sudo().action_confirm()
            
            if hasattr(subscription, 'button_start_date'):
                subscription.sudo().button_start_date()

            giftcard.sudo().write({
                'state': True,
                'sale_state': 'active',
                'res_partner': partner_suscripcion.id
            })

            # Retorno adaptado para ver la confirmación de ambas partes
            return {
                'status': True,
                'message': 'Giftcard activada y suscripción creada exitosamente',
                'subscription_id': subscription.id,
                'cliente_facturacion_id': partner_suscripcion.id, # El que pagó (Odoo)
                'ott_email_activado': ott_email,                  # El que se conectó (Postman)
                'giftcard_code': giftcard.code,
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
    