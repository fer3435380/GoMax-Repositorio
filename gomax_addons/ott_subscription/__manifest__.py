# -*- coding: utf-8 -*-
{
    'name': "ott_subscription",

    'summary': "Short (1 phrase/line) summary of the module's purpose",

    'description': """
Long description of module's purpose
    """,

    'author': "My Company",
    'website': "https://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'subscription_package', 'product', 'report_py3o'],


    # always loaded
    'data': [
        'security/ott_subscription_security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence.xml',
        'data/ir_cron_events.xml',
        'data/ir_cron_renew_lines.xml',
        'views/ott_subscription_package.xml',
        'views/views.xml',
        'views/templates.xml',
        'views/ott_config_settings.xml',
        'views/ott_rate_template.xml',
        'views/ott_stage.xml',
        'views/ott_franchise.xml',
        'views/res_users_inherit.xml',
        'views/giftcards_views.xml',
        'views/product_template.xml',
        'views/product_line.xml',
        'views/ott_service.xml',
        'views/ott_permanence.xml',
        'views/ott_orders_giftcards.xml',
        'views/giftcard_template.xml',
        'views/giftcard_report.xml',
        'views/ott_recom_programming.xml',
        'views/product_product.xml',
        'views/ott_background_home.xml',
        'views/ott_channel.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}

