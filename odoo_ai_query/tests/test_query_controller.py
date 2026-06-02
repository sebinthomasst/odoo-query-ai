# -*- coding: utf-8 -*-
import json
from odoo import fields
from odoo.tests.common import TransactionCase
from odoo.exceptions import AccessError

class TestAIQueryController(TransactionCase):

    def setUp(self):
        super(TestAIQueryController, self).setUp()
        self.QueryBuilder = self.env['ai.query.builder']
        
        # Configure test limits
        params = self.env['ir.config_parameter'].sudo()
        params.set_param('odoo_ai_query.default_limit', '50')
        params.set_param('odoo_ai_query.max_limit', '200')

    def test_query_builder_execution(self):
        # Test search read execution on res.partner
        payload = {
            'model': 'res.partner',
            'domain': [('name', '!=', False)],
            'fields': ['name', 'email'],
            'limit': 5
        }
        res = self.QueryBuilder.build_and_execute(payload)
        
        self.assertNotIn('error', res)
        self.assertIn('data', res)
        self.assertIn('html', res)
        self.assertTrue(len(res['data']) <= 5)
        self.assertEqual(res['model'], 'res.partner')

    def test_query_builder_clamping(self):
        # Limit requested exceeds max_limit (200)
        payload = {
            'model': 'res.partner',
            'domain': [],
            'fields': ['name'],
            'limit': 1000
        }
        res = self.QueryBuilder.build_and_execute(payload)
        self.assertEqual(res['pagination']['limit'], 200)

    def test_sensitive_model_restriction(self):
        # Accessing res.users password/hashes or config parameters should fail
        payload = {
            'model': 'ir.config_parameter',
            'domain': [],
            'fields': ['key', 'value']
        }
        res = self.QueryBuilder.build_and_execute(payload)
        self.assertIn('error', res)
        self.assertIn('restricted', res['error'].lower())

    def test_date_parsing(self):
        # Resolve 'today' and other placeholders
        resolved_today = self.QueryBuilder._get_date_placeholder('today')
        self.assertEqual(resolved_today, fields.Date.to_string(fields.Date.today()))

        resolved_start = self.QueryBuilder._get_date_placeholder('this month', '>=')
        self.assertEqual(resolved_start, fields.Date.to_string(fields.Date.today().replace(day=1)))
