from odoo import models, fields

class SeasonGift(models.Model):
    _name = "season.gift"
    _description = "Temporada de Giftcards"

    name = fields.Char(string="Nombre de la temporada", required=True)
    start_date = fields.Date(string="Fecha de inicio", required=True)
    end_date = fields.Date(string="Fecha de fin", required=True)

    # Relación 1 -> N con gift_template
    gift_template_ids = fields.One2many("gift.template", "season_id", string="Plantillas de regalos")
