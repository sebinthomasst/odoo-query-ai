# -*- coding: utf-8 -*-
import calendar
import json
import re
import requests
from datetime import datetime, date, timedelta
from odoo import models, fields, api, _
from odoo.exceptions import AccessError

class AIQueryBuilder(models.AbstractModel):
    _name = 'ai.query.builder'
    _description = 'Odoo AI Query Builder and Executor'

    def _detect_version(self):
        try:
            from odoo import release
            if hasattr(release, 'version_info') and release.version_info:
                return release.version_info[0]
        except Exception:
            pass

        try:
            base_module = self.env['ir.module.module'].sudo().search([('name', '=', 'base')], limit=1)
            if base_module and base_module.latest_version:
                return int(base_module.latest_version.split('.')[0])
        except Exception:
            pass

        return 16  # Fallback to Odoo 16

    def _model_map(self, model_name, version):
        # Compatibility Matrix Mapping
        mapping = {
            'account.invoice': {13: 'account.invoice', 14: 'account.invoice', 15: 'account.move', 16: 'account.move', 17: 'account.move', 18: 'account.move'},
            'account.analytic.account': {13: 'account.analytic.account', 14: 'account.analytic.account', 15: 'account.analytic.account', 16: 'account.analytic.account', 17: 'account.analytic.plan', 18: 'account.analytic.plan'},
            'stock.move.line': {13: 'stock.move.line', 14: 'stock.move.line', 15: 'stock.valuation.layer', 16: 'stock.valuation.layer', 17: 'stock.valuation.layer', 18: 'stock.valuation.layer'},
            'stock.valuation.layer': {13: 'stock.move.line', 14: 'stock.move.line', 15: 'stock.valuation.layer', 16: 'stock.valuation.layer', 17: 'stock.valuation.layer', 18: 'stock.valuation.layer'},
        }
        if model_name in mapping:
            return mapping[model_name].get(version, model_name)
        return model_name

    def _get_date_placeholder(self, term, operator=None):
        if not isinstance(term, str):
            return term

        today = fields.Date.today()
        year = today.year
        month = today.month

        term_lower = term.lower().strip()

        # today
        if term_lower == 'today':
            return fields.Date.to_string(today)

        # this week
        elif term_lower in ('this week', 'this_week_start'):
            if operator in ('>', '>='):
                return fields.Date.to_string(today - timedelta(days=today.weekday()))
            return fields.Date.to_string(today)
        elif term_lower == 'this_week_end':
            return fields.Date.to_string(today)

        # this month
        elif term_lower in ('this month', 'this_month_start'):
            if operator in ('>', '>='):
                return fields.Date.to_string(today.replace(day=1))
            return fields.Date.to_string(today)
        elif term_lower == 'this_month_end':
            return fields.Date.to_string(today)

        # last month
        elif term_lower in ('last month', 'last_month_start'):
            last_month_first = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
            if operator in ('>', '>='):
                return fields.Date.to_string(last_month_first)
            last_month_end = today.replace(day=1) - timedelta(days=1)
            return fields.Date.to_string(last_month_end)
        elif term_lower == 'last_month_end':
            last_month_end = today.replace(day=1) - timedelta(days=1)
            return fields.Date.to_string(last_month_end)

        # this quarter
        elif term_lower in ('this quarter', 'this_quarter_start'):
            quarter = (month - 1) // 3 + 1
            if operator in ('>', '>='):
                return fields.Date.to_string(today.replace(month=(quarter - 1) * 3 + 1, day=1))
            return fields.Date.to_string(today)
        elif term_lower == 'this_quarter_end':
            return fields.Date.to_string(today)

        # last quarter
        elif term_lower in ('last quarter', 'last_quarter_start'):
            quarter = (month - 1) // 3 + 1
            last_q = quarter - 1 if quarter > 1 else 4
            last_q_year = year if quarter > 1 else year - 1
            if operator in ('>', '>='):
                return fields.Date.to_string(today.replace(year=last_q_year, month=(last_q - 1) * 3 + 1, day=1))
            last_month_of_q = last_q * 3
            last_day = calendar.monthrange(last_q_year, last_month_of_q)[1]
            return fields.Date.to_string(today.replace(year=last_q_year, month=last_month_of_q, day=last_day))
        elif term_lower == 'last_quarter_end':
            quarter = (month - 1) // 3 + 1
            last_q = quarter - 1 if quarter > 1 else 4
            last_q_year = year if quarter > 1 else year - 1
            last_month_of_q = last_q * 3
            last_day = calendar.monthrange(last_q_year, last_month_of_q)[1]
            return fields.Date.to_string(today.replace(year=last_q_year, month=last_month_of_q, day=last_day))

        # YTD
        elif term_lower in ('ytd', 'ytd_start'):
            if operator in ('>', '>='):
                return fields.Date.to_string(today.replace(month=1, day=1))
            return fields.Date.to_string(today)
        elif term_lower == 'ytd_end':
            return fields.Date.to_string(today)

        # last 7 days
        elif term_lower in ('last 7 days', 'last_7_days_start'):
            if operator in ('>', '>='):
                return fields.Date.to_string(today - timedelta(days=6))
            return fields.Date.to_string(today)
        elif term_lower == 'last_7_days_end':
            return fields.Date.to_string(today)

        # Q1-Q4 specific year range e.g. Q2 2024
        match_q = re.match(r'^q([1-4])\s+(\d{4})$', term_lower)
        if match_q:
            q = int(match_q.group(1))
            y = int(match_q.group(2))
            if operator in ('>', '>='):
                return fields.Date.to_string(today.replace(year=y, month=(q - 1) * 3 + 1, day=1))
            else:
                last_month_of_q = q * 3
                last_day = calendar.monthrange(y, last_month_of_q)[1]
                return fields.Date.to_string(today.replace(year=y, month=last_month_of_q, day=last_day))

        return term

    def _parse_domain_dates(self, domain):
        if not isinstance(domain, list):
            return domain
        new_domain = []
        for term in domain:
            if isinstance(term, (tuple, list)) and len(term) == 3:
                field, operator, val = term
                resolved_val = self._get_date_placeholder(val, operator)
                new_domain.append((field, operator, resolved_val))
            else:
                new_domain.append(term)
        return new_domain

    def _get_field_value(self, record, field_path):
        parts = field_path.split('.')
        current = record
        for part in parts:
            if not current:
                return False
            if hasattr(current, '_name') and hasattr(current, 'browse'):
                if part in current._fields:
                    try:
                        current = getattr(current, part)
                    except Exception:
                        return False
                else:
                    return False
            else:
                try:
                    current = current[part]
                except Exception:
                    return False

        if hasattr(current, '_name') and hasattr(current, 'browse'):
            if not current:
                return ''
            if len(current) == 1:
                return current.display_name or current.name or current.id
            else:
                return [r.display_name or r.name or r.id for r in current]

        if isinstance(current, (datetime, date)):
            return fields.Date.to_string(current)
        return current

    def _format_number(self, val, is_indian_locale=False):
        if isinstance(val, int):
            val_str = f"{val}"
            dec_str = ""
        else:
            val_str = f"{val:.2f}"
            if '.' in val_str:
                val_str, dec_str = val_str.split('.')
                dec_str = "." + dec_str
            else:
                dec_str = ""

        if is_indian_locale:
            if len(val_str) <= 3:
                return val_str + dec_str
            last_three = val_str[-3:]
            remaining = val_str[:-3]
            groups = []
            while remaining:
                groups.append(remaining[-2:])
                remaining = remaining[:-2]
            groups.reverse()
            return ",".join(groups) + "," + last_three + dec_str
        else:
            groups = []
            while val_str:
                groups.append(val_str[-3:])
                val_str = val_str[:-3]
            groups.reverse()
            return ",".join(groups) + dec_str

    def build_and_execute(self, payload):
        env = self.env
        version = self._detect_version()

        raw_model = payload.get('model')
        if not raw_model:
            return {'error': _("Model parameter is missing.")}

        model_name = self._model_map(raw_model, version)

        # Safety: Restrict sensitive models
        sensitive_models = ['ir.config_parameter', 'res.users', 'mail.message', 'ir.actions.server', 'ir.cron', 'ir.model.fields', 'ir.model']
        if model_name in sensitive_models:
            return {'error': _("Access to model %s is restricted for safety reasons.") % model_name}

        # Check if model exists
        if model_name not in env:
            prefix_map = {
                'sale.': 'Sales',
                'account.': 'Accounting',
                'stock.': 'Inventory',
                'crm.': 'CRM',
                'hr.': 'HR',
                'purchase.': 'Purchase',
            }
            app_name = "associated"
            for prefix, app in prefix_map.items():
                if model_name.startswith(prefix):
                    app_name = app
                    break
            return {'error': _("The %s app isn't installed on your Odoo.") % app_name}

        model = env[model_name]

        # HR / Payroll security check
        if model_name.startswith('hr.') or 'payslip' in model_name or 'employee' in model_name:
            hr_group = env.ref('hr.group_hr_manager', raise_if_not_found=False)
            if not hr_group or hr_group.id not in env.user.groups_id.ids:
                return {'error': _("You don't have access to view this data.")}

        # Apply domain
        domain = payload.get('domain', [])
        domain = self._parse_domain_dates(domain)

        # Apply company filter if field exists
        if 'company_id' in model._fields:
            company_ids = env.user.company_ids.ids
            if not isinstance(domain, list):
                domain = []
            domain.append(('company_id', 'in', company_ids))

        # Enforce limits
        params = env['ir.config_parameter'].sudo()
        default_limit = int(params.get_param('odoo_ai_query.default_limit', 100))
        max_limit = int(params.get_param('odoo_ai_query.max_limit', 500))

        requested_limit = payload.get('limit') or default_limit
        limit = min(requested_limit, max_limit)

        # Check total count to avoid broad query (>10k)
        try:
            total_count = model.search_count(domain)
        except Exception as e:
            return {'error': _("Invalid query domain: %s") % str(e)}

        if total_count > 10000:
            return {
                'error': _("Query too broad (%s records). Please add a filter before proceeding.") % total_count
            }

        # Execution
        fields_to_read = payload.get('fields', [])
        order = payload.get('order')
        group_by = payload.get('group_by')

        # Separate relational fields from direct fields
        direct_fields = []
        dot_fields = []
        for f in fields_to_read:
            if '.' in f:
                dot_fields.append(f)
                base_f = f.split('.')[0]
                if base_f not in direct_fields:
                    direct_fields.append(base_f)
            else:
                direct_fields.append(f)

        data_results = []
        if group_by:
            try:
                read_group_results = model.read_group(
                    domain=domain,
                    fields=fields_to_read or [],
                    groupby=group_by,
                    offset=0,
                    limit=limit,
                    orderby=order or False
                )
                data_results = read_group_results
            except Exception as e:
                return {'error': _("Aggregated query failed: %s") % str(e)}
        else:
            try:
                records = model.search(domain, offset=0, limit=limit, order=order or False)
                if dot_fields:
                    for rec in records:
                        row = {}
                        for f in fields_to_read:
                            row[f] = self._get_field_value(rec, f)
                        data_results.append(row)
                else:
                    data_results = records.read(direct_fields)
            except Exception as e:
                return {'error': _("Query execution failed: %s") % str(e)}

        has_more = total_count > limit

        currency_symbol = env.user.company_id.currency_id.symbol or ""
        currency_position = env.user.company_id.currency_id.position or "after"
        is_indian_locale = env.user.company_id.currency_id.name == 'INR'

        # Formatting helper to pass into QWeb template context
        def format_val(col, val):
            if val is False or val is None or val == '':
                return ''
            # Try parsing date string
            if isinstance(val, str):
                # Check for standard YYYY-MM-DD
                if re.match(r'^\d{4}-\d{2}-\d{2}$', val):
                    try:
                        dt = fields.Date.from_string(val)
                        return dt.strftime('%d %b %Y')
                    except Exception:
                        pass
                # Check for standard datetime
                if re.match(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$', val):
                    try:
                        dt = fields.Datetime.from_string(val)
                        return dt.strftime('%d %b %Y')
                    except Exception:
                        pass
            if isinstance(val, (datetime, date)):
                return val.strftime('%d %b %Y')

            # Numbers formatting
            if isinstance(val, (int, float)) and not isinstance(val, bool):
                is_monetary = any(x in col.lower() for x in ['amount', 'price', 'total', 'margin', 'revenue', 'residual', 'value', 'price_unit'])
                is_quantity = any(x in col.lower() for x in ['qty', 'quantity', 'count'])
                
                formatted_num = self._format_number(val, is_indian_locale)
                if is_monetary:
                    if currency_position == 'before':
                        return f"{currency_symbol}{formatted_num}"
                    else:
                        return f"{formatted_num} {currency_symbol}"
                return formatted_num
            return str(val)

        def is_number(col, val):
            return isinstance(val, (int, float)) and not isinstance(val, bool)

        response = {
            'understood_as': payload.get('understood_as', _("Executed query on %s") % model_name),
            'model': model_name,
            'result_count': len(data_results),
            'data': data_results,
            'summary': payload.get('summary') or _("Retrieved %s records from %s.") % (len(data_results), model_name),
            'currency': env.user.company_id.currency_id.name or 'USD',
            'generated_at': fields.Datetime.to_string(fields.Datetime.now()),
            'pagination': {
                'limit': limit,
                'offset': 0,
                'has_more': has_more
            }
        }

        # Render QWeb HTML table
        try:
            html_table = env['ir.qweb']._render(
                'odoo_ai_query.result_template',
                {
                    'data': data_results,
                    'fields': fields_to_read or (data_results[0].keys() if data_results else []),
                    'format_val': format_val,
                    'is_number': is_number
                }
            )
            response['html'] = html_table
        except Exception as e:
            response['html'] = f"<div class='alert alert-danger'>Error rendering HTML table: {str(e)}</div>"

        return response

    def ask_claude(self, question):
        if not question:
            return {'error': _("Please provide a question.")}

        # Fetch API Key securely (from sudo config parameters)
        params = self.env['ir.config_parameter'].sudo()
        api_key = params.get_param('odoo_ai_query.api_key')
        if not api_key:
            return {'error': _("Claude API Key is not configured. Please enter your API Key in Settings -> AI Query Settings first.")}

        version = self._detect_version()

        # Formulate System Prompt with detailed Odoo instructions
        system_prompt = f"""You are an expert Odoo ORM query generator for Odoo version {version}.
Convert the user's natural language question into a precise JSON ORM query payload.

Supported Domains & Models:
1. Sales: sale.order, sale.order.line, product.product, product.template
   Fields: amount_total, state, partner_id, user_id, date_order, product_id, qty_ordered, price_unit, discount, margin
   States: draft=Quotation, sent=Sent, sale=Confirmed, done=Locked, cancel=Cancelled
2. Accounting: account.move, account.move.line, account.payment, res.partner
   Fields: move_type (out_invoice, in_invoice, out_refund), payment_state, amount_residual, invoice_date, invoice_date_due, journal_id, state (draft, posted, cancel)
   Note: Always filter move_type explicitly for invoice/bill queries!
3. Inventory: stock.quant, stock.move, stock.picking, stock.warehouse
   Fields: qty_available, virtual_available, incoming_qty, outgoing_qty, reserved_quantity, location_id, product_id
4. CRM: crm.lead, crm.stage
   Fields: stage_id, probability, expected_revenue, date_conversion, user_id, partner_id, type (lead vs opportunity)
5. HR / Payroll: hr.employee, hr.leave, hr.payslip (Require hr.group_hr_manager check)
6. Purchase: purchase.order, purchase.order.line
   Fields: state, amount_total, partner_id, date_approve, date_planned

Rules:
1. Return EXACTLY a JSON payload structure, no conversation, no fluff:
{{
  "understood_as": "A clear, detailed description of how you translated their query.",
  "model": "odoo.model.name",
  "domain": [["field", "operator", "value"], ...],
  "fields": ["field1", "relational_id.field2", ...],
  "limit": 100,
  "order": "field desc",
  "group_by": ["field"]
}}
2. For aggregations (sum, count, avg) use read_group by specifying "group_by" and aggregated fields (e.g. 'amount_total:sum', 'qty_ordered:sum').
3. For Many2one fields, use dot notation in fields display (e.g., 'partner_id.name') but IDs in domain comparisons.
4. Convert all natural dates to keywords: 'today', 'this week', 'this month', 'last month', 'this quarter', 'last quarter', 'YTD', 'last 7 days', or specific quarter ranges (e.g. 'Q2 2024_start', 'Q2 2024_end').
5. If the model or module doesn't exist or query is impossible, return: {{"error": "explanation"}}
"""

        # Call Claude API
        url = 'https://api.anthropic.com/v1/messages'
        headers = {
            'x-api-key': api_key,
            'anthropic-version': '2023-06-01',
            'content-type': 'application/json'
        }
        data = {
            'model': 'claude-3-5-sonnet-20241022',
            'max_tokens': 2000,
            'system': system_prompt,
            'messages': [
                {'role': 'user', 'content': question}
            ]
        }

        try:
            res = requests.post(url, headers=headers, json=data, timeout=15)
            if res.status_code != 200:
                return {'error': _("Claude API returned error code %s: %s") % (res.status_code, res.text)}
            
            res_data = res.json()
            content = res_data.get('content', [{}])[0].get('text', '')
        except Exception as e:
            return {'error': _("Failed to communicate with Claude: %s") % str(e)}

        # JSON Safety Wrapper & Extractor
        parsed_payload = self._extract_json(content)
        if not parsed_payload:
            return {'error': _("Claude did not return a valid JSON payload. Response: %s") % content}

        if 'error' in parsed_payload:
            return {'error': parsed_payload['error']}

        # Build and execute query
        return self.build_and_execute(parsed_payload)

    def _extract_json(self, response_text):
        if not response_text:
            return {}
        try:
            return json.loads(response_text.strip())
        except json.JSONDecodeError:
            pass

        # Try markdown code blocks
        match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL | re.IGNORECASE)
        if match:
            try:
                return json.loads(match.group(1).strip())
            except json.JSONDecodeError:
                pass

        # Try first { and last }
        start = response_text.find('{')
        end = response_text.rfind('}')
        if start != -1 and end != -1:
            try:
                return json.loads(response_text[start:end+1].strip())
            except json.JSONDecodeError:
                pass

        return {}
