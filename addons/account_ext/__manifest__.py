{
    'name': 'Invoice DGII Integration',
    'version': '1.0',
    'summary': 'Adds Invoice Type to invoices and integrates with DGII API',
    'category': 'Accounting',
    'author': 'Your Name',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'views/account_move_views.xml',
    ],
    'installable': True,
    'application': False,
}