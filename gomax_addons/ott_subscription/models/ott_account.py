import logging
import string
import random

from odoo import models, fields, api
from .ott_hardware import OTTHardware

_logger = logging.getLogger(__name__)


class OTTAccount(models.Model):
    _name = "ott.account"
    _description = "OTT Account"
    _rec_name = "ott_account_email"

    ott_account_email  = fields.Char(string = "Mail OTT")
    ott_account_password = fields.Char(string="Password OTT")
    ott_account_user_id = fields.Char(string="OTT User ID")
    ott_account_partner = fields.Integer(string="Sequence Partner")

    @api.model
    def create(self, vals):
        seq_value = self.env['ir.sequence'].next_by_code('res.partner.code') or '9999999'
        _logger.info(f"VALOR OBTENIDO DE LA SECUENCIA: {seq_value}")

        forced_id = int(seq_value)

        vals['ott_account_partner'] = forced_id

        record = super(OTTAccount, self).create(vals)
        return record
    
    def _generate_provisional_password(self, length=15):
        chars = string.ascii_letters + string.digits
        return ''.join(random.choice(chars) for _ in range(length))
    
    def gather_ott_account(self):
        self.ensure_one()
        ott_hardware = OTTHardware(self.env)
        account = self
        email = account.ott_account_email
        result = ott_hardware.find_user({'login':email})
        _logger.info(f"++++++++++++++++++\n{result}")

        vals_to_write = {}
        ott_id = False

        if result.get('status') != 1:

            temp_password = self._generate_provisional_password()

            result = ott_hardware.register_user({
                'id': account.ott_account_partner,
                'email':account.ott_account_email,
                'login': account.ott_account_email,
                'password': temp_password,
            })

            ott_id = result.get('id') or result.get('userId')

            _logger.info("OTT: Creación de usuarios: %s, %s, %s" % (account.ott_account_email, temp_password, ott_id))

            vals_to_write['ott_account_password'] = temp_password
            vals_to_write['ott_account_user_id'] = ott_id
            
        else:
            ott_id = result.get('id') or result.get('userId')

            if self.ott_account_user_id != str(ott_id):
                vals_to_write['ott_account_user_id'] = ott_id
        
        if vals_to_write and ott_id:
            self.write(vals_to_write)
            _logger.info("OTT: Base de Datos Odoo actualizada para %s: %s" %(email, vals_to_write))

            
        return ott_id
    

