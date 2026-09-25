"""Publishing a form.

The builder edits a draft. Visitors are served an immutable snapshot
(FP Form Version) chosen by Form.active_version, so editing a live form never
changes what the public sees until it is explicitly published again.
"""

import frappe
from frappe import _

from forms_pro.services.publishing.compiler import FormCompiler


def _require_write(form_id: str) -> None:
    if not frappe.has_permission("Form", "write", form_id):
        frappe.throw(_("You do not have write access to this form"), frappe.PermissionError)


def _draft_hash(form_id: str) -> str:
    return FormCompiler(form_id).compile()["schema_hash"]


@frappe.whitelist()
def get_publish_state(form_id: str) -> dict:
    """
    Whether the draft differs from what visitors are currently served.

    `has_unpublished_changes` drives the "Update published form" button: it
    compares the hash of the current draft against the published snapshot.
    """
    if not frappe.has_permission("Form", "read", form_id):
        frappe.throw(_("You do not have read access to this form"), frappe.PermissionError)

    form = frappe.get_doc("Form", form_id)
    active = form.active_version

    published_hash = (
        frappe.db.get_value("FP Form Version", active, "schema_hash") if active else None
    )
    version_number = (
        frappe.db.get_value("FP Form Version", active, "version_number") if active else None
    )

    try:
        draft_hash = _draft_hash(form_id)
    except Exception:
        # Never let a compile error block the builder from loading.
        frappe.log_error(frappe.get_traceback(), "Forms Pro publish state")
        draft_hash = None

    return {
        "is_published": bool(form.is_published),
        "active_version": active,
        "version_number": version_number,
        "draft_hash": draft_hash,
        "published_hash": published_hash,
        "has_unpublished_changes": bool(
            form.is_published and draft_hash and draft_hash != published_hash
        ),
        "never_published": not active,
    }


@frappe.whitelist(methods=["POST"])
def publish_form(form_id: str) -> dict:
    """Compile the draft into a new version and serve it to visitors."""
    _require_write(form_id)

    version = FormCompiler(form_id).publish()
    frappe.db.commit()  # nosemgrep: frappe-semgrep-rules.rules.frappe-manual-commit - publishing must be durable before the UI reports success

    return get_publish_state(form_id)


@frappe.whitelist(methods=["POST"])
def unpublish_form(form_id: str) -> dict:
    """
    Take the form offline.

    The active version is kept so republishing restores the same snapshot
    rather than silently promoting whatever the draft happens to be.
    """
    _require_write(form_id)

    form = frappe.get_doc("Form", form_id)
    form.db_set("is_published", 0)
    form.db_set("status", "Draft")
    frappe.db.commit()  # nosemgrep: frappe-semgrep-rules.rules.frappe-manual-commit - keep UI state and stored state in step

    return get_publish_state(form_id)
