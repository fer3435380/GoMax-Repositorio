from odoo import models, fields

class OTTRecomProgramming(models.Model):
    _name = 'ott.recommended.programming'
    _description = 'Programacion recomendada'

    title = fields.Char('title')
    description = fields.Char('description')
    state = fields.Boolean('state', default=False)
    image_file = fields.Image(
        "Recom Programming Image", 
        max_width=1920, 
        max_height=1920, 
        required=True)
    
    image_filename = fields.Char("File Name")

    def get_active_programming_data(self):
        programmings = self.search([('state', '=', True)])
        result = []

        for prg in programmings:
            raw_image = prg.image_file
            final_image = ""

            if raw_image:
                if isinstance(raw_image, bytes):
                    final_image = raw_image.decode('utf-8')
                else:
                    final_image = raw_image

            result.append({
                'title': prg.title,
                'description': prg.description,
                'state': prg.state,
                'logo': final_image,
            })

        return result
