{
    "name": "AI Query Assistant",
    "version": "16.0.1.0.0",
    "author": "Sebin Thomas",
    "category": "Tools",
    "summary": "Natural language query assistant for Odoo 13‑18",
    "description": """AI-powered natural language query assistant.

Convert plain English queries into Odoo ORM calls and return results as JSON and HTML tables.
Supports Odoo 13 through 18 via dynamic version mapping.
""",
    "depends": ["base"],
    "data": [
        "security/ir.model.access.csv",
        "views/ai_query_settings_views.xml",
        "views/result_template.xml"
    ],
    "assets": {
        "web.assets_backend": [
            "odoo_ai_query/static/src/css/systray_search.css",
            "odoo_ai_query/static/src/xml/systray_search.xml",
            "odoo_ai_query/static/src/js/systray_search.js"
        ]
    },
    "installable": True,
    "application": False,
    "auto_install": False
}
