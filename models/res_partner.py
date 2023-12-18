# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.exceptions import ValidationError
from odoo.tools import float_is_zero, float_compare, float_round


class ResPartner(models.Model):
    _inherit = "res.partner"

    payer_type = fields.Selection([('done', 'Good payer'),
                                   ('normal', 'Normal payer'),
                                   ('blocked', 'Bad payer'), ], string='Type of payer', required=True, index=True,
                                  default='normal')
    next_reminder_date = fields.Date(string='Next reminder Date', index=True, )
    account_move_residual_ids = fields.One2many("account.move", 'partner_id',
                                                domain=[('move_type', 'in',('out_invoice',))
                                                    , ('state', '=', 'posted'),
                                                        ('payment_state', 'in', ('not_paid', 'partial'))],
                                                string='unpaid invoices')
    total_amount_due = fields.Monetary(compute='_get_amounts',
                                       string="Amount Due",store=False )  # search='_payment_due_search')
    total_amount_overdue = fields.Monetary(compute='_get_amounts',
                                           string="Amount Overdue",store=False )  # search='_payment_overdue_search')
    followup_status = fields.Selection(
        [('in_need_of_action', 'In need of action'),
         ('with_overdue_invoices', 'With overdue invoices'),
         ('no_action_needed', 'No action needed')],
        string='Followup status',default='no_action_needed')

    @api.depends('account_move_residual_ids')
    def _get_amounts(self):
        company = self.env.user.company_id
        current_date = fields.Date.today()
        for partner in self:
            total_amount_due = 0.0
            total_amount_overdue = 0.0
            for account_move in partner.account_move_residual_ids.filtered(lambda move: move.company_id == company):
                date_due = account_move.invoice_date_due or account_move.date
                total_amount_due += account_move.amount_residual
                if date_due <= current_date:
                    total_amount_overdue += account_move.amount_residual
            partner.total_amount_due = total_amount_due
            partner.total_amount_overdue = total_amount_overdue
