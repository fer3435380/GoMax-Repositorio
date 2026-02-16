# -*- coding: utf-8 -*-

from odoo import models, fields
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
import logging


_logger = logging.getLogger(__name__)

class ProductProduct(models.Model):
    _inherit = 'product.product'

    # rank_ott = fields.Integer(
    #     'Rango OTT', help="Utilizado para filtrar los productos al momento de hacer upgrade")
    
    # web_product = fields.Boolean('Visible en Portal GoMax')


    def get_ott_products_base(self):
        result = {}

        # Filtro actualizado: 
        # 1. p.product_tmpl_id.web_product debe ser False (not)
        # 2. No debe ser un evento
        products = self.filtered(
            lambda p: p.product_tmpl_id.web_product and p.product_tmpl_id.ott_subscription_type != 'event'
        )

        for product in products:
            tmpl = product.product_tmpl_id
            
            result[product.id] = {
                'id': product.id,
                'name': product.name,
                'description': product.description_sale,
                'extra_product': tmpl.ott_subscription_type == 'extra',
                'rank_product': tmpl.rank_ott,
                'image': (
                    product.image_512.decode('utf-8')
                    if product.image_512
                    else ''
                ),
                'product_configuration': {
                    'channel_count': tmpl.channel_count,
                    'simultaneous_screens': tmpl.simultaneous_screens,
                    'recording_hours': tmpl.recording_hours,
                    'included_events': tmpl.included_events or '',
                    'ott_extras': tmpl.ott_extras or '',
                }
            }

        return result

    def get_ott_products(self, product_ids=None, partner_id=None):
        Product = self.env['product.product']
        Pricelist = self.env['product.pricelist']
        Partner = self.env['res.partner']

        # Productos extra OTT
        extra_products = Product.search([
            ('product_tmpl_id.ott_subscription_type', '=', 'extra')
        ]).ids

        # Pricelist base (solo activas)
        pricelist = Pricelist.search([
            ('active', '=', True),
        ], limit=1)

        # Meses disponibles
        num_months = [1, 6, 12]

        partner = None
        if partner_id:
            partner = Partner.browse(partner_id)
            if not partner.exists():
                partner = None

        # Productos
        if product_ids:
            products = Product.browse(product_ids).exists()
        else:
            products = Product.search([
                ('sale_ok', '=', True),
            ])

        product_data = products.get_ott_products_base()
        result = defaultdict(list)

        for n in num_months:
            for key, product in product_data.items():
                item = product.copy()
                product_rec = Product.browse(item['id'])

                try:
                    # 🔑 Odoo 18 → precio UNITARIO para quantity = n
                    price_unit = pricelist._get_products_price(
                        product_rec,
                        quantity=n,
                        partner=partner
                    )[product_rec.id]

                    # ───── PRODUCTO NORMAL (MISMA LÓGICA ODOO 15) ─────
                    if key not in extra_products:
                        item['price'] = float(
                            Decimal(price_unit * n).quantize(Decimal('0.01'))
                        )
                        item['quantity'] = n
                        item['pricelist_id'] = pricelist.id

                    # ───── PRODUCTO EXTRA ─────
                    else:
                        contracts = (
                            self.env['subscription.package'].search([
                                ('partner_id', '=', partner.id),
                                ('current_stage', '=', 'progress')
                            ]) if partner else False
                        )
                        _logger.info(contracts)
                        if contracts:
                            _logger.info("Calculando precio prorrateado para producto extra")
                            contract = contracts[0]
                            current_plan = contract._get_current_base_plan()
                            _logger.info(f"--------------------: {current_plan}/n/n")
                            #cambiar por next_payment_date en vez de ott_end_date, linea 114 - 118
                            if current_plan and current_plan.ott_end_date:
                                _logger.info("Calculando precio prorrateado para producto extra - con end date")
                                today = fields.Date.today()
                                n_days = (
                                    current_plan.ott_end_date - today
                                ).days

                                extra_price = float(
                                    Decimal(
                                        price_unit * n_days / 30
                                    ).quantize(Decimal('0.01'))
                                )

                                item['price'] = extra_price
                                item['quantity'] = n
                                item['pricelist_id'] = pricelist.id
                        else:
                            _logger.info("Calculando precio normal para producto extra - sin contrato")
                            item['price'] = float(
                                Decimal(price_unit * n).quantize(Decimal('0.01'))
                            )
                            item['quantity'] = n
                            item['pricelist_id'] = pricelist.id

                except Exception:
                    _logger.exception("Error en get_ott_products")

                result[int(n)].append(item)

        return result
