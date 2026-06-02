/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, useRef, useEffect } from "@odoo/owl";

class AISystraySearch extends Component {
    setup() {
        this.root = useRef("root");
        this.rpc = useService("rpc");
        
        this.state = useState({
            isOpen: false,
            query: "",
            loading: false,
            result: null,
            error: null,
        });

        // Close dropdown when clicking outside
        useEffect(
            () => {
                const onClickOutside = (ev) => {
                    if (this.state.isOpen && this.root.el && !this.root.el.contains(ev.target)) {
                        this.state.isOpen = false;
                    }
                };
                document.addEventListener("mousedown", onClickOutside);
                return () => document.removeEventListener("mousedown", onClickOutside);
            },
            () => [this.state.isOpen]
        );
    }

    toggleSearch(ev) {
        ev.stopPropagation();
        this.state.isOpen = !this.state.isOpen;
        if (this.state.isOpen) {
            this.state.error = null;
        }
    }

    closeSearch() {
        this.state.isOpen = false;
    }

    onKeydown(ev) {
        if (ev.key === "Enter") {
            ev.preventDefault();
            this.performSearch();
        }
    }

    async performSearch() {
        const queryStr = this.state.query.strip ? this.state.query.strip() : this.state.query.trim();
        if (!queryStr) {
            return;
        }

        this.state.loading = true;
        this.state.error = null;
        this.state.result = null;

        try {
            const data = await this.rpc("/ai_query/ask", {
                question: queryStr
            });

            if (data && data.error) {
                this.state.error = data.error;
            } else if (data) {
                this.state.result = data;
                // Clear input after a successful query to keep it clean
                this.state.query = "";
            } else {
                this.state.error = "No response received from the database assistant.";
            }
        } catch (err) {
            this.state.error = err.message || "An unexpected error occurred while processing your request.";
        } finally {
            this.state.loading = false;
        }
    }
}

AISystraySearch.template = "odoo_ai_query.AISystraySearch";

registry.category("systray").add("odoo_ai_query.AISystraySearch", {
    Component: AISystraySearch,
    sequence: 5,
});
