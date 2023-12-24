# -*- coding: utf-8 -*-


from odoo import fields, models, _


class FollowupLevel(models.Model):
    _name = 'followup.level'
    _description = 'Follow-up level'

    sequence = fields.Integer(help="Gives the sequence order when displaying a list of follow-up lines.")
    name = fields.Char(string="Name", required=True)
    delay = fields.Integer('Due Days', required=True,
                           help="The number of days after the due date of the invoice"
                                " to wait before sending the reminder."
                                "  Could be negative if you want to send a polite alert beforehand.")
    email_template_id = fields.Many2one('mail.template', 'Email Template',
                                        ondelete='set null', default=lambda self: self.env.ref(
            'account_customer_followup.email_template_followup_level0'))
    company_id = fields.Many2one('res.company', 'Company',
                                 default=lambda self: self.env.company)
    active = fields.Boolean(default=True)
    action_list_ids = fields.Many2many('followup.level.action', 'followup_level_action_rel', 'level_id', 'action_id',
                                       string="Actions")


class FollowupLevelAction(models.Model):
    _name = 'followup.level.action'

    name = fields.Char(string='Name', required=True)
    action_code = fields.Selection([('action_send_bymail', 'Send by mail')], required=True)
