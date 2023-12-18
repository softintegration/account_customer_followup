# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.exceptions import ValidationError
from odoo.tools import float_is_zero, float_compare, float_round


class AccountMove(models.Model):
    _inherit = "account.move"

    excluded_from_report = fields.Boolean(string='Excluded',default=False)