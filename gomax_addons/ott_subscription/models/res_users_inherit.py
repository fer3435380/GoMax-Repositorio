from odoo import models, fields

class ResUsers(models.Model):
    _inherit = 'res.users'

    allowed_franchises = fields.Many2many(
        'ott.franchise',
        'user_ott_franchise_rel',  # nombre de la tabla intermedia
        'user_id',                 # columna que referencia a res.users
        'franchise_id',            # columna que referencia a ott.franchise
        string='Franquicias Permitidas'
    )
