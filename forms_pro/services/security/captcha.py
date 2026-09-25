"""reCAPTCHA v3 verification service for Forms Pro.

This is the single implementation. `api/v1/public/security.py` delegates here so
there is one place that knows how the secret is read and what happens when the
configuration is incomplete.
"""

from __future__ import annotations

import frappe
import requests

VERIFY_URL = "https://www.google.com/recaptcha/api/siteverify"
VERIFY_TIMEOUT_SECONDS = 5
DEFAULT_THRESHOLD = 0.5


def get_settings():
    """Forms Pro Settings. Frappe already caches Singles, so don't re-cache it
    here — the previous version cached the document (secret included) in Redis."""
    return frappe.get_cached_doc("Forms Pro Settings")


def is_enabled(form_captcha: int | None = None) -> bool:
    """Whether CAPTCHA applies, globally or for one form."""
    if form_captcha is not None:
        return bool(form_captcha)
    return bool(get_settings().require_captcha_for_public_forms)


def get_site_key() -> str | None:
    """The public key, safe to hand to the browser."""
    return get_settings().recaptcha_site_key or None


def get_secret_key() -> str | None:
    """
    The secret must be read with get_password(). Reading it off as_dict() (as
    this module used to) returns the encrypted value, so verification against
    Google could never succeed.
    """
    return get_settings().get_password("recaptcha_secret_key", raise_exception=False)


def get_threshold() -> float:
    try:
        return float(get_settings().default_score_threshold or DEFAULT_THRESHOLD)
    except (TypeError, ValueError):
        return DEFAULT_THRESHOLD


class CaptchaError(Exception):
    """Verification could not be completed or did not pass."""


def verify(token: str | None, action: str = "submit") -> float:
    """
    Verify a reCAPTCHA v3 token and return its score.

    Raises CaptchaError when the token is missing, rejected by Google, scores
    below the threshold, or when the secret is not configured. Callers convert
    that into the user-facing error.
    """
    secret = get_secret_key()
    if not secret:
        # Fail closed. This used to return True, which meant a form with CAPTCHA
        # switched on but no keys silently accepted everything.
        frappe.log_error(
            "CAPTCHA is required but no secret key is configured in Forms Pro Settings.",
            "Forms Pro CAPTCHA",
        )
        raise CaptchaError("CAPTCHA is not configured correctly.")

    if not token:
        raise CaptchaError("CAPTCHA token is missing.")

    try:
        response = requests.post(
            VERIFY_URL,
            data={
                "secret": secret,
                "response": token,
                "remoteip": frappe.local.request_ip,
            },
            timeout=VERIFY_TIMEOUT_SECONDS,
        )
        result = response.json()
    except Exception as exc:
        # A network problem must not become a free pass.
        frappe.log_error(f"reCAPTCHA request failed: {exc}", "Forms Pro CAPTCHA")
        raise CaptchaError("Could not verify CAPTCHA. Please try again.") from exc

    if not result.get("success"):
        frappe.log_error(
            f"reCAPTCHA rejected the token: {result.get('error-codes')}",
            "Forms Pro CAPTCHA",
        )
        raise CaptchaError("CAPTCHA verification failed.")

    # v3 returns the action it was executed with; a mismatch means the token was
    # minted for something else and replayed here.
    returned_action = result.get("action")
    if action and returned_action and returned_action != action:
        frappe.log_error(
            f"reCAPTCHA action mismatch: expected {action}, got {returned_action}",
            "Forms Pro CAPTCHA",
        )
        raise CaptchaError("CAPTCHA verification failed.")

    score = float(result.get("score", 0) or 0)
    threshold = get_threshold()
    if score < threshold:
        raise CaptchaError("CAPTCHA score too low. Suspicious activity detected.")

    return score
