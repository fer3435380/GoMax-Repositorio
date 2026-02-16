import logging

from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = "sale.order"

    is_giftcard = fields.Boolean(string="Es orden de giftcard", default=False)
    gift_template_id = fields.Many2one('gift.template', string='Plantilla de Giftcard')
    franchise_id = fields.Many2one('ott.franchise', string='Franquicia')

    # Intersección: Franquicias de la Plantilla vs Franquicias del Usuario
    allowed_franchise_ids = fields.Many2many(
        'ott.franchise', 
        compute='_compute_allowed_franchise_ids'
    )

    # 2. Este NUEVO campo calculará qué PLANTILLAS pertenecen a la franquicia elegida
    allowed_gift_template_ids = fields.Many2many(
        'gift.template',
        compute='_compute_allowed_gift_template_ids'
    )

    @api.depends('is_giftcard')
    def _compute_allowed_franchise_ids(self):
        for order in self:
            # Filtramos solo las franquicias que el usuario tiene asignadas en su perfil
            order.allowed_franchise_ids = self.env.user.allowed_franchises

    @api.depends('franchise_id')
    def _compute_allowed_gift_template_ids(self):
        for order in self:
            if order.franchise_id:
                # Buscamos plantillas que tengan esta franquicia en su Many2many (franchise_ids)
                templates = self.env['gift.template'].search([
                    ('franchise_ids', 'in', order.franchise_id.id)
                ])
                order.allowed_gift_template_ids = templates
            else:
                # Si no hay franquicia, no mostramos plantillas (o todas, según prefieras)
                order.allowed_gift_template_ids = self.env['gift.template'].browse()

    @api.onchange('franchise_id')
    def _onchange_franchise_id_clear_template(self):
        """Si cambia la franquicia, borramos la plantilla seleccionada anteriormente."""
        if self.franchise_id:
            self.gift_template_id = False           

    @api.constrains('gift_template_id', 'franchise_id', 'is_giftcard')
    def _check_giftcard_validations(self):
        for order in self:
            if not order.is_giftcard:
                continue
            
            # Solo validamos si ya intentamos seleccionar algo
            if order.franchise_id and order.franchise_id not in order.allowed_franchise_ids:
                raise ValidationError(f"La franquicia {order.franchise_id.franchise_name} no está en su lista de permitidas.")
            
            # Validación cruzada: La plantilla debe pertenecer a la franquicia
            if order.gift_template_id and order.franchise_id:
                if order.franchise_id not in order.gift_template_id.franchise_ids:
                    raise ValidationError("La plantilla seleccionada no está disponible para esta franquicia.")

    def _get_gift_template_data(self, template):
        """Retorna producto, precio, rate_template_id y display_name."""
        product = template.product_id
        price = product.lst_price
        rate_id = False
        display_name = product.name

        if template.ott_type_selection == 'event' and template.rate_template_id:
            rate = template.rate_template_id
            product = rate.rate_product
            price = rate.rate_price
            rate_id = rate.id
            display_name = rate.rate_name
            
        return product, price, rate_id, display_name

    @api.onchange('gift_template_id')
    def _onchange_gift_template_id(self):
        for order in self:
            if order.gift_template_id:
                product, price, rate_id, name = self._get_gift_template_data(order.gift_template_id)
                if product:
                    order.order_line = [(5, 0, 0)]
                    order.order_line = [(0, 0, {
                        'product_id': product.id,
                        'name': name, 
                        'product_uom_qty': 1,
                        'price_unit': price,
                        'rate_template_id': rate_id,
                        'tax_id': [(6, 0, product.taxes_id.ids)],
                    })]

    @api.model
    def create(self, vals):
        if vals.get('is_giftcard') and vals.get('gift_template_id'):
            template = self.env['gift.template'].browse(vals['gift_template_id'])
            product, price, rate_id, name = self._get_gift_template_data(template)
            if 'order_line' in vals:
                for line in vals['order_line']:
                    if line[0] == 0:
                        line[2].update({
                            'product_id': product.id,
                            'name': name,
                            'price_unit': price,
                            'rate_template_id': rate_id,
                            'tax_id': [(6, 0, product.taxes_id.ids)]
                        })
        return super(SaleOrder, self).create(vals)

    def write(self, vals):
        res = super(SaleOrder, self).write(vals)
        if 'gift_template_id' in vals or 'is_giftcard' in vals:
            for order in self:
                if order.is_giftcard and order.gift_template_id:
                    product, price, rate_id, name = self._get_gift_template_data(order.gift_template_id)
                    for line in order.order_line:
                        line.write({
                            'product_id': product.id,
                            'name': name,
                            'price_unit': price,
                            'rate_template_id': rate_id,
                        })
        return res

    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        for order in self:
            if not order.is_giftcard: continue
            for line in order.order_line:
                qty = int(line.product_uom_qty)
                for i in range(qty):
                    self.env['gift.card'].create({
                        'template_id': order.gift_template_id.id,
                        'franchise_id': order.franchise_id.id,
                        'sale_order_id': order.id,
                        'res_partner': order.partner_id.id,
                        'rate_template_id': line.rate_template_id.id if line.rate_template_id else False,
                        'sale_state': 'sale',
                    })
        return res

    def action_cancel(self):
        """Cancela las giftcards asociadas al cancelar la orden."""
        res = super(SaleOrder, self).action_cancel()
        for order in self:
            if order.is_giftcard:
                giftcards = self.env['gift.card'].search([('sale_order_id', '=', order.id)])
                giftcards.write({'sale_state': 'cancel'})
        return res

    def action_create_gift_invoice(self):
        self.ensure_one()
        if not self.gift_template_id or not self.franchise_id:
            raise UserError("Faltan datos obligatorios para facturar.")
        return self.env.ref('sale.action_view_sale_advance_payment_inv').sudo().read()[0]

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"
    rate_template_id = fields.Many2one('ott.rate.template', string="Tarifa de Evento")