# -*- coding: utf-8 -*-
from odoo import http, _, tools
from odoo.http import request

class AIQueryController(http.Controller):

    @http.route('/ai_query/execute', type='json', auth='user', methods=['POST'])
    def execute(self, **payload):
        required = ['model', 'domain']
        for k in required:
            if k not in payload:
                return {'error': _('Missing required key %s') % k}
        env = request.env
        builder = env['ai.query.builder']
        result = builder.build_and_execute(payload)
        return result

    @http.route('/ai_query/ask', type='json', auth='user', methods=['POST'])
    def ask(self, **payload):
        question = payload.get('question')
        if not question:
            return {'error': _('Missing required key "question"')}
        
        env = request.env
        builder = env['ai.query.builder']
        result = builder.ask_claude(question)
        return result
