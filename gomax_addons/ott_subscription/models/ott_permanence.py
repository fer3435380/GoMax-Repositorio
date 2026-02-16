from odoo import models, fields, api

class OTTPermanence(models.Model):
    _name = 'ott.permanence'
    _description = 'OTT Permanence'
    _rec_name = 'permanence_name'

    permanence_name = fields.Char('Name', required=True)
    permanence_duration = fields.Integer('Duration', required=True)
    permanence_type = fields.Selection([('days', 'Days'), ('months', 'Months'), ('fixed_date', 'Fixed Date')], 'Type', required=True)