"""Rate limiting service for public form endpoints."""
from __future__ import annotations

import frappe

RATE_LIMIT_KEY = "forms_pro_rate_limit"


def check(identifier: str, max_requests: int = 10, window_seconds: int = 60) -> bool:
    """Check if rate limit is exceeded. Returns True if allowed.

    Uses Redis INCR + EXPIRE which is atomic: two concurrent requests can never
    both read the same counter value and both slip through the limit.  The old
    implementation used a read-then-write pair, so bursts of concurrent
    submissions could exceed the intended cap.
    """
    # `frappe.cache` is itself the Redis client (RedisWrapper subclasses
    # redis.Redis); there is no `.redis` attribute. Reaching for one raised on
    # every call, the except below "failed open", and the limiter allowed
    # everything. `make_key` adds the site prefix, so sites sharing a Redis do
    # not share counters.
    cache_key = frappe.cache.make_key(f"{RATE_LIMIT_KEY}:{identifier}")

    try:
        count = frappe.cache.incr(cache_key)
        if count == 1:
            # First request in this window — set the expiry.  Done after INCR
            # so the key always has a TTL even if EXPIRE was never called.
            frappe.cache.expire(cache_key, window_seconds)
        return int(count) <= max_requests
    except Exception:
        # Fail open on Redis errors — a broken cache must not take down the form.
        return True


def for_submit(route: str) -> bool:
    return check(f"submit:{route}", max_requests=20, window_seconds=60)


def for_link_search(route: str) -> bool:
    return check(f"link_search:{route}", max_requests=60, window_seconds=60)


def for_upload(form_id: str) -> bool:
    return check(f"upload:{form_id}", max_requests=30, window_seconds=60)