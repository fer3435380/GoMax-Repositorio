from odoo import models, fields, api, _
from odoo.exceptions import AccessError
from odoo import SUPERUSER_ID

class OTTFranchise(models.Model):
    _name = "ott.franchise"
    _description = "Franquicia OTT"
    _rec_name = "franchise_name"

    franchise_name = fields.Char(string="Nombre de la franquicia", required=True)
    franchise_information = fields.Text(string="Información adicional")

    # 1. Separación de productos Base
    allowed_base_product_ids = fields.Many2many(
        'product.product', 
        'ott_franchise_base_prod_rel', # Tabla relacional única
        'franchise_id', 'product_id',
        string='Planes Base Permitidos',
        domain="[('product_tmpl_id.ott_subscription_type', '=', 'base')]"
    )

    # 2. Separación de productos Extra
    allowed_extra_product_ids = fields.Many2many(
        'product.product', 
        'ott_franchise_extra_prod_rel', # Tabla relacional única
        'franchise_id', 'product_id',
        string='Servicios Extra Permitidos',
        domain="[('product_tmpl_id.ott_subscription_type', '=', 'extra')]"
    )

    # 3. Tarifas de Eventos (Usa tu modelo ott.rate.template)
    allowed_rate_ids = fields.Many2many(
        'ott.rate.template', 
        'ott_franchise_rate_template_rel', # Tabla relacional única
        'franchise_id', 'rate_id',
        string='Tarifas de Eventos Permitidas',
        domain="[('rate_state', '=', True)]" # Solo tarifas activas
    )

    # Relación inversa con gift templates (opcional pero útil)
    gift_template_ids = fields.Many2many(
        'gift.template', 
        'gift_template_franchise_rel',  # tabla relacional
        'franchise_id',  # columna que apunta a OTTFranchise
        'template_id',   # columna que apunta a GiftTemplate
        string='Plantillas de Giftcards'
    )
