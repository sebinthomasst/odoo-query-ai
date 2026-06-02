# Implementation Plan: Claude Integration, OWL Systray Widget, and GitHub Actions

## Goal
Implement a complete natural language processing pipeline within the `odoo_ai_query` module by:
1. Adding a `/ai_query/ask` route that takes plain English, sends it to the Claude API, and translates it into an ORM query.
2. Building an OWL frontend widget + systray search bar.
3. Securely handling API credentials.
4. Structuring and committing the full codebase to `sebinthomasst/odoo-query-ai`.
5. Designing a GitHub Actions deployment workflow.

---

## Proposed Changes

### 1. Claude Integration (`controllers/main.py`)
- Add a new JSON-RPC endpoint `@http.route('/ai_query/ask', type='json', auth='user', methods=['POST'])`.
- Accept payload: `{"question": str}`.
- Fetch the secure API key from `ir.config_parameter` in `sudo()` mode (never expose the key to the client).
- Call Anthropic's Claude API (`https://api.anthropic.com/v1/messages`) using python `requests`.
- **System Prompt**: Feed Claude Odoo's compatibility matrices, key fields, aggregation guidelines, and date keywords.
- **Safety Wrapper**: Implement a robust regex-based JSON extractor to sanitize Claude's output (handling markdown backticks, conversational fluff).
- Parse the output JSON, pass the parameters directly to our `ai.query.builder` execution engine, and return the final JSON/HTML formatted response!

### 2. OWL Systray Widget (`static/src/`)
Create a custom Odoo 16 OWL component that places a search bar in the top navigation bar.
- **Files**:
  - `static/src/xml/systray_search.xml`: The template containing the search input, "Ask AI" button, a loading spinner, and a dropdown container to display query results.
  - `static/src/js/systray_search.js`: The OWL Component Javascript registering in `systray` registry.
  - `static/src/css/systray_search.css`: Beautiful, premium glassmorphism styling, hover animations, responsive table spacing.
- **Wiring**:
  - Wire search input → trigger JSON-RPC request to `/ai_query/ask` on enter or click.
  - Display standard spinner while loading.
  - Render the HTML table returned from `/ai_query/ask` directly in the dropdown using Odoo's standard `t-out` or `t-raw`.
  - Display the "understood as" query translation and dynamic summary for clarity.

### 3. API Key Security & Restricting Access
- Implement strict access control to prevent regular users from reading the `odoo_ai_query.api_key` config parameter via direct RPC.
- Explicitly block any non-admin attempts to retrieve this config.

### 4. Git & GitHub Actions
- Create a standard `.gitignore` file.
- Commit all consolidated files.
- Create a `.github/workflows/deploy.yml` file to handle automated code checking/deployment (e.g. running linting or notifying the system).

---

## Open Questions
> [!IMPORTANT]
> - Which Claude model should we default to? We propose `claude-3-5-sonnet-20241022` or `claude-3-haiku-20240307` for quick speed.
> - For GitHub Actions, do you have a target deployment server (e.g., SSH deploy to an Odoo server) or should we write a clean syntax check & release packaging workflow?

---

## Verification Plan

### Manual Verification
- Go to Settings, enter an Anthropic API Key, and save.
- Notice the new search bar in Odoo's top header.
- Type `"What are my top 5 customers by outstanding balance?"` and hit enter.
- Verify the dropdown panel renders a premium HTML table, right-aligned monetary values, currency symbol, and the natural language summary!

### Automated Verification
- Run Odoo test suite to verify tests pass.
- Git status check.
