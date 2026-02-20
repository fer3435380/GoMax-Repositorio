import logging
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = "sale.order"

    is_giftcard = fields.Boolean(string="Es orden de giftcard", default=False)
    gift_template_id = fields.Many2one('gift.template', string='Plantilla de Giftcard')
    franchise_id = fields.Many2one('ott.franchise', string='Franquicia')

    gift_card_ids = fields.One2many('gift.card', 'sale_order_id', string="Giftcards Generadas")

    base_line_ids = fields.One2many('sale.order.line', 'order_id', string="Líneas Base", domain=[('ott_type', '=', 'base')])
    extra_line_ids = fields.One2many('sale.order.line', 'order_id', string="Líneas Extra", domain=[('ott_type', '=', 'extra')])
    event_line_ids = fields.One2many('sale.order.line', 'order_id', string="Líneas Evento", domain=[('ott_type', '=', 'event')])

    allowed_franchise_ids = fields.Many2many(
        'ott.franchise', 
        compute='_compute_allowed_franchise_ids'
    )

    allowed_gift_template_ids = fields.Many2many(
        'gift.template',
        compute='_compute_allowed_gift_template_ids'
    )

    @api.depends('is_giftcard')
    def _compute_allowed_franchise_ids(self):
        is_manager = self.env.user.has_group('ott_subscription.group_ott_admin')
        for order in self:
            order.allowed_franchise_ids = self.env['ott.franchise'].search([]) if is_manager else self.env.user.allowed_franchises

    @api.depends('franchise_id')
    def _compute_allowed_gift_template_ids(self):
        today = fields.Date.context_today(self)
        for order in self:
            domain = [
                '|', ('end_date', '>=', today), ('end_date', '=', False)
            ]
            
            if order.franchise_id:
                domain.append(('franchise_ids', 'in', order.franchise_id.id))
                order.allowed_gift_template_ids = self.env['gift.template'].search(domain)
            else:
                order.allowed_gift_template_ids = self.env['gift.template'].search(domain) if self.env.user.has_group('ott_subscription.group_ott_gift') else self.env['gift.template'].browse()

    @api.onchange('franchise_id')
    def _onchange_franchise_id_clear_template(self):
        if self.franchise_id:
            self.gift_template_id = False 

    @api.constrains('gift_template_id', 'franchise_id', 'state')
    def _check_giftcard_validations(self):
        today = fields.Date.context_today(self)
        for order in self:
            # 1. Si no hay plantilla, no es una giftcard, ignoramos.
            if not order.gift_template_id:
                continue
                
            # 2. Validación de Vigencia de la Plantilla
            if order.gift_template_id.end_date and order.gift_template_id.end_date < today:
                raise ValidationError(f"La plantilla '{order.gift_template_id.name}' ya caducó el {order.gift_template_id.end_date}. No se puede usar.")
            
            # 3. Validación de Franquicias
            if order.franchise_id:
                if order.franchise_id not in order.allowed_franchise_ids:
                    raise ValidationError(f"La franquicia {order.franchise_id.franchise_name} no está en su lista de permitidas.")
                if order.franchise_id not in order.gift_template_id.franchise_ids:
                    raise ValidationError("La plantilla seleccionada no está disponible para esta franquicia.")
    
    @api.constrains('order_line')
    def _check_lines_permanence(self):
        """
        Bloquea el guardado de la Orden si alguna línea Base o Extra no tiene permanencia.
        """
        for order in self:
            if not order.is_giftcard:
                continue
            
            for line in order.order_line:
                # Si es un plan base o extra y la permanencia está vacía, bloqueamos todo
                if line.ott_type in ['base', 'extra'] and not line.ott_permanence:
                    raise ValidationError(
                        f"¡Alto! Falta asignar la duración (permanencia) para el producto: '{line.product_id.display_name}'. "
                        "Por favor, selecciona una duración en la pestaña correspondiente antes de guardar."
                    )

    def _get_gift_template_data_list(self, template):
        """
        Retorna tres listas independientes para alimentar los campos One2many
        de la Orden de Giftcard de forma aislada.
        """
        # Listas individuales
        base_data = []
        extra_data = []
        event_data = []
        
        common = {
            'ott_permanence': False,
            'state': 'draft',
            'is_giftcard_line': True,
        }

        # 1. Lista Individual de Planes Base
        for p in template.base_product_ids:
            base_data.append({
                **common,
                'product_id': p.id,
                'name': p.get_product_multiline_description_sale() if hasattr(p, 'get_product_multiline_description_sale') else p.name,
                'product_uom_qty': 1.0,
                'price_unit': p.lst_price,
                'ott_type': 'base',
                'tax_id': [(6, 0, p.taxes_id.ids)],
            })
        
        # 2. Lista Individual de Servicios Extras
        for p in template.extra_product_ids:
            extra_data.append({
                **common,
                'product_id': p.id,
                'name': p.get_product_multiline_description_sale() if hasattr(p, 'get_product_multiline_description_sale') else p.name,
                'product_uom_qty': 1.0,
                'price_unit': p.lst_price,
                'ott_type': 'extra',
                'tax_id': [(6, 0, p.taxes_id.ids)],
            })

        # 3. Lista Individual de Eventos
        for r in template.rate_template_ids:
            event_data.append({
                **common,
                'product_id': r.rate_product.id,
                'name': r.rate_product.get_product_multiline_description_sale() if hasattr(r.rate_product, 'get_product_multiline_description_sale') else r.rate_product.name,
                'product_uom_qty': 1.0,
                'price_unit': r.rate_price,
                'rate_template_id': r.id,
                'ott_type': 'event',
                'ott_permanence': r.rate_permanence.id,
                'tax_id': [(6, 0, r.rate_product.taxes_id.ids)],
            })

        print(f"\nDEBUG: Listas Generadas -> Base: {len(base_data)}, Extra: {len(extra_data)}, Eventos: {len(event_data)}")
        
        # Retornamos las 3 listas como una tupla
        return base_data, extra_data, event_data

    @api.onchange('gift_template_id')
    def _onchange_gift_template_id(self):
        # Si el usuario borra la plantilla, limpiamos toda la orden y las vistas
        if not self.gift_template_id:
            self.order_line = [(5, 0, 0)]
            self.base_line_ids = [(5, 0, 0)]
            self.extra_line_ids = [(5, 0, 0)]
            self.event_line_ids = [(5, 0, 0)]
            return

        # Obtenemos las 3 listas (los diccionarios)
        base_list, extra_list, event_list = self._get_gift_template_data_list(self.gift_template_id)

        # 1. Creamos TODOS los registros en la memoria caché maestra de una sola vez
        all_lines = base_list + extra_list + event_list
        self.order_line = [(5, 0, 0)] + [(0, 0, d) for d in all_lines]

        # 2. EL TRUCO MÁGICO: Forzamos a las pestañas de la interfaz a leer esa memoria filtrada.
        # Al asignar el "recordset" directamente, el front-end reacciona al instante.
        self.base_line_ids = self.order_line.filtered(lambda l: l.ott_type == 'base')
        self.extra_line_ids = self.order_line.filtered(lambda l: l.ott_type == 'extra')
        self.event_line_ids = self.order_line.filtered(lambda l: l.ott_type == 'event')

    def _clean_order_lines(self, commands):
        """
        Limpia las líneas fantasma que manda la vista y asegura que las válidas tengan 'name'.
        """
        if not commands:
            return []
        
        cleaned = []
        for cmd in commands:
            if cmd[0] in (0, 1) and len(cmd) == 3 and isinstance(cmd[2], dict):
                line_vals = cmd[2]
                
                # 1. Detectar y destruir líneas fantasma (sin producto y sin ser nota/sección)
                if not line_vals.get('product_id') and not line_vals.get('display_type') and cmd[0] == 0:
                    continue # Saltamos esta línea (no se agrega a la base de datos)

                # 2. Si es una línea válida que sobrevivió, aseguramos el name
                if not line_vals.get('name'):
                    if line_vals.get('product_id'):
                        product = self.env['product.product'].browse(line_vals['product_id'])
                        line_vals['name'] = product.display_name or 'Producto Giftcard'
                    else:
                        line_vals['name'] = 'Línea de Giftcard'
            
            cleaned.append(cmd)
            
        return cleaned

    @api.model
    def create(self, vals):
        if vals.get('is_giftcard') and vals.get('gift_template_id'):
            if not any(f in vals for f in ['base_line_ids', 'extra_line_ids', 'event_line_ids', 'order_line']):
                template = self.env['gift.template'].browse(vals['gift_template_id'])
                b, ex, ev = self._get_gift_template_data_list(template)
                vals['order_line'] = [(0, 0, d) for d in (b + ex + ev)]
        
        merged_lines = []
        for field_name in ['base_line_ids', 'extra_line_ids', 'event_line_ids']:
            if field_name in vals:
                merged_lines.extend(vals.pop(field_name))
        
        if merged_lines:
            vals['order_line'] = vals.get('order_line', []) + merged_lines
            
        # APLICAMOS EL NUEVO FILTRO DE LIMPIEZA
        if 'order_line' in vals:
            vals['order_line'] = self._clean_order_lines(vals['order_line'])
            
        return super(SaleOrder, self).create(vals)

    def write(self, vals):
        merged_lines = []
        for field_name in ['base_line_ids', 'extra_line_ids', 'event_line_ids']:
            if field_name in vals:
                merged_lines.extend(vals.pop(field_name))
        
        if merged_lines:
            vals['order_line'] = vals.get('order_line', []) + merged_lines
            
        # APLICAMOS EL NUEVO FILTRO DE LIMPIEZA
        if 'order_line' in vals:
            vals['order_line'] = self._clean_order_lines(vals['order_line'])
            
        res = super(SaleOrder, self).write(vals)
        
        if 'gift_template_id' in vals and vals.get('gift_template_id'):
            for order in self:
                if order.is_giftcard:
                    b, ex, ev = order._get_gift_template_data_list(order.gift_template_id)
                    all_lines = b + ex + ev
                    order.order_line = [(5, 0, 0)] + [(0, 0, d) for d in all_lines]
                    
        return res

    def action_confirm(self):
        # -------------------------------------------------------------
        # 0. VALIDACIÓN DE LÍMITE AL MOMENTO DE LA COMPRA REAL
        # -------------------------------------------------------------
        for order in self:
            if order.is_giftcard and order.gift_template_id and order.franchise_id:
                limit = order.gift_template_id.giftcard_limit
                
                if limit and limit > 0:
                    # Contamos ÚNICAMENTE las giftcards reales que ya fueron confirmadas/vendidas
                    cards_count = self.env['gift.card'].search_count([
                        ('template_id', '=', order.gift_template_id.id),
                        ('franchise_id', '=', order.franchise_id.id),
                        ('sale_state', '!=', 'cancel')
                    ])
                    
                    if cards_count >= limit:
                        raise ValidationError(
                            f"¡Promoción Agotada! No se puede confirmar esta orden.\n"
                            f"La plantilla '{order.gift_template_id.name}' ya ha alcanzado "
                            f"su límite máximo de {limit} giftcards vendidas en esta franquicia."
                        )
        # -------------------------------------------------------------

        # 1. Limpieza de líneas fantasma (obligatorio para evitar errores nativos)
        for order in self:
            ghost_lines = order.order_line.filtered(lambda l: not l.product_id and not l.display_type)
            if ghost_lines:
                ghost_lines.unlink()

        res = super(SaleOrder, self).action_confirm()

       # 2. Generación del "Combo" Giftcard
        for order in self:
            if not order.is_giftcard: 
                continue
                
            # Filtramos las líneas por su tipo OTT
            base_lines = order.order_line.filtered(lambda l: l.ott_type == 'base')
            extra_lines = order.order_line.filtered(lambda l: l.ott_type == 'extra')
            event_lines = order.order_line.filtered(lambda l: l.ott_type == 'event')

            # Creamos 1 sola giftcard separando los IDs en sus respectivos campos
            self.env['gift.card'].create({
                'template_id': order.gift_template_id.id,
                'franchise_id': order.franchise_id.id,
                'sale_order_id': order.id,
                'res_partner': order.partner_id.id,
                'base_product_ids': [(6, 0, base_lines.mapped('product_id').ids)],
                'extra_product_ids': [(6, 0, extra_lines.mapped('product_id').ids)],
                'rate_template_ids': [(6, 0, event_lines.mapped('rate_template_id').ids)],
                'sale_state': 'sale',
            })
            
        return res

    def action_cancel(self):
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
    
   #Funcion para sumar los totales de las pestañas y mostrarlos en la vista 
    @api.depends(
        'order_line.price_subtotal', 'order_line.price_tax', 'order_line.price_total',
        'base_line_ids.price_subtotal', 'base_line_ids.price_tax', 'base_line_ids.price_total',
        'extra_line_ids.price_subtotal', 'extra_line_ids.price_tax', 'extra_line_ids.price_total',
        'event_line_ids.price_subtotal', 'event_line_ids.price_tax', 'event_line_ids.price_total'
    )
    def _compute_amounts(self):
        """
        Sobrescribimos el cálculo total para forzar que respete el 
        multiplicador leyendo los datos frescos directamente de las pestañas.
        """
        super(SaleOrder, self)._compute_amounts()
        
        for order in self:
            if order.is_giftcard:
                # 1. Unimos todas las líneas de las pestañas en tiempo real
                active_lines = order.base_line_ids | order.extra_line_ids | order.event_line_ids
                
                # 2. Si las pestañas están vacías (ej. antes de cargar), usamos order_line
                if not active_lines:
                    active_lines = order.order_line
                    
                # 3. Sumamos usando la información fresca
                untaxed = sum(active_lines.mapped('price_subtotal'))
                tax = sum(active_lines.mapped('price_tax'))
                
                # 4. Actualizamos los campos nativos
                order.amount_untaxed = untaxed
                order.amount_tax = tax
                order.amount_total = untaxed + tax

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    rate_template_id = fields.Many2one('ott.rate.template', string="Events Template")
    ott_type = fields.Selection([('base', 'Base'), ('event', 'Event'), ('extra', 'Extra')], string="Type", store=True)
    ott_permanence = fields.Many2one('ott.permanence', string="Permanence")
    permanence_type = fields.Selection(related='ott_permanence.permanence_type', readonly=True)
    state = fields.Selection([('draft', 'Draft'), ('open', 'Open'), ('terminated', 'Terminated')], default="draft")
    is_giftcard_line = fields.Boolean(related='order_id.is_giftcard', store=True)

    #Funcion para aplicar el valor total de precio unitario multiplicado por la permanencia
    @api.depends('product_uom_qty', 'price_unit', 'tax_id', 'ott_permanence')
    def _compute_amount(self):
        """Aplica el Billing Factor de suscripciones a la orden de venta."""
        super(SaleOrderLine, self)._compute_amount()
        for line in self:
            if not line.is_giftcard_line or not line.ott_permanence:
                continue
                
            billing_factor = 1.0
            p = line.ott_permanence
            if p.permanence_type == 'days' and p.permanence_duration:
                billing_factor = p.permanence_duration / 30.0
            elif p.permanence_type == 'months' and p.permanence_duration:
                billing_factor = float(p.permanence_duration)

            base_amount = line.price_unit * line.product_uom_qty * billing_factor
            taxes = line.tax_id.compute_all(base_amount, line.order_id.currency_id, 1.0, product=line.product_id, partner=line.order_id.partner_id)

            line.update({
                'price_subtotal': taxes['total_excluded'],
                'price_total': taxes['total_included'],
                'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
            })