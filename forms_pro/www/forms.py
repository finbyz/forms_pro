import re

import frappe

no_cache = 1

SCRIPT_TAG_PATTERN = re.compile(r"\<script[^<]*\</script\>")
CLOSING_SCRIPT_TAG_PATTERN = re.compile(r"</script\>")


def get_context(context):
    csrf_token = frappe.sessions.get_csrf_token()
    frappe.db.commit()  # nosemgrep: frappe-semgrep-rules.rules.frappe-manual-commit - required to persist CSRF token before page render
    # developer mode
    context.is_developer_mode = frappe.conf.developer_mode
    context.csrf_token = csrf_token

    # Allow framing only for the public form renderer (embed use-case).
    # Builder and management routes must not be embeddable — they are admin
    # surfaces and allowing any origin to frame them is a clickjacking risk.
    #
    # The public renderer is recognised by its path, /forms/p/<route>. An
    # earlier version looked for a `?route=` query parameter instead, which the
    # embed script never sends -- so every embedded form was served with
    # X-Frame-Options: SAMEORIGIN and the browser refused to show it.
    if hasattr(frappe.local, "response_headers"):
        path = (getattr(frappe.local, "request", None) and frappe.local.request.path) or ""
        if path.startswith("/forms/p/"):
            frappe.local.response_headers.set("Content-Security-Policy", "frame-ancestors *")
            frappe.local.response_headers.set("X-Frame-Options", "ALLOWALL")

