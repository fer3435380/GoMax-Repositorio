from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    ott_subscription_type = fields.Selection(
        [('base', 'Base'), ('event', 'Evento'), ('extra', 'Extra')],
        string='OTT Tipo de Producto',
    )

    service = fields.Many2many('ott.service','product_service_rel', 'product_id', 'service_id', 'Servicios OTT')
    
    rank_ott = fields.Integer('Rango OTT')
    web_product = fields.Boolean('Visible en Portal GoMax', default=False)

    # --- Nuevas variables para la tabla comparativa ---
    
    # Se usa Integer para poder mostrar el número exacto (ej. 80, 100, 120)
    channel_count = fields.Integer(string='Número de Canales')    
    
    # Cantidad de dispositivos al mismo tiempo
    simultaneous_screens = fields.Integer(string='Pantallas en Simultáneo')

    # Horas de contenido que el usuario puede guardar
    recording_hours = fields.Integer(string='Horas de Grabación')
    
    # Para "Eventos que incluye" y "Extras", como suelen ser textos cortos 
    included_events = fields.Char(string='Eventos que Incluye')

    # (ej. "Mundialito de los pobres", "ECDF"), usamos Char.
    ott_extras = fields.Char(string='Extras')