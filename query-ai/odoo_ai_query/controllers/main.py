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
