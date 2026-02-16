from odoo import models, fields, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    ott_url = fields.Char(string='OTT URL', config_parameter='ott.url_ott')
    ott_user = fields.Char(string='OTT user', config_parameter='ott.user_ott')
    ott_password = fields.Char(string='OTT password', config_parameter='ott.password_ott')
    #ott_price_min = fields.Float(string='Precio mínimo de plan', config_parameter='ott.price_min_ott')
    ott_password_redirect_url = fields.Char(
        'URL de redirección para reset password', config_parameter='ott.ott_password_redirect_url')

    datafast_url = fields.Char(string='Datafast URL', config_parameter='ott.url_datafast', help='eu-test.oppwa.com')
    datafast_entityId = fields.Char(string='Datafast Entity ID', config_parameter='ott.entityId_datafast', help='token de empresa')
    datafast_mid = fields.Char(string='Datafast MID', config_parameter='ott.mid_datafast')
    datafast_tid = fields.Char(string='Datafast TID', config_parameter='ott.tid_datafast')
    datafast_eci = fields.Char(string='Datafast ECI', config_parameter='ott.eci_datafast')
    datafast_auth = fields.Char(string='Datafast AUTH', config_parameter='ott.auth_datafast')
    datafast_test_mode = fields.Boolean(string='Test Mode', config_parameter='ott.test_mode_datafast')

    placetopay_url = fields.Char(string='Placetopay URL', config_parameter='ott.placetopay.url')
    placetopay_login = fields.Char(string='Placetopay Login', config_parameter='ott.placetopay.login')
    placetopay_secret = fields.Char(string='Placetopay Secret', config_parameter='ott.placetopay.secret')
    placetopay_question = fields.Char(string='Placetopay Preguntas', config_parameter='ott.placetopay.question')
