from odoo.exceptions import UserError, ValidationError
from odoo import models, fields, api
from dateutil.relativedelta import relativedelta

class GiftTemplate(models.Model):
    _name = "gift.template"
    _description = "Plantilla de Giftcard"

    name = fields.Char(string="Nombre de la plantilla", required=True)
    description = fields.Text(string="Descripción")

    franchise_ids = fields.Many2many(
        'ott.franchise', 
        'gift_template_ott_franchise_rel', 
        'gift_template_id', 
        'ott_franchise_id',
        string="Franquicias asociadas"
    )

    base_product_ids = fields.Many2many(
        'product.product', 'gift_template_base_rel', 
        'template_id', 'product_id', string="Planes Base"
    )
    extra_product_ids = fields.Many2many(
        'product.product', 'gift_template_extra_rel', 
        'template_id', 'product_id', string="Servicios Extras"
    )
    rate_template_ids = fields.Many2many(
        'ott.rate.template', 'gift_template_rate_rel', 
        'template_id', 'rate_id', string="Tarifas de Evento"
    )

    # CAMPOS TÉCNICOS DE FILTRADO (Mantener los que calculan por franquicia)
    allowed_base_ids = fields.Many2many('product.product', compute="_compute_allowed_fields")
    allowed_extra_ids = fields.Many2many('product.product', compute="_compute_allowed_fields")
    allowed_event_ids = fields.Many2many('ott.rate.template', compute="_compute_allowed_fields")

    @api.depends('franchise_ids')
    def _compute_allowed_fields(self):
        for rec in self:
            base, extra, event = [], [], []
            for franchise in rec.franchise_ids:
                base.extend(franchise.allowed_base_product_ids.ids)
                extra.extend(franchise.allowed_extra_product_ids.ids)
                event.extend(franchise.allowed_rate_ids.ids)
            rec.allowed_base_ids = [(6, 0, list(set(base)))]
            rec.allowed_extra_ids = [(6, 0, list(set(extra)))]
            rec.allowed_event_ids = [(6, 0, list(set(event)))]

    # Mantenemos los campos de datos
    product_ids = fields.Many2many(
        "product.product", 'gift_template_product_rel',
        'template_id', 'product_id', string="Productos"
    )

    @api.constrains('base_product_ids', 'extra_product_ids', 'rate_template_ids')
    def _check_selection(self):
        for rec in self:
            if not rec.base_product_ids and not rec.extra_product_ids and not rec.rate_template_ids:
                raise ValidationError("La plantilla debe tener al menos un plan base, un servicio extra o un evento.")

    # --- Resto de campos originales ---
    season_id = fields.Many2one("season.gift", string="Temporada", ondelete="cascade")
    giftcard_limit = fields.Integer(string="Cantidad de Giftcards", required=True, default=1)
    permanence_id = fields.Many2one('ott.permanence', string="Duración")
    start_date = fields.Date(string="Fecha inicio", required=True)
    end_date = fields.Date(string="Fecha fin", compute="_compute_end_date", store=True, readonly=False)

    @api.depends('start_date', 'permanence_id')
    def _compute_end_date(self):
        for rec in self:
            p = rec.permanence_id
            if not p or not rec.start_date:
                rec.end_date = False
                continue
            if p.permanence_type == 'fixed_date':
                continue
            if p.permanence_type == 'days':
                rec.end_date = rec.start_date + relativedelta(days=p.permanence_duration)
            elif p.permanence_type == 'months':
                rec.end_date = rec.start_date + relativedelta(months=p.permanence_duration)