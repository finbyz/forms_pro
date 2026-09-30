"""
Who may open and submit a form -- decided on the server.

A form's Access Mode was only ever checked by the browser: the Vue router sent
a signed-out visitor to /login for a "Requires Login" form. The API behind it
served the form and accepted submissions from anyone who called it directly,
so the setting protected nothing (FP-SEC-07).

Every public entry point -- loading the form, submitting or saving a draft,
uploading a file for it -- now asks this module.

  Public          anyone
  Requires Login  anyone signed in
  Internal Only   desk users (System Users) only
"""

import frappe
from frappe import _

PUBLIC = "Public"
REQUIRES_LOGIN = "Requires Login"
INTERNAL_ONLY = "Internal Only"


def access_mode(form) -> str:
    """The form's mode, reading older forms that only carry `login_required`."""
    mode = (form.get("access_mode") if hasattr(form, "get") else getattr(form, "access_mode", None))
    if mode in (PUBLIC, REQUIRES_LOGIN, INTERNAL_ONLY):
        return mode
    login_required = form.get("login_required") if hasattr(form, "get") else getattr(form, "login_required", 0)
    return REQUIRES_LOGIN if login_required else PUBLIC


def can_access(form, user: str | None = None) -> bool:
    user = user or frappe.session.user
    mode = access_mode(form)
    if mode == PUBLIC:
        return True
    if user == "Guest":
        return False
    if mode == INTERNAL_ONLY:
        return frappe.get_cached_value("User", user, "user_type") == "System User"
    return True


def assert_can_access(form, user: str | None = None) -> None:
    """Refuse the current user if the form's Access Mode does not admit them."""
    if can_access(form, user):
        return
    user = user or frappe.session.user
    if user == "Guest":
        frappe.throw(_("Please sign in to open this form."), frappe.PermissionError)
    frappe.throw(_("This form is only available to internal users."), frappe.PermissionError)
