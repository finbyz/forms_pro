import json
import re
from typing import Any

from urllib.parse import urlparse

import frappe
from frappe import _
from forms_pro.services.submissions.processor import SubmissionProcessor
from frappe.share import add_docshare

from forms_pro.forms_pro.doctype.form.form import Form
from forms_pro.forms_pro.doctype.form_field.form_field import _DISPLAY_ONLY_FIELDTYPES
from forms_pro.utils.form_generator import SubmissionStatus
from forms_pro.utils.permissions import require_permission
from forms_pro.api.v1.public.security import check_rate_limit, verify_captcha
from forms_pro.services.submissions import listing

from .schema import UserSubmissionResponse


def _coerce_field_value(value: Any, fieldtype: str) -> Any:
    """Coerce a submitted value to its comparable type, matching frontend conditionals.ts logic."""
    if value is None or value == "":
        return None
    # Matches isBoolean types in the frontend registry (Switch, Checkbox)
    if fieldtype in ("Switch", "Checkbox"):
        return bool(value)
    if fieldtype == "Number":
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
    return str(value)


def _evaluate_conditions(conditions: list[dict], form_data: dict, field_map: dict) -> bool:
    """Evaluate AND-joined conditions against submitted form data."""
    for condition in conditions:
        fieldname = condition.get("fieldname")
        operator = condition.get("operator")
        expected = condition.get("value")
        field = field_map.get(fieldname)
        if not field:
            return False
        actual = _coerce_field_value(form_data.get(fieldname), field.fieldtype)
        # Coerce the condition's expected value through the same function so
        # types match — avoids str(True)=="True" vs "true" mismatches and
        # str(3.0)=="3.0" vs "3" mismatches for Number fields.
        expected_coerced = _coerce_field_value(expected, field.fieldtype)
        if operator == "Is" and actual != expected_coerced:
            return False
        if operator == "Is Not" and actual == expected_coerced:
            return False
        if operator == "Is Empty" and actual is not None and actual != "":
            return False
        if operator == "Is Not Empty" and (actual is None or actual == ""):
            return False
    return True


# Format checks mirror the client, because submit_form_response is public and a
# direct API call never runs the browser validation.


def _format_error(field, value) -> str | None:
    if value in (None, "", []):
        return None

    text = str(value).strip()

    if field.fieldtype == "Email":
        # Use Frappe's own validator so a form accepts exactly what the rest of
        # the framework does (requires an @ and a dotted domain).
        from frappe.utils import validate_email_address

        if not validate_email_address(text):
            return _("{0} must be a valid email address").format(field.label)

    if field.fieldtype == "Phone":
        digits = re.sub(r"\D", "", text)
        if not (6 <= len(digits) <= 15):
            return _("{0} must be a valid phone number").format(field.label)

    if field.fieldtype == "URL":
        # Permissive on the scheme -- people type "example.com" -- but the host
        # has to look like a host. The client checks the same shape.
        candidate = text if "://" in text else f"https://{text}"
        parsed = urlparse(candidate)
        if not parsed.netloc or "." not in parsed.netloc:
            return _("{0} must be a valid URL").format(field.label)

    if field.fieldtype == "Number":
        try:
            float(text)
        except (TypeError, ValueError):
            return _("{0} must be a number").format(field.label)

    return None


def _validate_form_response(form: "Form", form_data: dict) -> None:
    """
    Validate required and conditionally-required fields server-side.

    Mirrors the shouldFieldBeVisible / shouldFieldBeRequired logic in
    frontend/src/utils/conditionals.ts so that direct API calls cannot
    bypass frontend validation.
    """
    field_map = {f.fieldname: f for f in form.fields}
    errors: list[str] = []

    for field in form.fields:
        if field.fieldtype in _DISPLAY_ONLY_FIELDTYPES:
            continue
        is_visible = not field.hidden
        # A read-only field is displayed but not editable, so it can never be
        # something the visitor failed to fill in.
        is_required = bool(field.reqd) and not getattr(field, "read_only", 0)

        for other in form.fields:
            if not other.conditional_logic:
                continue
            try:
                logic = json.loads(other.conditional_logic)
            except (json.JSONDecodeError, TypeError):
                continue

            if logic.get("target_field") != field.fieldname:
                continue

            conditions_met = _evaluate_conditions(logic.get("conditions", []), form_data, field_map)
            if conditions_met:
                action = logic.get("action")
                if action == "Show Field":
                    is_visible = True
                elif action == "Hide Field":
                    is_visible = False
                elif action == "Require Answer":
                    is_required = True

        if not is_visible:
            continue

        value = form_data.get(field.fieldname)
        is_empty = value is None or value == "" or value == []
        if is_required and is_empty:
            errors.append(_("{0} is required").format(field.label))
            continue

        problem = _format_error(field, value)
        if problem:
            errors.append(problem)

    if errors:
        frappe.throw("\n".join(errors), frappe.ValidationError)


