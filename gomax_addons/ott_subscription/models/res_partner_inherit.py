import logging
import string
import random

from odoo import models, fields, api
from .ott_hardware import OTTHardware

_logger = logging.getLogger(__name__)

class ResPartner(models.Model):
    _inherit = 'res.partner'

    middleware_password = fields.Char(string="Password OTT")
    ott_user_id = fields.Char(string="OTT User ID")


