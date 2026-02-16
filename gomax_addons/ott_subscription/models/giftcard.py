import random
import string
from odoo import api, models, fields
from odoo.exceptions import UserError


class GiftCard(models.Model):
    _name = "gift.card"
    _description = "Giftcard individual"

    code = fields.Char(string="Código", readonly=True, copy=False)
    code_display = fields.Char(string="Código (vis.)", compute="_compute_code_display")

    state = fields.Boolean('Activada ?', default=False, readonly=True)
    #issue_date = fields.Date(default=fields.Date.today)
    #expiration_date = fields.Date()

    template_id = fields.Many2one(
        "gift.template",
        string="Plantilla asociada",
        required=True,
        ondelete="cascade"
    )

    #lista calculada de franquicias permitidas
    allowed_franchise_ids = fields.Many2many(
        'ott.franchise',
        compute='_compute_allowed_franchises',
        string="Franquicias permitidas (interno)",
    )

    franchise_id = fields.Many2one(
        'ott.franchise',
        string="Franquicia asociada",
        required=True,
    )

    sale_order_id = fields.Many2one(
        'sale.order',
        string='Orden de venta',
        readonly=True,
    )

    res_partner = fields.Many2one('res.partner', 'Cliente', readonly=True)

    sale_state = fields.Selection([('draft','Borrador'),
                                   ('sale','Vendida'),
                                   ('active','Activada'),
                                   ('cancel','Cancelado')],
                                  'Estado de venta', default='draft')
    
    rate_template_id = fields.Many2one('ott.rate.template', string="Tarifa de Evento")

    product_id = fields.Many2one(
        'product.product', 
        string="Producto", 
        compute="_compute_product_id", 
        store=True
    )

    @api.depends('template_id')
    def _compute_product_id(self):
        for card in self:
            template = card.template_id
            if template.ott_type_selection == 'event' and template.rate_template_id:
                card.product_id = template.rate_template_id.rate_product
            else:
                card.product_id = template.product_id

    def get_check_giftcard(self, code):
        if not code:
            return {'status': False, 'message': 'Debe enviar un código'}

        code_upper = str(code).upper()

        if code_upper == 'VIVEALMAXIMO':
            code = code_upper

        print('Código recibido para verificación:', code)

        # Buscamos la giftcard por código sin importar el estado
        giftcard_exist = self.search([('code', '=', code)], limit=1)

        if not giftcard_exist:
            # No existe la giftcard
            return {'status': False, 'message': 'La giftcard no existe'}

        #giftcard disponible
        giftcard_available = self.search([
            ('code', '=', code),
            ('state', '=', False),
            ('sale_state', 'in', ['draft', 'sale']),
        ], limit=1)

        if giftcard_available:
            return {
                'status': True,
                'message': 'La giftcard esta disponible',
                'giftcard_code': code,
            }
        
        #giftcard activada
        giftcard_activated = self.search([
            ('code', '=', code),
            ('state', '=', True),
            ('sale_state', 'in', ['active']),
        ], limit=1)

        if giftcard_activated:
            return {
                'status': False,
                'message': 'La giftcard ya fue activada'
            }
        
        #giftcard cancelada
        giftcard_canceled = self.search([
            ('code', '=', code),
            ('state', 'in', [True, False]), 
            ('sale_state', 'in', ['cancel']),
        ], limit=1)

        if giftcard_canceled:
            return {
                'status': False,
                'message': 'La giftcard fue cancelada'
            }


    # ---------------------
    # CÓDIGO GENERADO
    # ---------------------
    @api.model
    def _generate_code(self):
        exclude_chars = "IL10O"
        allowed_chars = [c for c in string.ascii_letters + string.digits if c not in exclude_chars]
        return ''.join(random.choices(allowed_chars, k=6))

    @api.depends('code')
    def _compute_code_display(self):
        for card in self:
            card.code_display = card.code[:3] + '***' if card.code else ''

    # ---------------------
    # CÁLCULO DE FRANQUICIAS PERMITIDAS
    # ---------------------
    @api.depends('template_id')
    def _compute_allowed_franchises(self):
        for rec in self:
            if rec.template_id:
                rec.allowed_franchise_ids = rec.template_id.franchise_ids
            else:
                rec.allowed_franchise_ids = False

    # ---------------------
    # VALIDACIONES CREATE
    # ---------------------
    @api.model
    def create(self, vals):
        template = self.env['gift.template'].browse(vals.get('template_id'))

        # Validar límite
        if template and vals.get('franchise_id'):
            count = self.search_count([
                ('template_id', '=', template.id),
                ('franchise_id', '=', vals['franchise_id']),
            ])
            if count >= template.giftcard_limit:
                raise UserError("Límite alcanzado de giftcards para esta franquicia.")

        # Validar season
        if template and template.season_id and template.season_id.end_date < fields.Date.today():
            raise UserError("La temporada ya finalizó, no se pueden crear giftcards.")

        # Validar franquicia
        if template and vals.get('franchise_id'):
            franchise = self.env['ott.franchise'].browse(vals['franchise_id'])
            if franchise not in template.franchise_ids:
                raise UserError("La franquicia seleccionada no pertenece a esta plantilla.")

        # Generar código
        if not vals.get("code"):
            vals["code"] = self._generate_code()

        return super().create(vals)
