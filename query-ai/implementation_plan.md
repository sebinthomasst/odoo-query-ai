# Implementation Plan for Odoo AI Query Assistant Addon

## Goal
Provide a complete Odoo addon `odoo_ai_query` that exposes a REST endpoint `/ai_query/execute` to receive natural‑language questions, translate them into safe ORM queries (supporting Odoo 13‑18), execute them server‑side and return a structured JSON response with an HTML table rendering.

## High‑Level Architecture
- **Controller** (`controllers/main.py`): receives JSON payload, validates, calls the query builder, executes the query and returns formatted response.
- **Query Builder** (`models/query_builder.py`):
  - Detects Odoo major version.
  - Maps version‑specific model names (invoice, analytic, stock, etc.).
  - Applies mandatory filters (company, HR group checks, limit clamping, safety rules).
  - Chooses `search_read` vs `read_group` based on `group_by`.
- **Settings Model** (`models/ai_query_settings.py`): stores LLM API key, default/max limits, and optional configuration.
- **QWeb Template** (`views/result_template.xml`): renders the `data` part as an attractive HTML table (currency formatting, right‑aligned monetary columns, Indian number grouping).
- **Security** (`security/ir.model.access.csv`): restricts settings to admin users.
- **Menu / Form View** (`views/ai_query_settings_views.xml`): UI for configuring the API key under *Settings → AI Query*.
- **Manifest** (`__manifest__.py`): declares dependencies (`base`, `web`), version compatibility, assets, and description.

## File / Directory Structure
```
odoo_ai_query/
├─ __init__.py
├─ __manifest__.py
├─ controllers/
│   ├─ __init__.py
│   └─ main.py
├─ models/
│   ├─ __init__.py
│   ├─ ai_query_settings.py
│   └─ query_builder.py
├─ security/
│   └─ ir.model.access.csv
├─ views/
│   ├─ ai_query_settings_views.xml
│   └─ result_template.xml
└─ static/ (optional for icons)
```

## Detailed Implementation Steps
1. **Create module skeleton** – already have `odoo_ai_query/__init__.py`. Add sub‑folders and empty `__init__` files.
2. **Manifest (`__manifest__.py`)** – include:
   - `name`, `version`, `category`, `summary`, `description` (copy from README).
   - `depends`: `["base", "web"]`.
   - `data`: list of XML files (security, views, manifest). 
   - `application`: `False`.
3. **Controllers**
   - `controllers/__init__.py` imports `main`.
   - `controllers/main.py`:
     ```python
     from odoo import http, fields, _, api
     from odoo.http import request
     import json

     class AIQueryController(http.Controller):
         @http.route('/ai_query/execute', type='json', auth='user', methods=['POST'])
         def execute(self, **payload):
             # payload validation
             required = ['model', 'domain']
             for k in required:
                 if k not in payload:
                     return {'error': _('Missing required key %s') % k}

             env = request.env
             qb = env['ir.model.data'].sudo()._get_query_builder()  # placeholder helper
             # Use our QueryBuilder utility
             builder = env['ai.query.builder']
             data = builder.build_and_execute(payload)
             return data
     ```
   - The controller will delegate all heavy lifting to the `ai.query.builder` model.
4. **Settings Model (`models/ai_query_settings.py`)**
   ```python
   class AIQuerySettings(models.TransientModel):
       _name = 'ai.query.settings'
       _description = 'AI Query Assistant Settings'

       api_key = fields.Char(string='Anthropic API Key')
       default_limit = fields.Integer(string='Default limit', default=100)
       max_limit = fields.Integer(string='Maximum limit', default=500)
   ```
   - Provide a method to fetch/store values in `ir.config_parameter` for persistence.
