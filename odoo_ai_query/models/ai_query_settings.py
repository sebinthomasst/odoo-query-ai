# -*- coding: utf-8 -*-
from odoo import models, fields, api

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    ai_query_api_key = fields.Char(
        string='Anthropic API Key',
        config_parameter='odoo_ai_query.api_key',
        help="Anthropic API key for AI Query Assistant."
    )
    ai_query_default_limit = fields.Integer(
        string='Default Limit',
        config_parameter='odoo_ai_query.default_limit',
        default=100,
        help="Default limit for query results."
    )
    ai_query_max_limit = fields.Integer(
        string='Max Limit',
        config_parameter='odoo_ai_query.max_limit',
        default=500,
        help="Max limit for query results without explicit request."
    )

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        params = self.env['ir.config_parameter'].sudo()
        res.update(
            ai_query_api_key=params.get_param('odoo_ai_query.api_key', ''),
            ai_query_default_limit=int(params.get_param('odoo_ai_query.default_limit', 100)),
            ai_query_max_limit=int(params.get_param('odoo_ai_query.max_limit', 500)),
        )
        return res

    @api.model
    def set_values(self):
        super(ResConfigSettings, self).set_values()
        params = self.env['ir.config_parameter'].sudo()
        params.set_param('odoo_ai_query.api_key', self.ai_query_api_key or '')
        params.set_param('odoo_ai_query.default_limit', str(self.ai_query_default_limit or 100))
        params.set_param('odoo_ai_query.max_limit', str(self.ai_query_max_limit or 500))
