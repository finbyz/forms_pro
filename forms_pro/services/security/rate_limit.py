"""Rate limiting service for public form endpoints."""
from __future__ import annotations

import frappe

RATE_LIMIT_KEY = "forms_pro_rate_limit"


def check(identifier: str, max_requests: int = 10, window_seconds: int = 60) -> bool:
    """Check if rate limit is exceeded. Returns True if allowed."""
    cache_key = f"{RATE_LIMIT_KEY}:{identifier}"

    try:
        count = frappe.cache.get_value(cache_key) or 0
        if int(count) >= max_requests:
            return False
        frappe.cache.set_value(cache_key, int(count) + 1, expires_in_sec=window_seconds)
        return True
    except Exception:
        return True


def for_submit(route: str) -> bool:
    return check(f"submit:{route}", max_requests=20, window_seconds=60)


def for_link_search(route: str) -> bool:
    return check(f"link_search:{route}", max_requests=60, window_seconds=60)


def for_upload(form_id: str) -> bool:
    return check(f"upload:{form_id}", max_requests=30, window_seconds=60)