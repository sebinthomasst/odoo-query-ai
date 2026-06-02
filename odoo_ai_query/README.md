# Odoo AI Query Assistant (`odoo_ai_query`)

An intelligent business data assistant embedded inside Odoo. It converts natural language business questions into safe, optimized Odoo ORM queries, executes them server-side, and returns clean, formatted results and gorgeous, interactive HTML tables.

---

## 🌟 Features

- **Natural Language → Odoo ORM Query**: Ask questions in plain English and retrieve real-time ERP data.
- **Cross-Domain Support**: Complete support for Sales, Accounting, Inventory, CRM, HR/Payroll, and Purchase.
- **Dynamic Version Compatibility (Odoo 13–18)**: Built-in dynamic version-mapping for critical models (Invoice, Analytic, Stock, Website Sale, etc.). Detects Odoo major version at runtime automatically!
- **Relational Field Traversal**: Supports dot notation in query field lists (e.g., `partner_id.country_id.name`) and parses it securely.
- **Smart Date Parsing**: Resolves natural language date terms (`today`, `this month`, `last quarter`, `YTD`, `Q2 2024`) with proper range boundaries dynamically on execution.
- **Ultimate Safety & Security**:
  - Auto-applies standard Odoo record rules and access control rights.
  - Multi-company filter (`company_id`) is automatically injected for the active user.
  - Strict payroll/HR data group check (requires `hr.group_hr_manager`).
  - Sensitive models (passwords, configurations) are securely blacklisted.
  - Prevents broad queries (`>10k` records) automatically.
  - No `sudo()` usage ensures standard user permissions are strictly followed.

---

## 📂 Module Structure

```
odoo_ai_query/
├─ __init__.py
├─ __manifest__.py
├─ README.md
├─ controllers/
│   ├─ __init__.py
│   └─ main.py                # REST JSON-RPC Endpoint /ai_query/execute
├─ models/
│   ├─ __init__.py
│   ├─ ai_query_settings.py   # Secure configuration (Anthropic API Key & Limits)
│   └─ query_builder.py       # Core ORM query construction, safety checks & formatting
├─ security/
│   └─ ir.model.access.csv    # Admin settings permissions
├─ tests/
│   ├─ __init__.py
│   └─ test_query_controller.py  # Unit & Integration tests for all rules
└─ views/
    ├─ ai_query_settings_views.xml  # Premium Configuration Settings Page
    └─ result_template.xml          # Outfit/Inter typography QWeb results template
```

---

## ⚙️ Configuration & Installation

1. Copy the `odoo_ai_query/` directory into your Odoo `addons` path.
2. Log into Odoo as an Administrator, activate **Developer Mode**, and go to **Apps → Update Apps List**.
3. Search for **AI Query Assistant** and click **Install**.
4. Go to **Settings → Technical / Administration → AI Query Settings** to configure your credentials:
   - **Anthropic API Key**: Enter your key securely (stores in config parameter).
   - **Default Limit**: Standard 100 rows unless specified.
   - **Max Limit**: Strictly caps requests to safeguard database performance.

---

## 🚀 JSON-RPC REST Endpoint Usage

The module exposes a secure controller endpoint:
- **URL**: `POST /ai_query/execute`
- **Auth**: `'user'` (Requires authenticated user session)
- **Content-Type**: `application/json`

### Sample Request
```json
{
  "jsonrpc": "2.0",
  "method": "call",
  "params": {
    "model": "sale.order",
    "domain": [
      ["state", "=", "sale"],
      ["date_order", ">=", "this month"]
    ],
    "fields": ["name", "partner_id.name", "amount_total", "date_order"],
    "limit": 10,
    "order": "amount_total desc"
  }
}
```

### Sample Response
```json
{
  "jsonrpc": "2.0",
  "id": null,
  "result": {
    "understood_as": "Top 10 sales orders confirmed this month by revenue",
    "model": "sale.order",
    "result_count": 1,
    "data": [
      {
        "name": "S00012",
        "partner_id.name": "Deco Addict",
        "amount_total": 4500.0,
        "date_order": "2026-06-02"
      }
    ],
    "summary": "Retrieved 1 records from sale.order.",
    "currency": "USD",
    "generated_at": "2026-06-02 06:20:00",
    "pagination": {
      "limit": 10,
      "offset": 0,
      "has_more": false
    },
    "html": "<div class=\"table-responsive\" ...> ... </table> </div>"
  }
}
```

---

## 🧪 Running Tests

To run the automated test suite, execute:
```bash
odoo-bin -c your_config.conf -i odoo_ai_query --test-enable
```

---

## 📜 License
This module is licensed under the **LGPL-3** License. Developed and maintained by **Sebin Thomas**.
