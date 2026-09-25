from contextlib import contextmanager
from typing import Literal

import frappe
from frappe import _
from frappe.core.doctype.access_log.access_log import make_access_log
from frappe.core.doctype.data_export.exporter import DataExporter
from werkzeug.utils import secure_filename

from forms_pro.forms_pro.doctype.form.form import Form
from forms_pro.utils.permissions import require_permission

_SUPPORTED_FILE_TYPES = ("CSV", "Excel")


@contextmanager
def _as_administrator():
    """
    Run a block as Administrator inside a web request, leaving the caller's
    session exactly as it was.

    `frappe.set_user` is built for background jobs, not web requests. Besides
    swapping the user it overwrites `local.session.sid` with the username,
    replaces `local.session.data` with an empty dict, and clears
    `local.form_dict`. And `frappe.local.session` *is* the Session object's own
    `data` (frappe/sessions.py sets `frappe.local.session = self.data`), so at
    the end of the request `Session.update()` would write to a row keyed
    `sid="Administrator"` carrying empty session data. The real session loses
    `last_updated`, the next request treats it as expired, deletes the row, and
    the user is logged out.

    Everything `set_user` clobbers is snapshotted here and restored on the way
    out, including `form_dict` -- which holds the request arguments and was
    previously left empty for the rest of the request.
    """
    saved_user = frappe.session.user
    saved_sid = frappe.local.session.sid
    saved_data = frappe.local.session.data
    saved_form_dict = frappe.local.form_dict
    try:
        # Authorization is enforced by the caller via has_permission("Form", "write", ...).
        frappe.set_user("Administrator")  # nosemgrep: frappe-semgrep-rules.rules.security.frappe-setuser
        yield
    finally:
        frappe.set_user(saved_user)  # nosemgrep: frappe-semgrep-rules.rules.security.frappe-setuser
        frappe.local.session.sid = saved_sid
        frappe.local.session.data = saved_data
        frappe.local.form_dict = saved_form_dict
@frappe.whitelist()
@require_permission("Form", "write", param="form_id")
def export_submissions(form_id: str, file_type: Literal["CSV", "Excel"] = "CSV") -> None:
    """
    Export submissions for a form as a CSV or XLSX download.

    Permission model: gated on `write` on the Form doctype only.
    Frappe's `DataExporter` enforces `can_export` on the linked DocType,
    which our app deliberately does not grant at the role level (Forms Pro
    permissions live on the Form, not on the linked DocType). To bridge
    that gap we run the exporter as Administrator and restore the original
    session user in `finally`. The Form-level permission check above is
    the real authorization gate.
    """
    # `Literal` is not enforced at runtime; validate explicitly.
    if file_type not in _SUPPORTED_FILE_TYPES:
        frappe.throw(
            _("Unsupported file_type {0}. Allowed: {1}.").format(file_type, ", ".join(_SUPPORTED_FILE_TYPES)),
            frappe.ValidationError,
        )

    form: Form = frappe.get_doc("Form", form_id)
    target_doctype = form.target_doctype

    columns = [
        "name",
        "creation",
        "owner",
        "fp_submission_status",
        *[field.fieldname for field in form.fields if field.stores_value],
    ]
    select_columns = {target_doctype: columns}

    # Audit the export under the real (non-Admin) user before the swap.
    make_access_log(
        doctype=target_doctype,
        file_type=file_type,
        columns=frappe.as_json(columns),
        method="forms_pro.api.export.export_submissions",
    )

    try:
        # The swap bypasses `can_export` on the linked DocType, which Forms Pro
        # deliberately does not grant at the role level; the Form-level check
        # above is the real authorization gate.
        with _as_administrator():
            exporter = DataExporter(
                doctype=target_doctype,
                all_doctypes=False,
                with_data=True,
                select_columns=frappe.as_json(select_columns),
                filters=frappe.as_json({"fp_linked_form": form_id}),
                file_type=file_type,
                export_without_column_meta=True,
            )
            exporter.build_response()
            safe_title = secure_filename(form.title or "") or form_id
            timestamp = frappe.utils.now_datetime().strftime("%Y-%m-%d_%H%M%S")
            base_name = f"Submissions_{safe_title}_{timestamp}"
            frappe.response["doctype"] = base_name
            if file_type == "Excel":
                frappe.response["filename"] = f"{base_name}.xlsx"
    except Exception as e:
        frappe.log_error(title="export_submissions: failed to export submissions", message=str(e))
        raise e
