from odoo import models, fields
from odoo import http
from odoo.http import request, Response

class OTTBackgroundHome(models.Model):
    _name = 'ott.background.home'
    _description = 'OTT Background Home'

    title = fields.Char('title')
    state = fields.Boolean('state', default=True)
    image_file = fields.Image(
        "Background Image", 
        max_width=1920, 
        max_height=1920, 
        required=True)
    
    image_filename = fields.Char("File Name")

    def get_background(self):
        backgrounds = self.search([('state','=', True)])
        result = []

        for bg in backgrounds:
            raw_image = bg.image_file
            final_url = ""

            if raw_image:
                if isinstance(raw_image, bytes):
                    img_str = raw_image.decode('utf-8')
                else:
                    img_str = raw_image

                final_url = f"{img_str}"

            result.append({
                'title': bg.title,
                'state': bg.state,
                'image': final_url, 
            })
        
        return result