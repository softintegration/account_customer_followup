# -*- coding: utf-8 -*-

{
    'name': 'Account customer followup',
    'version': '1.0.1.2',
    'author':'Soft-integration',
    'category': 'Accounting',
    'description': "",
    'depends': [
        'account'
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/account_customer_followup_data.xml',
        'data/mail_templates_data.xml',
        'views/res_partner_views.xml',
        'views/followup_level_views.xml',
        'views/account_customer_followup_menuitems.xml',
        'report/report_followup_report.xml',
        'report/account_customer_followup_report.xml'
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