@frappe.whitelist(allow_guest=True, methods=["POST"])  # nosemgrep: frappe-semgrep-rules.rules.security.guest-whitelisted-method
def submit_form_response(
    form_id: str,
    form_data: list[dict],
    submission_status: str = SubmissionStatus.SUBMITTED.value,
    captcha_token: str | None = None,
) -> str:
    """
    Submit a form response

    Args:
        form_id: The ID of the form
        form_data: The data of the form
        submission_status: The status of the submission: Default is `Submitted`

    Returns:
        The name of the submission
    """
    try:
        status = SubmissionStatus(submission_status)
    except ValueError:
        frappe.throw(
            _("Invalid submission status: {0}").format(submission_status),
            frappe.ValidationError,
        )

    try:
        form: Form = frappe.get_doc("Form", form_id)

        if not form.is_published:
            frappe.throw(
                _("This form is un-published, so responses are no longer being collected."),
                frappe.PermissionError,
            )

        # Guard before any work happens, so a rejected request never creates a
        # submission row or touches the target DocType. A saved draft is the
        # user's own in-progress work, so only real submissions are checked.
        check_rate_limit(form.route or form_id)
        if status == SubmissionStatus.SUBMITTED:
            verify_captcha(captcha_token, action="submit")

        form_data_dict = {item["fieldname"]: item["value"] for item in form_data}

        # Whitelist to declared form fields only
        allowed_fieldnames = {f.fieldname for f in form.fields}
        form_data_dict = {k: v for k, v in form_data_dict.items() if k in allowed_fieldnames}

        if status == SubmissionStatus.SUBMITTED:
            _validate_form_response(form, form_data_dict)

        processor = SubmissionProcessor(form_id=form_id, form_data=form_data_dict, status=status.value)
        result = processor.process()

        return result["submission_id"]
    except Exception:
        raise


@frappe.whitelist()
@require_permission("Form", "read", param="form_id")
def get_user_submissions(form_id: str) -> list[UserSubmissionResponse]:
    """
    Get the submissions for a user

    Args:
        form_id: The ID of the form

    Returns:
        A list of submissions for the user
    """
    return _list_submissions(form_id, owner=frappe.session.user)


@frappe.whitelist()
def get_submission_response(submission_id: str, doctype: str | None = None) -> dict[str, Any]:
    """
    Return one submission with its answers.

    Answers live on FP Form Submission.payload — including fields that are not
    mapped onto the target DocType (notes, ratings, repeating tables), which the
    old target-DocType lookup could never show.

    `doctype` is accepted for backwards compatibility and ignored.
    """
    submission = frappe.get_doc("FP Form Submission", submission_id)

    team = frappe.db.get_value("Form", submission.form, "linked_team_id")
    if not frappe.has_permission(doctype="FP Team", ptype="write", doc=team, user=frappe.session.user):
        frappe.throw(
            _("You do not have permission to read this form's submissions."),
            frappe.PermissionError,
        )

    try:
        answers = frappe.parse_json(submission.payload) or {}
    except Exception:
        answers = {}

    return {
        **answers,
        "name": submission.name,
        "creation": submission.creation,
        "modified": submission.modified,
        "owner": submission.owner,
        "status": submission.status,
        "target_doctype": submission.target_doctype,
        "target_name": submission.target_name,
    }


@frappe.whitelist()
def get_submission(submission_doctype: str, submission_name: str) -> dict[str, Any]:
    """
    Get a submission by name. Used usually by the form owner to view the submission details.

    Args:
        submission_name: The name of the submission

    Returns:
        The submission
    """
    submission = frappe.get_doc(submission_doctype, submission_name)

    if not frappe.has_permission(doctype=submission.doctype, ptype="read", doc=submission.name):
        frappe.throw(
            _("You do not have permission to read this submission."),
            frappe.PermissionError,
        )

    return submission.as_dict()


@frappe.whitelist()
@require_permission("Form", "read", param="form_id")
def get_all_submissions(form_id: str) -> list[UserSubmissionResponse]:
    """
    Get a form's most recent submissions.

    Kept for callers that only need a compact recent list. It is capped, because
    a form that has collected for a year must not be able to hand the browser
    every row it holds. Paged and filtered reads go through
    :func:`list_submissions`.

    Args:
        form_id: The ID of the form

    Returns:
        A list of submissions for the form
    """
    return _list_submissions(form_id, limit=listing.MAX_PAGE_LENGTH)


