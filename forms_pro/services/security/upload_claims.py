"""
Anonymous uploads are only accepted on behalf of a form (FP-SEC-08).

A visitor's file is filed under FP Form Submission, which is what the guest
upload allowlist in System Settings admits -- but nothing tied the upload to a
form at all. Anyone could post files with no form in sight, and since form
uploads are public (a visitor has to be able to see their own attachment), the
site doubled as anonymous file hosting.

A guest upload now has to carry a claim:

  * a token the server hands out with the form itself -- so only someone who
    could open the form gets one, Access Mode included -- signed and expiring;
  * the form it is for, which must still be published;
  * the field it is for, which must be one that takes files: an Attach field,
    a rich-text field (images and video dropped into the answer), or an Attach
    column in one of the form's tables.

Signed-in users are not asked for one: Frappe already checks their permission
to upload, and the form builder uploads images on the author's behalf.
"""

import hashlib
import hmac
import time

import frappe
from frappe import _

#: A visitor filling in a long form should not have their upload refused.
CLAIM_LIFETIME_SECONDS = 12 * 60 * 60

#: Field types an upload may be attached to.
_FILE_FIELD_TYPES = ("Attach", "Text Editor")


def _signature(form_id: str, expires: int) -> str:
    from frappe.utils.password import get_encryption_key

    key = get_encryption_key().encode()
    return hmac.new(key, f"forms-pro-upload:{form_id}:{expires}".encode(), hashlib.sha256).hexdigest()


def issue(form_id: str) -> str:
    """A claim to upload files for this form, valid for CLAIM_LIFETIME_SECONDS."""
    expires = int(time.time()) + CLAIM_LIFETIME_SECONDS
    return f"{expires}.{_signature(form_id, expires)}"


def is_valid(form_id: str, token: str) -> bool:
    try:
        expires_text, signature = (token or "").split(".", 1)
        expires = int(expires_text)
    except ValueError:
        return False
    if expires < time.time():
        return False
    return hmac.compare_digest(signature, _signature(form_id, expires))


def _file_fieldnames(form) -> set[str]:
    """Every fieldname on this form an upload may belong to."""
    names = {f.fieldname for f in form.fields if f.fieldtype in _FILE_FIELD_TYPES}
    for table in (f for f in form.fields if f.fieldtype == "Table" and f.options):
        if frappe.db.exists("DocType", table.options):
            names.update(
                df.fieldname
                for df in frappe.get_meta(table.options).fields
                if df.fieldtype in ("Attach", "Attach Image")
            )
    return names


def assert_guest_upload_allowed() -> None:
    """Refuse an anonymous upload that does not carry a valid claim for a form."""
    form_id = (frappe.form_dict.get("fp_form") or "").strip()
    token = (frappe.form_dict.get("fp_upload_token") or "").strip()
    fieldname = (frappe.form_dict.get("fp_field") or "").strip()

    refused = _("This upload is not attached to a form you can fill in. Reload the form and try again.")
    if not (form_id and token and fieldname) or not is_valid(form_id, token):
        frappe.throw(refused, frappe.PermissionError)

    form = frappe.get_doc("Form", form_id)
    if not form.is_published or form.status == "Archived":
        frappe.throw(refused, frappe.PermissionError)

    from forms_pro.services.security.access import assert_can_access
    from forms_pro.services.security.rate_limit import check

    assert_can_access(form)
    if fieldname not in _file_fieldnames(form):
        frappe.throw(refused, frappe.PermissionError)

    ip = getattr(frappe.local, "request_ip", None) or "unknown"
    if not check(f"upload:{form_id}:{ip}", max_requests=30, window_seconds=60):
        frappe.throw(_("Too many uploads. Please wait a minute and try again."), frappe.PermissionError)
