import logging

from odoo import models, fields, api
from dateutil.relativedelta import relativedelta
from .ott_hardware import OTTHardware
from datetime import datetime, timedelta
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

class ProductLine(models.Model):
    _inherit = 'subscription.package.product.line'

    subscription_id = fields.Many2one('subscription.package', string="Subscription")
    
    ott_start_date = fields.Date(
        string="Start Date",
        default=fields.Date.context_today,
        required=True,
        store=True)
    
    ott_end_date = fields.Date(
        string="End Date",
        compute='_compute_ott_end_date',
        store=True,
        readonly=True
        )
    
    ott_permanence = fields.Many2one('ott.permanence', string="Permanence", required=True)

    permanence_type = fields.Selection(
        related='ott_permanence.permanence_type',
        string="Permanence Type",
        readonly=True
    )

    state_options = [('draft', 'Draft'),
                     ('open', 'Open'),
                     ('terminated', 'Terminated')]

    state = fields.Selection(
                        selection=state_options,
                        string="State",
                        default="draft",
                        readonly=True,
                        help="Define el estado del modulo")
    
    type_options = [('base', 'Base'),
                     ('event', 'Event'),
                     ('extra', 'Extra')]
    
    ott_type = fields.Selection(
        selection=type_options,
        string = "Type",
        default="base",
        required=True,
        readonly=False,
        store=True,
        help="Define el tipo de subscripción OTT"
    )

    # En ott_product_line.py
    package_franchise_id = fields.Many2one(
        related='subscription_id.franchise_id', 
        string="Franquicia del Paquete",
        store=True
    )

    rate_template_id = fields.Many2one(
        'ott.rate.template',
        string="Events Template",
        domain=[('rate_state','=', True)]
    )

    ott_auto_renew = fields.Boolean(
        string = "Renew",
        default = False,
        required = False,
        help = "Define si el producto va ser de pago recurrente (se renueva cada tiempo de permanencia) o no"
    )

    @api.model_create_multi
    def create(self, vals_list):
        return super(ProductLine, self.sudo()).create(vals_list)

    def write(self, vals):
        return super(ProductLine, self.sudo()).write(vals)

    @api.depends('ott_permanence', 'ott_start_date')
    def _compute_ott_end_date(self):
        for record in self:
            if record.rate_template_id and record.rate_template_id.rate_type == 'special':
                record.ott_end_date = record.rate_template_id.rate_end_date
                continue

            if not record.ott_start_date:
                record.ott_start_date = fields.Date.context_today(record)

            if not record.ott_permanence:
                record.ott_end_date = False
                continue

            duration = record.ott_permanence.permanence_duration
            p_type = record.ott_permanence.permanence_type
            start_date = record.ott_start_date

            if p_type == 'days' and start_date:
                record.ott_end_date = start_date + relativedelta(days=duration)
            elif p_type == 'months' and start_date:
                record.ott_end_date = start_date + relativedelta(months=duration)
            else:
                if not record.ott_end_date:
                    record.ott_end_date = False
        
    def prepare_ott_data(self):
        self.ensure_one()
        result = {
            'partner_id': self.subscription_id.ott_account_id,
            'product_id': self.product_id,
            'start_date': self.ott_start_date,
            'end_date': self.ott_end_date
        }

        _logger.info(result)

        if self.ott_end_date:
            result['ott_end_date'] = self.ott_end_date

        if self.id:
            result['id'] = self.id

        return result

    @api.model
    def _activate_ott_product(self, lines):
        ott_hardware = OTTHardware(self.env)
        for line in lines:
            partner = line['partner_id']
            partner.gather_ott_account()
            product = line['product_id']

            _logger.info(partner)
            
            for service in product.service:
                result = ott_hardware.activate_services({
                    'partnerId': partner.ott_account_partner,
                    'ott_id': partner.ott_account_user_id,
                    'service': service.service,
                    'date_start': line.get('start_date'),
                    'date_end': line.get('end_date'),
                })

                if result and result.get('status') == 1:
                    _logger.info(result)
                else:
                    api_error = result.get('message', 'Error Desconocido')
                    raise UserError(_("No se ha podido activar el producto de manera correcta: %s. \n Detalle: %s") %(service.service, api_error))

            if line.get('id'):
                contract_line = self.browse(line['id'])
                contract_line.state = 'open'

                contract = contract_line.subscription_id
                
                if contract:
                    contract.write({'current_stage': 'progress'})

    @api.depends('product_qty', 'unit_price', 'discount', 'tax_ids',
                 'currency_id', 'ott_permanence', 'ott_start_date', 'ott_end_date')
    def _compute_total_amount(self):
        for line in self:
            base_price = line.unit_price * (1 - (line.discount or 0.0) / 100)
            
            billing_factor = 1.0
            permanence = line.ott_permanence

            if permanence:

                if permanence.permanence_type == 'days' and permanence.permanence_duration:
                    billing_factor = permanence.duration / 30.0

                elif permanence.permanence_type == 'months' and permanence.permanence_duration:
                    billing_factor = float(permanence.permanence_duration)

            final_qty = line.product_qty * billing_factor
            
            taxes = line.tax_ids._origin.compute_all(
                base_price,
                line.subscription_id._origin.currency_id,
                final_qty,
                product=line.product_id,
                partner=line.subscription_id._origin.partner_id
            )

            line.update({
                'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                'price_total': taxes['total_included'],
                'total_amount': taxes['total_excluded'],
            })

    @api.onchange('rate_template_id')
    def _onchange_rate_template_id(self):
        if not self.rate_template_id:
            return
        
        template = self.rate_template_id

        self.product_id = template.rate_product
        self.unit_price = template.rate_price
        self.ott_permanence = template.rate_permanence
        self.ott_start_date = fields.Date.context_today(self)


        if template.rate_type == 'special':
            self.ott_end_date = template.rate_end_date
        
        if self.product_id:
            self.product_uom_id = self.product_id.uom_id
            self.tax_ids = self.product_id.taxes_id
    

    @api.constrains('ott_type', 'rate_template_id', 'product_id')
    def _check_event_requirements(self):
        for line in self:
            if line.ott_type == 'event' and not line.rate_template_id:
                raise ValidationError("Para las líneas de evento, debes seleccionar una Tarifa (Rate Template).")
            
            if line.ott_type in ['base', 'extra'] and not line.product_id:
                raise ValidationError("Las líneas base o extra requieren un producto.")

    @api.model
    def _cron_renew_expiring_lines(self):
        today = fields.Date.context_today(self)

        expiring_lines = self.search([
            ('state', '=', 'open'),
            ('ott_end_date', '<=', today),
            ('subscription_id.stage_category', '=', 'progress'),
            ('ott_type', 'in', ['base', 'extra']),
            ('ott_auto_renew', '=', True),
        ])

        _logger.info("=="*100+f"\nCron Renovación: Encontradas {len(expiring_lines)} lineas venciendo el {today}")

        for line in expiring_lines:
            try:
                new_start_date = line.ott_end_date
                vals = line.copy_data({
                    'ott_start_date': new_start_date,
                    'state': 'draft',
                    'ott_end_date': False,
                })[0]

                new_line = self.create(vals)
                new_line._compute_ott_end_date()
                new_line._compute_total_amount()

                _logger.info(f"Renovación creada: {new_line.id} para contrato {new_line.subscription_id.name}")

                ott_data = new_line.prepare_ott_data()
                self._activate_ott_product([ott_data])
                new_line.state = 'open'
                line.state = 'terminated'

            except Exception as e:
                _logger.error(f"Error al renovar la línea  {line.id}: {str(e)}")
                continue

    @api.model
    def _cron_expire_non_renewing_lines(self):
        today = fields.Date.context_today(self)

        expiring_lines = self.search([
            ('state', '=', 'open'),
            ('ott_end_date', '<=', today),
            ('subscription_id.stage_category', '=', 'progress'),
            '|',
            ('ott_type','=','event'),
            '&',
            ('ott_type', 'in', ['base','extra']),
            ('ott_auto_renew', '=', False)
        ])

        _logger.info(f"Cron Expiración: Encontradas {len(expiring_lines)} lineas para terminar (NO RENOVAR) el {today}")

        for line in expiring_lines:
            try:
                line.state = 'terminated'
                _logger.info(f"Línea terminada correctamente: {line.id} (Tipo: {line.ott_type})")
            except Exception as e:
                _logger.error(f"Error al terminar la línea {line.id}: {str(e)}")

    @api.onchange('product_id', 'product_qty', 'ott_permanence')
    def _onchange_product_id_for_pricelist(self):
        for line in self:
            if not line.product_id:
                continue

            base_price = line.product_id.list_price
            line.unit_price = base_price
            line.discount = 0.0

            billing_factor = 1.0
            permanence = line.ott_permanence
            if permanence:
                if permanence.permanence_type == 'days' and permanence.permanence_duration:
                    billing_factor = permanence.permanence_duration / 30.0
                elif permanence.permanence_type == 'months' and permanence.permanence_duration:
                    billing_factor = float(permanence.permanence_duration)
            
            eval_qty = line.product_qty * billing_factor
            date = line.ott_start_date or fields.Date.context_today(line)
            partner = line.subscription_id.partner_id or self.env.user.partner_id

            user_pricelists = self.env.user.sudo().pricelist_ids
            applied_rule = False
            final_price = base_price

            for pricelist in user_pricelists:
                price, rule_id = pricelist._get_product_price_rule(
                    line.product_id,
                    max(1.0, eval_qty),
                    partner=partner,
                    date=date,
                    uom_id=line.product_id.uom_id
                )
                
                if rule_id:
                    final_price = price
                    applied_rule = self.env['product.pricelist.item'].browse(rule_id)
                    break 

            if applied_rule:
                if applied_rule.compute_price == 'percentage':
                    line.unit_price = base_price
                    line.discount = applied_rule.percent_price
                else:
                    line.unit_price = final_price
                    line.discount = 0.0
            