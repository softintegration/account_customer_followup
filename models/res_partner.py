# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import timedelta


class ResPartner(models.Model):
    _inherit = "res.partner"

    payer_type = fields.Selection([('done', 'Good payer'),
                                   ('normal', 'Normal payer'),
                                   ('blocked', 'Bad payer'), ], string='Type of payer', required=True, index=True,
                                  default='normal')
    followup_level_id = fields.Many2one('followup.level',string='Follow-up level currently applied to this partner')
    next_reminder_date = fields.Date(string='Next reminder Date', index=True,readonly=True)
    account_move_residual_ids = fields.One2many("account.move", 'partner_id',
                                                domain=[('move_type', 'in',('out_invoice',))
                                                    , ('state', '=', 'posted'),
                                                        ('payment_state', 'in', ('not_paid', 'partial'))],
                                                string='unpaid invoices',readonly=False)
    total_amount_due = fields.Monetary(compute='_get_amounts',
                                       string="Amount Due",store=True )  # search='_payment_due_search')
    total_amount_due_report = fields.Monetary(compute='_get_amounts',
                                       string="Amount Due",store=False )
    total_amount_overdue = fields.Monetary(compute='_get_amounts',
                                           string="Amount Overdue",store=True )  # search='_payment_overdue_search')

    followup_status = fields.Selection(
        [('in_need_of_action', 'In need of action'),
         ('with_overdue_invoices', 'With overdue invoices'),
         ('no_action_needed', 'No action needed')],
        string='Followup status',default='no_action_needed')
    send_by_mail_action = fields.Boolean(default=False)
    reminder_email_template_id = fields.Many2one('mail.template', 'Email Template')



    @api.depends('account_move_residual_ids')
    def _get_amounts(self):
        company = self.env.user.company_id
        current_date = fields.Date.today()
        for each in self:
            total_amount_due = 0.0
            total_amount_due_report = 0.0
            total_amount_overdue = 0.0
            for account_move in each.account_move_residual_ids.filtered(lambda move: move.company_id == company):
                date_due = account_move.invoice_date_due or account_move.date
                total_amount_due += account_move.amount_residual
                if not account_move.excluded_from_report:
                    total_amount_due_report += account_move.amount_residual
                if date_due <= current_date:
                    total_amount_overdue += account_move.amount_residual
                    account_move.amount_residual_overdue = account_move.amount_residual
            each.total_amount_due = total_amount_due
            each.total_amount_due_report = total_amount_due_report
            each.total_amount_overdue = total_amount_overdue

    @api.model
    def _get_followup(self):
        """ Get the reminder level rule applied for each partner according to its use case
        * When the minimum due date from the list of unpaid invoices + reminder level rule delay <= today and the reminder level rule hasn't been applied yet,
        we have to pick the reminder level and put the possible actions according to it
        * Else we seek other levels and do the same checks"""
        # Get only the partners with unpaid invoices
        partners = self.env['account.move'].search([('move_type', 'in',('out_invoice',)),('state', '=', 'posted'),
                                                        ('payment_state', 'in', ('not_paid', 'partial'))]).mapped("partner_id")
        current_date = fields.Date.today()
        for each in partners:
            # TODO : First step => if the customer is excluded from reminding we have to skip them
            # browse all the unpaid invoices
            for account_move in each.account_move_residual_ids:
                invoice_date_due = account_move.invoice_date_due or account_move.date
                # if the invoice due date is not reached yet ,we have to skip the invoice
                if invoice_date_due > current_date:
                    continue
                # if the invoice is already being followed-up ,we should skip it
                if account_move._is_being_followed_invoice():
                    continue
                # if this is the first time to follow the invoice or it has been already followed and done with follow-up level
                # we have to follow the invoice with the next follow-up level
                if not account_move._is_followed_invoice() or account_move._is_done_followed_invoice():
                    account_move._followup_invoice()
            # get the earliest due date invoice
            #earliest_date_due = each._get_earliest_date_due()
            # if no invoice has exceeded the due duration,we have no reminder to do
            #if earliest_date_due > current_date:
            #    continue
            # search the suitable reminder rule to apply according to the earliest date due found for this partner
            #reminder_date = False
            #suitable_followup_level = each._get_suitable_followup_level(earliest_date_due)
            #if suitable_followup_level:
            #    reminder_date = earliest_date_due + timedelta(days=suitable_followup_level.delay)
            #    each.next_reminder_date = reminder_date
            #if reminder_date and reminder_date <= current_date:
            #    each._apply_reminder_rule(suitable_followup_level)
            #    each.next_reminder_date = current_date
            if each.followup_status != 'in_need_of_action' and each.total_amount_overdue > 0:
                each.followup_status = 'with_overdue_invoices'
            elif each.followup_status != 'in_need_of_action':
                each._init_followup_status()


    def _evaluate_followup_level(self,followup_level):
        for each in self:
            if followup_level._greater_then_followup_level(each.followup_level_id):
                each._apply_followup_level(followup_level)

    def _apply_followup_level(self,followup_level):
        # in this step ,beside the reminder rule details,the followup_status must be in_need_of_action
        values = {'followup_level_id':followup_level.id,'followup_status':'in_need_of_action'}
        if followup_level.action_list_ids.filtered(lambda act:act.action_code == 'action_send_bymail'):
            values.update({'send_by_mail_action':True,'reminder_email_template_id':followup_level.email_template_id.id})
        self.write(values)

    def _init_followup_status(self):
        self.write({'followup_status':'no_action_needed'})


    def send_invoices_by_mail(self):
        self.ensure_one()
        template = self.reminder_email_template_id
        lang = self.env.context.get('lang')
        if template.lang:
            lang = template._render_lang(self.ids)[self.id]
        template.report_template = self.env.ref('account_customer_followup.action_report_followup_reminder').id
        ctx = {
            'default_model': self._name,
            'default_res_id': self.ids[0],
            'default_use_template': False,
            'default_template_id': template.id,
            'default_composition_mode': 'comment',
            'mark_so_as_sent': True,
            'custom_layout': "mail.mail_notification_paynow",
            'force_email': True,
            'model_description': _('Follow-up Reminder'),
        }
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(False, 'form')],
            'view_id': False,
            'target': 'new',
            'context': ctx,
            'lang': lang,
        }

    def make_as_done(self):
        self._make_as_done()

    def _make_as_done(self):
        self.mapped("account_move_residual_ids")._is_being_followed_invoice()._set_as_done()
        self._init_followup_status()



