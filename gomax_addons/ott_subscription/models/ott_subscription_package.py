# -*- coding: utf-8 -*-
import logging

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError, ValidationError
from .ott_hardware import OTTHardware

_logger = logging.getLogger(__name__)

class SubscriptionPackage(models.Model):
    _inherit = 'subscription.package'   

    is_ott_managed = fields.Boolean(
        string='Managed by OTT',
        default=True,
        help='Technical flag that indicates this subscription is handled by the OTT module.'
    )

    ott_reference = fields.Char(
        string='OTT Reference',
        help='Optional reference used by the OTT integration.'
    )

    ott_account_id = fields.Many2one('ott.account', string="OTT Account", required=True)

    # En ott_subscription_package.py
    franchise_id = fields.Many2one('ott.franchise', string='Franquicia')

    # allowed_product_ids = fields.Many2many(
    #     related='franchise_id.allowed_product_ids',
    #     string='Productos Permitidos por Franquicia',
    #     readonly=True
    # )

    event_line_ids = fields.One2many(
        'subscription.package.product.line',
        'subscription_id',
        string="Event Lines",
        domain=[('ott_type', '=', 'event')],
        context={'default_ott_type': 'event'}
    )

    extra_line_ids = fields.One2many(
        'subscription.package.product.line', 
        'subscription_id', 
        string="Extra Lines",
        domain=[('ott_type', '=', 'extra')],
        context={'default_ott_type': 'extra'}
    )

    base_line_ids = fields.One2many(
        'subscription.package.product.line', 
        'subscription_id', 
        string="Subscription Lines",
        domain=[('ott_type', '=', 'base')],
        context={'default_ott_type': 'base'}
    )

    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True)
    amount_untaxed = fields.Monetary(string="Untaxed Amount", compute='_compute_all_totals', store=True, currency_field='currency_id')
    amount_tax = fields.Monetary(string="Taxes", compute='_compute_all_totals', store=True, currency_field='currency_id')
    recurring_total = fields.Monetary(string="Total Recurring", compute='_compute_all_totals', store=True, currency_field='currency_id')

    @api.depends('product_line_ids.price_total', 
                 'base_line_ids.price_total', 
                 'event_line_ids.price_total', 
                 'extra_line_ids.price_total')
    def _compute_all_totals(self):
        for sub in self:
            sub.amount_untaxed = sum(sub.product_line_ids.mapped('total_amount'))
            sub.amount_tax = sum(sub.product_line_ids.mapped('price_tax'))
            sub.recurring_total = sum(sub.product_line_ids.mapped('price_total'))
            
    
    @api.onchange('base_line_ids', 'event_line_ids', 'extra_line_ids', 'product_line_ids')
    def _onchange_lines_recompute_totals(self):
        self._compute_all_totals()
    
    # ott_partner_password = fields.Char(string="Password", required=True)

    @api.model
    def create(self, vals):
        # Si es OTT, genera una referencia automática si no tiene
        if vals.get('is_ott_managed') and not vals.get('ott_reference'):
            partner_id = vals.get('partner_id')
            if partner_id:
                partner = self.env['res.partner'].browse(partner_id)
                if partner and partner.name:
                    vals['ott_reference'] = ('OTT/%s' % partner.name)[:64]
        return super().create(vals)

    def write(self, vals):
        """
        Solo permitir modificar registros OTT para usuarios normales.
        Los no-OTT solo pueden ser modificados por administradores.
        """
        user = self.env.user
        if not user.has_group('base.group_system'):
            for rec in self:
                if not rec.is_ott_managed:
                    raise AccessError(_("Solo el administrador puede modificar suscripciones que no son gestionadas por OTT."))
        return super().write(vals)

    def unlink(self):
        """
        Solo el administrador puede eliminar suscripciones.
        """
        if not self.env.user.has_group('base.group_system'):
            raise AccessError(_("Solo el administrador puede eliminar suscripciones."))
        return super().unlink()
    
    def action_suspend_subscription(self):
        
        records = self.filtered(lambda r: r.current_stage in ['progress'])
        _logger.info(str(records))
        for rec in records:
            response = rec._suspend_ott_user()

            if response['status'] and response['status'] == 1:
                suspended_stage = self.env['subscription.package.stage'].search([('name', '=', 'Suspended')], limit=1)
                records.write({'stage_id': suspended_stage})
            else:
                raise UserError(_("No se pudo suspender la subscripción --%s-- en el sistema externo.")%(rec.reference_code))


    def action_activate_subscription(self):
        records = self.filtered(lambda r: r.current_stage in ['suspend'])
        for rec in records:
            response = rec._unsuspend_ott_user()

            if response['status'] and response['status'] == 1:
                _logger.info(response)
                progress_stage = self.env['subscription.package.stage'].search([('name', '=', 'In Progress')], limit=1)
                if not progress_stage:
                    raise ValueError(_("No existe el estado 'In Progress'."))
                self.write({'stage_id': progress_stage.id})
            else:
                raise UserError(_("No se pudo activar la subscripción --%s-- en el sistema externo.")%(rec.reference_code))


    def button_close(self):
        result = super(SubscriptionPackage, self).button_close()
        closed_stage = self.env['subscription.package.stage'].search([('name', '=', 'Closed')], limit=1)
        ContractLineModel = self.env['subscription.package.product.line']

        if not closed_stage:
            raise ValueError(_("No existe el estado 'Closed'."))
        
        records = self.filtered(lambda r: r.current_stage in ['progress', 'suspend'])
        _logger.info(records)

        for rec in records:
            response = rec._cancel_ott_user()
            _logger.info(response)
            status = response.get('status')

            if status == 1:
                rec.write({'stage_id': closed_stage.id})

                all_lines = rec.product_line_ids

                if all_lines:
                    for line in all_lines:
                        line.state = 'terminated'

            else:
                raise UserError(_("No se pudo cancelar la subscripción --%s-- en el sistema externo.")%(rec.reference_code))
        
        return result


    def send_contract_lines_hardware(self):

        ContractLineModel = self.env['subscription.package.product.line']
        to_activate = []

        for contract in self:
            if contract.stage_category in ['draft', 'progress']:
                all_lines = ContractLineModel.search([
                    ('subscription_id', '=', contract.id),
                    ('state', '=', 'draft')
                ])

                for line in all_lines:
                    ott_data = line.prepare_ott_data()

                    if ott_data:
                        to_activate.append(ott_data)

        if to_activate:
            ContractLineModel._activate_ott_product(to_activate)
        else:
            _logger.info('No hay datos para activar.')

        return True
    
    def _suspend_ott_user(self):
        ott_hardware = OTTHardware(self.env)
        response = ott_hardware.suspend_user({
            'userId': self.ott_account_id.ott_account_user_id
        })

        if response['status'] and response['status'] == 1:
            _logger.info("OTT: Servicio desactivado, usuario: %s\n", 
                        self.ott_account_id.ott_account_email)
        
        _logger.info("OTT: Servicio no desactivado, usuario: %s\n", 
                        self.ott_account_id.ott_account_email)
        return response
        
            

    def _unsuspend_ott_user(self):
        ott_hardware = OTTHardware(self.env)
        response = ott_hardware.unsuspend_user({
            'userId': self.ott_account_id.ott_account_user_id
        })

        if response['status'] and response['status'] == 1:
            _logger.info("OTT: Servicio activado nuevamente, usuario: %s\n", 
                        self.ott_account_id.ott_account_email)
        return response
    
    def _cancel_ott_user(self):
        ott_hardware = OTTHardware(self.env)
        
        response = ott_hardware.remove_user({
            'userId': self.ott_account_id.ott_account_user_id
        })

        if response['status'] and response['status'] == 1:
            _logger.info("OTT: Usuario eliminado: %s" % (self.ott_account_id.ott_account_user_id))
        return response

    
    def button_start_date(self):

        self.send_contract_lines_hardware()

        res = super(SubscriptionPackage, self).button_start_date()

        for rec in self:
           
            if not rec.reference_code:
                continue
           
            new_name = False

            if 'SUB' in rec.reference_code and 'SUB-' not in rec.reference_code:
               new_name = rec.reference_code.replace('SUB', 'SUB-')
            elif 'GIF' in rec.reference_code and 'GIF-' not in rec.reference_code:
               new_name = rec.reference_code.replace('GIFS', 'GIFT-')
            
            if new_name:
               rec.write({'name': new_name})

        return res
    
    def _get_current_base_plan(self, new_ids=None, date_ref=None):
        self.ensure_one()
        if not date_ref:
            date_ref = fields.Date.context_today(self)
        
        SubscriptionLine = self.env['subscription.package.product.line']
        
        base_domain = [
            ('ott_type', '=', 'base'),
            ('subscription_id', '=', self.id),
            ('product_id.product_tmpl_id.ott_subscription_type', '!=', 'extra'),
            ('state', '=', 'open')
        ]
        
        if new_ids:
            base_domain.append(('id', 'not in', new_ids))

        # Intento 1: Planes sin fecha de fin (indefinidos)
        domain1 = base_domain + [('ott_end_date', '=', False)]
        current_plan = SubscriptionLine.search(domain1, order='create_date desc', limit=1)

        # Intento 2: Planes que terminan en el futuro
        if not current_plan:
            domain2 = base_domain + [('ott_end_date', '>', date_ref)]
            current_plan = SubscriptionLine.search(domain2, order='create_date desc', limit=1)

        return current_plan
    

    # # --- INICIO DEL CAMBIO SOLICITADO ---
    # @api.onchange('franchise_id')
    # def _onchange_franchise_id_filter_products(self):
    #     """
    #     Al cambiar la franquicia, forzamos el dominio en la interfaz para
    #     todas las líneas de productos.
    #     """
    #     if self.franchise_id:
    #         # Obtenemos los IDs de los productos permitidos
    #         product_ids = self.franchise_id.allowed_product_ids.ids
            
    #         # Definimos el dominio para los campos Many2one dentro de los One2many
    #         domain = [('id', 'in', product_ids)]
            
    #         return {
    #             'domain': {
    #                 'base_line_ids.product_id': domain,
    #                 'event_line_ids.product_id': domain,
    #                 'extra_line_ids.product_id': domain,
    #                 'product_line_ids.product_id': domain,
    #             }
    #         }


    # Asegúrate de que 'product.product' esté bien escrito
    allowed_base_product_ids = fields.Many2many(
        related='franchise_id.allowed_base_product_ids',
        string='Planes Base Permitidos',
        readonly=True
    )

    allowed_extra_product_ids = fields.Many2many(
        related='franchise_id.allowed_extra_product_ids',
        string='Servicios Extra Permitidos',
        readonly=True
    )

    allowed_rate_ids = fields.Many2many(
        related='franchise_id.allowed_rate_ids',
        string='Tarifas Permitidas',
        readonly=True
    )

    @api.onchange('franchise_id')
    def _onchange_franchise_id_clear_lines(self):
        if self.franchise_id:
            # Esto limpia las líneas si se cambia la franquicia para evitar inconsistencias
            self.base_line_ids = [(5, 0, 0)]
            self.extra_line_ids = [(5, 0, 0)]
            self.event_line_ids = [(5, 0, 0)]
    
    def action_add_new_services(self):
        self.ensure_one()
        if self.stage_category != 'progress':
            raise UserError(_("Solo se pueden agregar servicios en contratos en Progreso."))
        
        self.send_contract_lines_hardware()
        self._compute_all_totals()

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
            'params': {
                'title': _('Actualización Exitosa'),
                'message': _('Los nuevos servicios han sido activados'),
                'type': 'success',
                'sticky': False,
            }
        }
    
    @api.constrains('ott_account_id', 'stage_category')
    def _check_unique_active_contract(self):
        for sub in self:
            active_stages = ['progress', 'suspend']

            if sub.stage_category not in active_stages:
                pass

            domain = [
                ('ott_account_id', '=', sub.ott_account_id.id),
                ('id', '!=', sub.id),
                ('stage_category', 'in', active_stages)
            ]

            existing_contracts = self.search(domain)

            if existing_contracts:

                email_ott = sub.ott_account_id.ott_account_email or "Desconocido"

                contract_name = existing_contracts[0].reference_code
                raise ValidationError(_(
                    "El usuario OTT %s ya tiene un contrato activo (%s)."
                    "\nNo se permite tener multiples contratos activos simultáneamente."
                    "\nPor favor, agregue los nuevos servicios al contrato existente."
                ) % (email_ott, contract_name))
            
    @api.model
    def _cron_close_empty_contracts(self):
        active_contracts = self.search([
            ('stage_category', '=', 'progress')
        ])

        for sub in active_contracts:
                has_active_base = any(l.state == 'open' for l in sub.base_line_ids)
                has_active_extra = any(l.state == 'open' for l in sub.extra_line_ids)
                has_active_event = any(l.state == ' open' for l in sub.event_line_ids)

                if not(has_active_base or has_active_extra or has_active_event):
                    try:
                        _logger.info(f"Cron Cierre: El contrato {sub.name} no tiene líneas activas. Cerrando....")
                        sub.button_close()
                        
                    except Exception as e:
                        _logger.error(f"Error al cerrar contrato vacío {sub.id}: {str(e)}")

                _logger.info(f"Cron Cierre Automático: Se cerraron los contratos vacíos.")
            
