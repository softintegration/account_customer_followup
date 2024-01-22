# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import timedelta
from odoo.exceptions import UserError
from odoo.exceptions import ValidationError
from odoo.tools import float_is_zero, float_compare, float_round


class AccountMove(models.Model):
    _inherit = "account.move"

    excluded_from_report = fields.Boolean(string='Excluded',default=False,readonly=False)
    amount_residual_overdue = fields.Monetary(string='Amount Due',store=True,currency_field='company_currency_id')


    def _is_followed_invoice(self):
        """ Check if this invoice(s) is(are) already followed,this can be true if the invoice is being in process of
        follow or has been followed with a specific follow-up level"""
        return self.env['account.move.followup.level'].search_count([('account_move_id','in',self.ids)])

    def _is_being_followed_invoice(self):
        """ Check the invoice is being in process of follow-up """
        return self.env['account.move.followup.level'].search([('account_move_id','in',self.ids),('state','=','in_progress')])

    def _is_done_followed_invoice(self):
        """ Check if this invoice(s) has been followed with a specific follow-up level"""
        return self.env['account.move.followup.level'].search([('account_move_id','in',self.ids),('state','=','done')])

    def _followup_invoice(self):
        """ Follow up the invoice by assigning it to the next found follow-up level if it's applied"""
        current_date = fields.Date.today()
        if not self._is_followed_invoice():
            followup_dict = []
            # Get the first followup level and try to apply it
            follow_up_level = self.env['followup.level'].search([],order='delay',limit=1)
            if follow_up_level:
                # we should apply the followup level only if the invoice due date with the followup specified delay reaches or exceeds the current date
                delay_days = timedelta(days=follow_up_level.delay)
                for each in self:
                    invoice_date_due = each.invoice_date_due or each.date
                    if invoice_date_due + delay_days < current_date:
                        followup_dict.append({
                            'account_move_id':each.id,
                            'followup_level_id':follow_up_level.id
                        })
                    each.partner_id._evaluate_followup_level(follow_up_level)
                self.env['account.move.followup.level'].create(followup_dict)
        elif self._is_done_followed_invoice():
            for each in self:
                invoice_date_due = each.invoice_date_due or each.date
                done_followup_level = each._is_done_followed_invoice().followup_level_id
                next_followup_level = self.env['followup.level'].search([('delay','>',done_followup_level.delay)],order='delay',limit=1)
                if next_followup_level:
                    # we should apply the followup level only if the invoice due date with the followup specified delay reaches or exceeds the current date
                    delay_days = timedelta(days=next_followup_level.delay)
                    if invoice_date_due + delay_days < current_date:
                        each._is_done_followed_invoice().write({'followup_level_id':next_followup_level.id,'state':'in_progress'})
                        each.partner_id._evaluate_followup_level(next_followup_level)



class AccountMoveFollowup(models.Model):
    _name = 'account.move.followup.level'

    account_move_id = fields.Many2one('account.move',required=True,string='Account move',index=True)
    followup_level_id = fields.Many2one('followup.level',required=True,string='Follow-up level',index=True)
    state = fields.Selection([('in_progress','In progress'),
                              ('done','Done')],default='in_progress',required=True)
    company_id = fields.Many2one('res.company', required=True, readonly=True, default=lambda self: self.env.company)

    _sql_constraints = [
        ('account_move_followup_uniq',
         'unique (account_move_id,followup_level_id,company_id)',
         'At more One follow-up level can be assigned to account move!')
    ]


    def _set_as_done(self):
        self.write({'state':'done'})