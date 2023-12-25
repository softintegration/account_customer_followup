# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import timedelta


class ResPartner(models.Model):
    _inherit = "res.partner"

    payer_type = fields.Selection([('done', 'Good payer'),
                                   ('normal', 'Normal payer'),
                                   ('blocked', 'Bad payer'), ], string='Type of payer', required=True, index=True,
                                  default='normal')
    next_reminder_date = fields.Date(string='Next reminder Date', index=True,readonly=True)
    account_move_residual_ids = fields.One2many("account.move", 'partner_id',
                                                domain=[('move_type', 'in',('out_invoice',))
                                                    , ('state', '=', 'posted'),
                                                        ('payment_state', 'in', ('not_paid', 'partial'))],
                                                string='unpaid invoices',readonly=False)
    total_amount_due = fields.Monetary(compute='_get_amounts',
                                       string="Amount Due",store=False )  # search='_payment_due_search')
    total_amount_due_report = fields.Monetary(compute='_get_amounts',
                                       string="Amount Due",store=False )
    total_amount_overdue = fields.Monetary(compute='_get_amounts',
                                           string="Amount Overdue",store=False )  # search='_payment_overdue_search')

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
            each.total_amount_due = total_amount_due
            each.total_amount_due_report = total_amount_due_report
            each.total_amount_overdue = total_amount_overdue
        self._get_followup()

    def _get_earliest_date_due(self):
        self.ensure_one()
        earliest_date_due = min([am.invoice_date_due or am.date for am in self.account_move_residual_ids])
        return earliest_date_due

    def _possible_followup_levels(self):
        possible_followup_levels_domain = [('company_id','=',self.env.company.id)]
        return self.env['followup.level'].search(possible_followup_levels_domain,order='sequence,id')



    def _get_suitable_followup_level(self,reference_date_due):
        self.ensure_one()
        current_date = fields.Date.today()
        for followup_level in self._possible_followup_levels():
            if reference_date_due + timedelta(days=followup_level.delay) <= current_date:
                return followup_level

    def _get_followup(self):
        """ Get the reminder level rule applied for each partner according to its use case
        * When the minimum due date from the list of unpaid invoices + reminder level rule delay <= today and the reminder level rule hasn't been applied yet,
        we have to follow the level rule and put the possible actions according to it
        * Else we seek other rules and do the same checks"""
        current_date = fields.Date.today()
        # check only partner with unpaid invoices
        for each in self.filtered(lambda par:par.account_move_residual_ids):
            # get the earliest due date invoice
            earliest_date_due = each._get_earliest_date_due()
            # if no invoice has exceeded the due duration,we have no reminder to do
            if earliest_date_due > current_date:
                continue
            # search the suitable reminder rule to apply according to the earliest date due found for this partner
            reminder_date = False
            suitable_followup_level = each._get_suitable_followup_level(earliest_date_due)
            if suitable_followup_level:
                reminder_date = earliest_date_due + timedelta(days=suitable_followup_level.delay)
                each.next_reminder_date = reminder_date
            if reminder_date and reminder_date <= current_date:
                each._apply_reminder_rule(suitable_followup_level)
                each.next_reminder_date = current_date
            elif each.total_amount_overdue > 0:
                each.followup_status = 'with_overdue_invoices'
            else:
                each._init_followup_status()


    def _apply_reminder_rule(self,reminder_rule):
        # in this step ,beside the reminder rule details,the followup_status must be in_need_of_action
        values = {'followup_status':'in_need_of_action'}
        if reminder_rule.action_list_ids.filtered(lambda act:act.action_code == 'action_send_bymail'):
            values.update({'send_by_mail_action':True,'reminder_email_template_id':reminder_rule.email_template_id.id})
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
        pass

