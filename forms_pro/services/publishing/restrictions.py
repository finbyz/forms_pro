"""
DocTypes a form may never write to.

A form creates records on behalf of whoever fills it in -- often an anonymous
visitor. Pointed at `User`, it creates accounts; at `Role` or `System
Settings`, it changes who can do what. The publish validator held this list,
but nothing ever ran the validator, so a form targeting `User` was published
and taking submissions on this site.

The check is enforced at both ends: publishing refuses a restricted target, and
so does submitting, which also covers a form that was published before this
existed.
"""

import frappe
from frappe import _

RESTRICTED_TARGETS = frozenset(
    {
        "User",
        "Role",
        "Role Profile",
        "Has Role",
        "User Permission",
        "DocShare",
        "System Settings",
        "DocType",
        "Custom Field",
        "Property Setter",
        "Server Script",
        "Client Script",
        "OAuth Client",
        "Installed Applications",
        "Email Account",
        "API Key",
        "File",
    }
)


def target_problem(doctype: str | None) -> str | None:
    """Why a form may not write to this DocType, or None when it may."""
    if not doctype:
        return None
    if doctype in RESTRICTED_TARGETS:
        return _("{0} is a restricted DocType and cannot be written to by a form.").format(doctype)
    if not frappe.db.exists("DocType", doctype):
        return _("Target DocType {0} does not exist.").format(doctype)
    meta = frappe.get_meta(doctype)
    if meta.issingle:
        return _("{0} is a Single DocType and cannot be written to by a form.").format(doctype)
    if meta.istable:
        return _("{0} is a child table and cannot be a form's target on its own.").format(doctype)
    return None


def assert_target_allowed(doctype: str | None) -> None:
    if problem := target_problem(doctype):
        frappe.throw(problem, frappe.PermissionError)
