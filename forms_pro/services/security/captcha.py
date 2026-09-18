"""reCAPTCHA v3 verification service for Forms Pro."""
from __future__ import annotations

import frappe


def get_settings() -> dict:
    """Get Forms Pro Settings as a dict (cached)."""
    return frappe.cache.hget("forms_pro_settings", "main",
        generator=lambda: frappe.get_doc("Forms Pro Settings").as_dict())


def is_enabled(form_captcha: int | None = None) -> bool:
    """Check if CAPTCHA is enabled globally or for a specific form."""
    settings = get_settings()
    if form_captcha is not None:
        return bool(form_captcha)
    return bool(settings.get("require_captcha_for_public_forms", 1))


def get_site_key() -> str | None:
    return get_settings().get("recaptcha_site_key")


def verify(token: str, action: str = "submit") -> bool:
    """Verify a reCAPTCHA v3 token. Returns True if valid."""
    if not token:
        return False

    settings = get_settings()
    secret = settings.get("recaptcha_secret_key")
    if not secret:
        frappe.log_error("reCAPTCHA secret key not configured", "Forms Pro CAPTCHA")
        return False

    threshold = float(settings.get("default_score_threshold", 0.5))

    try:
        import requests
        resp = requests.post(
            "https://www.google.com/recaptcha/api/siteverify",
            data={"secret": secret, "response": token},
            timeout=5,
        )
        result = resp.json()
        if not result.get("success"):
            frappe.log_error(f"reCAPTCHA verification failed: {result.get('error-codes')}", "Forms Pro CAPTCHA")
            return False
        score = result.get("score", 0)
        return score >= threshold
    except Exception as e:
        frappe.log_error(f"reCAPTCHA request failed: {e}", "Forms Pro CAPTCHA")
        return False