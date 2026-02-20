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

    def write(self, vals):
        # 1. Guardamos los cambios normalmente
        res = super(ResUsers, self).write(vals)
        
        # 2. LA MAGIA: Si en los cambios se modificó tu campo de franquicias...
        if 'allowed_franchises' in vals:
            # Destruimos la caché de las reglas de seguridad
            self.env['ir.rule'].clear_caches()
            # Destruimos la caché de la memoria RAM del ORM (para limpiar las vistas)
            self.clear_caches()
            
        return res
