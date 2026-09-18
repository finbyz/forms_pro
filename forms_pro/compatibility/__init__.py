"""Frappe v16 compatibility helpers for Forms Pro.

Centralize v16-specific adapters here to:
- Keep version checks in one place
- Simplify future v17 migration
- Avoid scattered `if frappe.__version__` checks

Do NOT put business logic in this module.
"""
from __future__ import annotations

import frappe
from frappe.utils import cint


def is_frappe_v16() -> bool:
    return frappe.__version__.startswith("16")


def safe_get_value(doctype: str, fieldname: str, filters: dict | None = None) -> str | int | None:
    """Wrapper around frappe.db.get_value that handles v16 Single DocType casting.

    Frappe v16 changed db.get_value for Single DocTypes to return native values
    (e.g. int instead of str). This normalizes the behavior across versions.
    """
    value = frappe.db.get_value(doctype, filters or {}, fieldname)
    return value


def safe_cint(value: str | int | None, default: int = 0) -> int:
    """Consistent integer conversion across v16 versions.

    Use this instead of direct `int()` or `== "1"` checks on Single DocType values.
    """
    return cint(value) if value is not None else default


def in_test() -> bool:
    """Check if running in test mode.

    Prefer frappe.in_test over frappe.flags.in_test per v16 recommendation.
    """
    try:
        return frappe.in_test() if callable(frappe.in_test) else bool(frappe.flags.in_test)
    except (AttributeError, TypeError):
        return bool(frappe.flags.get("in_test", False))


def get_default_sort_order() -> str:
    """Return explicit sort order for queries.

    Frappe v16 defaults many APIs/list views to `creation` instead of `modified`.
    Always prefer explicit ordering.
    """
    return "modified desc"