@frappe.whitelist()
@require_permission("Form", "read", param="form_id")
def list_submissions(
    form_id: str,
    filters=None,
    answer_filters=None,
    search: str | None = None,
    order_by: str | None = None,
    limit_start=0,
    limit_page_length=listing.DEFAULT_PAGE_LENGTH,
    fields=None,
    include_payload=False,
) -> dict:
    """One page of a form's submissions, filtered and sorted in SQL.

    ``filters`` apply to the submission's own columns, ``answer_filters`` to the
    form's questions inside the stored payload. The page is always bounded and
    ``total`` counts the filtered set, so the pager stays honest.

    Requires ``read`` on the Form; the query is pinned to it.
    """
    return listing.list_form_submissions(
        form_id,
        filters=filters,
        answer_filters=answer_filters,
        search=search,
        order_by=order_by,
        limit_start=limit_start,
        limit_page_length=limit_page_length,
        fields=fields,
        include_payload=include_payload,
    )


@frappe.whitelist()
@require_permission("Form", "read", param="form_id")
def get_submission_filter_fields(form_id: str) -> dict:
    """Every field an operator may filter this form's submissions by."""
    return listing.submission_filter_fields(form_id)


def _list_submissions(
    form_id: str, owner: str | None = None, limit: int = listing.MAX_PAGE_LENGTH
) -> list[UserSubmissionResponse]:
    """
    Read a form's submissions from FP Form Submission.

    These listings used to query the target DocType for `fp_submission_status`,
    which raises OperationalError whenever that legacy custom field is absent
    (a form pointed at Contact, or at a generated placeholder DocType) and,
    worse, returned every record of that DocType instead of this form's.
    """
    filters: dict = {"form": form_id}
    if owner:
        filters["owner"] = owner

    submissions = frappe.get_all(
        "FP Form Submission",
        filters=filters,
        fields=["name", "creation", "modified", "status", "owner"],
        order_by="creation desc",
        limit=listing.coerce_page_length(limit),
    )

    return [
        UserSubmissionResponse.model_validate(
            {
                "name": s.name,
                "creation": s.creation,
                "modified": s.modified,
                "fp_submission_status": s.status or SubmissionStatus.SUBMITTED.value,
                "owner": s.owner,
            }
        ).model_dump()
        for s in submissions
    ]


@frappe.whitelist()
def get_submission_for_document(doctype: str, docname: str) -> dict | None:
    """
    Find the form submission that produced a given document.

    Someone looking at a Contact in the desk has no way to tell it came from a
    form, let alone see the answers that were not mapped onto the record. This
    resolves the record back to its submission so the desk can link across to
    the Forms Pro submission view, where the full set of answers lives.

    Returns None when the document did not come from a form.
    """
    if not (doctype and docname):
        return None

    if not frappe.has_permission(doctype, "read", docname):
        frappe.throw(_("You do not have read access to this document"), frappe.PermissionError)

    if not frappe.get_meta(doctype).has_field("fp_linked_form"):
        return None

    form_id = frappe.db.get_value(doctype, docname, "fp_linked_form")
    if not form_id or not frappe.db.exists("Form", form_id):
        return None

    submission = frappe.db.get_value(
        "FP Form Submission",
        {"target_doctype": doctype, "target_name": docname},
        ["name", "submitted_at"],
        as_dict=True,
        order_by="creation desc",
    )

    return {
        "form": form_id,
        "form_title": frappe.db.get_value("Form", form_id, "title"),
        "submission": submission.name if submission else None,
        "submitted_at": submission.submitted_at if submission else None,
    }


@frappe.whitelist()
def reveal_password_field(doctype: str, docname: str, fieldname: str) -> str:
    """
    Show the value a visitor typed into a Password field.

    Frappe stores a Password field encrypted and hands the desk `***`, and its
    eye icon only unmasks what is being typed -- so an answer already submitted
    could not be read back at all. Storing it as plain text instead would fix
    the symptom by removing the protection, so the value stays encrypted and is
    decrypted only on request, by someone who may already read the record.

    Every reveal is written to the Access Log, because reading someone's
    submitted secret should leave a trace.
    """
    if not (doctype and docname and fieldname):
        frappe.throw(_("Document and field are required"), frappe.ValidationError)

    if not frappe.has_permission(doctype, "read", docname):
        frappe.throw(_("You do not have read access to this document"), frappe.PermissionError)

    field = frappe.get_meta(doctype).get_field(fieldname)
    if not field or field.fieldtype != "Password":
        frappe.throw(_("{0} is not a password field").format(fieldname), frappe.ValidationError)

    from frappe.core.doctype.access_log.access_log import make_access_log
    from frappe.utils.password import get_decrypted_password

    make_access_log(
        doctype=doctype,
        document=docname,
        columns=fieldname,
        method="forms_pro.api.submission.reveal_password_field",
    )

    return get_decrypted_password(doctype, docname, fieldname, raise_exception=False) or ""
