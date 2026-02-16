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
        'gift_template_ott_franchise_rel', # La tabla que ya existe
        'gift_template_id', 
        'ott_franchise_id',
        string="Franquicias asociadas"
    )

    ott_type_selection = fields.Selection([
        ('base', 'Base'),
        ('event', 'Evento'),
        ('extra', 'Extra')
    ], string="Tipo de Producto", required=True, default='base')

    # Producto para Base y Extra (ya no es requerido siempre)
    product_id = fields.Many2one(
        "product.product", 
        string="Producto", 
        compute="_compute_product_id", 
        store=True, 
        readonly=False,
        ondelete="cascade",
        domain="[('product_tmpl_id.ott_subscription_type', '=', ott_type_selection)]"
    )

    @api.depends('ott_type_selection', 'rate_template_id')
    def _compute_product_id(self):
        for rec in self:
            if rec.ott_type_selection == 'event' and rec.rate_template_id:
                # Si es evento, extrae el producto de la tarifa automáticamente
                rec.product_id = rec.rate_template_id.rate_product
            elif rec.ott_type_selection != 'event' and not rec.product_id:
                # Si no es evento y está vacío, lo dejamos así para que el usuario elija
                rec.product_id = False
                
    # Rate Template exclusivo para Eventos
    rate_template_id = fields.Many2one(
        'ott.rate.template', string="Tarifa de Evento",
        domain="[('rate_state', '=', True)]"
    )

    # Validar que se elija uno u otro según el tipo
    @api.constrains('ott_type_selection', 'product_id', 'rate_template_id')
    def _check_selection(self):
        for rec in self:
            if rec.ott_type_selection == 'event' and not rec.rate_template_id:
                raise ValidationError("Para un evento debe seleccionar una Tarifa (Rate Template).")
            if rec.ott_type_selection in ['base', 'extra'] and not rec.product_id:
                raise ValidationError("Debe seleccionar un producto.")
            

    season_id = fields.Many2one("season.gift", string="Temporada", ondelete="cascade")
    giftcard_limit = fields.Integer(string="Cantidad de Giftcards", required=True, default=1)

    permanence_id = fields.Many2one('ott.permanence', string="Duración")

    start_date = fields.Date(string="Fecha inicio", required=True)

    end_date = fields.Date(
        string="Fecha fin",
        compute="_compute_end_date",
        store=True,
        readonly=False  # se deja False para que el XML controle si es editable o no
    )

    @api.depends('start_date', 'permanence_id')
    def _compute_end_date(self):
        for rec in self:
            p = rec.permanence_id

            # Sin permanencia o sin fecha inicio → limpiar end_date
            if not p or not rec.start_date:
                rec.end_date = False
                continue

            # Si es fixed_date → no calcular, usuario define manualmente
            if p.permanence_type == 'fixed_date':
                if not rec.end_date:
                    rec.end_date = False
                continue

            # Si es days o months → calcular automáticamente
            if p.permanence_type == 'days':
                rec.end_date = rec.start_date + relativedelta(days=p.permanence_duration)
            elif p.permanence_type == 'months':
                rec.end_date = rec.start_date + relativedelta(months=p.permanence_duration)
            else:
                rec.end_date = False
