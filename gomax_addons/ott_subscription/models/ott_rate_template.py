import logging
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta

_logger = logging.getLogger(__name__)


class OTTRateTemplate(models.Model):
    _name = 'ott.rate.template'
    _description = 'Event Rate Template'
    _rec_name = 'rate_name'

    EVENTS_SELECTION = [
        ('special', 'Special Event'), 
        ('normal', 'Normal Event')
    ]

    rate_name = fields.Char(string="Name")
    rate_state = fields.Boolean(string="State", 
                                default=True)
    rate_type = fields.Selection(string="Type of the event", 
                                 selection=EVENTS_SELECTION)

    rate_start_date = fields.Date(string="Start Date", 
                                  default=fields.Date.context_today)
    
    rate_end_date = fields.Date(string="End Date",
                                compute="_compute_rate_end_date",
                                store=True,
                                readonly=False)
    rate_product = fields.Many2one('product.product', 
                                   string="Product",
                                   domain="[('product_tmpl_id.ott_subscription_type', '=', 'event')]")

    rate_permanence = fields.Many2one('ott.permanence', 
                                      string="Permanence",
                                      required=True)
    
    rate_price = fields.Float(string="Price", default=0.0, required=True)

    currency_id = fields.Many2one(
        'res.currency', 
        string="Currency", 
        default=lambda self: self.env.company.currency_id,
        readonly=True
    )
    

    @api.depends('rate_permanence', 'rate_start_date')
    def _compute_rate_end_date(self):
        for record in self:
            if not record.rate_permanence or not record.rate_start_date:
                record.rate_end_date = False
                continue

            if not record.rate_start_date:
                record.rate_start_date = fields.Date.context_today(record)

            if record.rate_permanence:
                duration = record.rate_permanence.permanence_duration
                p_type = record.rate_permanence.permanence_type
                start_date = record.rate_start_date

                if p_type == 'days':
                    record.rate_end_date = start_date + relativedelta(days=duration)
                elif p_type == 'months':
                    record.rate_end_date = start_date + relativedelta(months=duration)
                elif p_type == 'fixed_date':
                    if not record.rate_end_date:
                        record.rate_end_date = False
                    continue
                else:
                    record.rate_end_date = False
    

    @api.onchange('rate_type')
    def _onchange_rate_type(self):
        domain = []

        if self.rate_type == 'special':
            fixed_perm = self.env['ott.permanence'].search([('permanence_type', '=', 'fixed_date')], limit=1)
            self.rate_permanence = fixed_perm
            domain = [('permanence_type', '=', 'fixed_date')]
        else:
            self.rate_permanence = False
            self.rate_start_date = False
            self.rate_end_date = False
            domain = [('permanence_type', '!=', 'fixed_date')]

        return {'domain':{'rate_permanence': domain}}
    
    @api.model
    def _cron_archive_expired_rates(self):
        today = fields.Date.context_today(self)

        expired_records = self.search([
            ('rate_state', '=', True),
            ('rate_end_date', '<', today)
        ])

        if expired_records:
            expired_records.write({'rate_state': False})

            _logger.info(f"Cron OTT: Se ha desactivado {len(expired_records)} tarifas vencidas.")

