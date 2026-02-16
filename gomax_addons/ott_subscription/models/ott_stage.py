from odoo import models, fields

class SubscriptionPackageStage(models.Model):
    _inherit = "subscription.package.stage"

    category = fields.Selection(
        selection_add=[('suspend', 'Suspended')],
    )
