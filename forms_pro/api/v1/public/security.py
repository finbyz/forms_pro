"""Public-endpoint guards: CAPTCHA and rate limiting.

The CAPTCHA logic itself lives in forms_pro.services.security.captcha; this
module only turns its result into the HTTP-facing error.
"""

import frappe
from frappe import _

from forms_pro.services.security import captcha as captcha_service

RATE_LIMIT_PER_MINUTE = 10


def verify_captcha(token: str | None, action: str = "submit", form_captcha: int | None = None):
    """
    Verify a submission's CAPTCHA token.

    Returns the score when verification passes, or None when CAPTCHA is turned
    off. Throws PermissionError otherwise.
    """
    if not captcha_service.is_enabled(form_captcha):
        return None

    try:
        return captcha_service.verify(token, action=action)
    except captcha_service.CaptchaError as exc:
        frappe.throw(_(str(exc)), exc=frappe.PermissionError)


def check_rate_limit(route: str):
    """Cap submissions per IP per form so a public endpoint can't be hammered."""
    ip = frappe.local.request_ip
    cache_key = f"forms_pro_rate_limit:{route}:{ip}"

    count = frappe.cache().get_value(cache_key) or 0
    if int(count) >= RATE_LIMIT_PER_MINUTE:
        frappe.throw(
            _("Too many requests. Please try again later."),
            exc=frappe.PermissionError,
        )

    frappe.cache().set_value(cache_key, int(count) + 1, expires_in_sec=60)