5. **Query Builder Model (`models/query_builder.py`)**
   ```python
   class AIQueryBuilder(models.AbstractModel):
       _name = 'ai.query.builder'
       _description = 'Helper to translate NL queries to ORM calls'

       def _detect_version(self, env):
           # Returns major int, e.g., 13,14,...
           version = env['ir.module.module']._search([('name', '=', 'base')], limit=1)
           # fallback using tools.config if needed
           return int(tools.config['server_version'].split('.')[0])

       def _model_map(self, model_name, version):
           mapping = {
               'account.invoice': {13: 'account.invoice', 14: 'account.invoice', 15: 'account.move', 16: 'account.move', 17: 'account.move', 18: 'account.move'},
               'account.analytic.account': {13: 'account.analytic.account', 14: 'account.analytic.account', 15: 'account.analytic.account', 16: 'account.analytic.account', 17: 'account.analytic.plan', 18: 'account.analytic.plan'},
               'stock.move.line': {13: 'stock.move.line', 14: 'stock.move.line', 15: 'stock.move.line', 16: 'stock.move.line', 17: 'stock.valuation.layer', 18: 'stock.valuation.layer'},
           }
           return mapping.get(model_name, {}).get(version, model_name)

       def _apply_company_filter(self, domain, env):
           company_ids = env.user.company_ids.ids
           return domain + [('company_id', 'in', company_ids)]

       def _enforce_limit(self, requested, settings):
           max_allowed = settings.max_limit or 500
           return min(requested or settings.default_limit, max_allowed)

       def _check_hr_permission(self, env):
           hr_group = env.ref('hr.group_hr_manager', raise_if_not_found=False)
           if hr_group and hr_group.id not in env.user.groups_id.ids:
               raise AccessError(_('You are not allowed to query HR / Payroll data'))

       def build_and_execute(self, payload):
           env = request.env
           settings = env['ai.query.settings'].search([], limit=1)
           version = self._detect_version(env)

           model_name = self._model_map(payload.get('model'), version)
           model = env[model_name]

           domain = payload.get('domain', [])
           domain = self._apply_company_filter(domain, env)

           # HR safety
           if model_name.startswith('hr.'):
               self._check_hr_permission(env)

           limit = self._enforce_limit(payload.get('limit'), settings)

           fields = payload.get('fields', [])
           order = payload.get('order')
           group_by = payload.get('group_by')

           if group_by:
               # read_group path
               result = model.read_group(domain, fields, group_by, offset=0, limit=limit, orderby=order)
           else:
               result = model.search_read(domain, fields, offset=0, limit=limit, order=order)

           # pagination hint
           total = model.search_count(domain)
           has_more = total > limit

           response = {
               'understood_as': payload.get('understood_as', ''),
               'model': model_name,
               'result_count': len(result),
               'data': result,
               'summary': '',
               'currency': env.user.company_id.currency_id.name,
               'generated_at': fields.Datetime.now(),
               'pagination': {'limit': limit, 'offset': 0, 'has_more': has_more},
           }
           # Render HTML using QWeb
           response['html'] = request.env['ir.ui.view']._render_template('odoo_ai_query.result_template', {'data': result, 'currency': response['currency']})
           return response
   ```
6. **QWeb Template (`views/result_template.xml`)** – create a table with proper formatting, using `t-foreach`.
   ```xml
   <template id="result_template" inherit_id="web.standard_layout">
     <t t-name="odoo_ai_query.result_template">
       <table class="o_list_view table table-hover" style="width:100%;">
         <thead>
           <tr>
             <t t-foreach="data[0].keys()" t-as="col">
               <th><t t-esc="col"/></th>
             </t>
           </tr>
         </thead>
         <tbody>
           <t t-foreach="data" t-as="row">
             <tr>
               <t t-foreach="row.values()" t-as="val">
                 <td t-attf-class="{{ 'text-right' if isinstance(val, (int, float)) else '' }}">
                   <t t-esc="val"/>
                 </td>
               </t>
             </tr>
           </t>
         </tbody>
       </table>
     </t>
   </template>
   ```
7. **Security (`security/ir.model.access.csv`)** – allow only admin (`base.group_system`) to manage settings.
   ```csv
   id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
   access_ai_query_settings,access_ai_query_settings,model_ai_query_settings,base.group_system,1,1,1,0
   ```
8. **Views (`views/ai_query_settings_views.xml`)** – form view and menu.
   ```xml
   <odoo>
     <record id="view_ai_query_settings_form" model="ir.ui.view">
       <field name="name">ai.query.settings.form</field>
       <field name="model">ai.query.settings</field>
       <field name="arch" type="xml">
         <form string="AI Query Assistant Settings">
           <group>
             <field name="api_key" password="True"/>
             <field name="default_limit"/>
             <field name="max_limit"/>
           </group>
         </form>
       </field>
     </record>

     <menuitem id="menu_ai_query_root" name="AI Query" parent="base.menu_administration" sequence="20"/>
     <menuitem id="menu_ai_query_settings" name="Settings" parent="menu_ai_query_root" action="action_ai_query_settings"/>

     <record id="action_ai_query_settings" model="ir.actions.act_window">
       <field name="name">AI Query Settings</field>
       <field name="res_model">ai.query.settings</field>
       <field name="view_mode">form</field>
       <field name="target">inline</field>
     </record>
   </odoo>
   ```
9. **Testing** – create a simple test that posts a payload to `/ai_query/execute` and asserts keys exist.
10. **Documentation** – add README details, usage example.

## Open Questions (need clarification)
- **LLM integration**: Should we implement the NL→ORM translation now (e.g., call Anthropic Claude) or keep it as a placeholder (`NotImplementedError`) for later?
- **User UI**: Do you want a front‑end widget inside Odoo where users can type their natural language query, or is the pure JSON‑RPC endpoint sufficient?
- **Menu placement**: Under *Settings* (technical) or *Administration*?
- **Additional restricted models** beyond HR/payroll (e.g., accounting journals) that need group checks?

## Verification Plan
1. **Module load** – run `odoo -i odoo_ai_query` in a test database; ensure no import errors.
2. **Endpoint test** – use `curl` with a minimal payload:
   ```json
   {"model": "sale.order", "domain": [], "fields": ["name","amount_total"], "limit": 5}
   ```
   Verify JSON response includes `data`, `html`, correct pagination.
3. **Permission checks** – attempt HR query as a non‑HR user; expect error.
4. **HTML rendering** – open the rendered template via Odoo UI (e.g., a menu action that calls the controller) and confirm table styling.
5. **Unit tests** – run `odoo test -d test_db -i odoo_ai_query` and ensure all tests pass.

*Awaiting your approval and clarification on the open questions before proceeding with code generation.*
