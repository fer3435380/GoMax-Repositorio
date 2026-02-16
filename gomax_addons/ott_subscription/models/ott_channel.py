from odoo import models, fields
from odoo import http
from odoo.http import request, Response

class OTTChannel(models.Model):
    _name = 'ott.channel'
    _description = 'OTT Channel'
    
    channel_name = fields.Char('Channel Name', required=True)
    channel_code = fields.Char('Channel Code', required=True, unique=True)
    channel_image = fields.Image(
        "Channel Image",
        max_width=1920,
        max_height=1920,
        required=True
    )
    channel_state = fields.Boolean('Active', default=True)
    channel_category = fields.Selection(
        [('national', 'National'), 
         ('international', 'International'),
         ('sports', 'Sports'),
         ('movies', 'Movies'),
         ('series', 'Series'),
         ('kids', 'Kids'),
         ('cultural', 'Cultural')]
    )

    image_filename = fields.Char("Image File Name")

    def get_active_channels(self):
        channels = self.search([('channel_state', '=', True)])
        result = {}

        category_dict = {
        'kids': 'Infantil',
        'movies': 'Películas',
        'sports': 'Deportes',
        'culture': 'Cultural',
        'news': 'Noticias',
        'national': 'Nacionales',
        'music': 'Música',
        'entertainment': 'Entretenimiento',
        'premium': 'Premium',
        }

        for channel in channels:

            if channel.channel_state == False:
                continue
            else:
                raw_image = channel.channel_image
                final_url = ""

                if raw_image:
                    if isinstance(raw_image, bytes):
                        img_str = raw_image.decode('utf-8')
                    else:
                        img_str = raw_image
                    
                    final_url = f"{img_str}"

                channel_data = {
                    'name': channel.channel_name,
                    'code': channel.channel_code,
                    'image': final_url
                }

                category_key = channel.channel_category or 'others'

                category_sp = category_dict.get(category_key, category_key.capitalize())

                result.setdefault(category_sp, []).append(channel_data)

        return result