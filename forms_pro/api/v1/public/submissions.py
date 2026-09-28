import json
from typing import Any
from urllib.parse import urlparse

import frappe
from frappe import _
from forms_pro.utils.mapping import FormMappingEngine
from frappe.share import add_docshare

from forms_pro.forms_pro.doctype.form.form import Form
from forms_pro.forms_pro.doctype.form_field.form_field import _DISPLAY_ONLY_FIELDTYPES
from forms_pro.utils.form_generator import SubmissionStatus
from forms_pro.utils.permissions import require_permission
from forms_pro.api.v1.public.security import check_rate_limit, verify_captcha

from forms_pro.api.submission.schema import UserSubmissionResponse


def _coerce_field_value(value: Any, fieldtype: str) -> Any:
    """Coerce a submitted value to its comparable type, matching frontend conditionals.ts logic."""
    if value is None or value == "":
        return None
    # Matches isBoolean types in the frontend registry (Switch, Checkbox, Check)
    if fieldtype in ("Switch", "Checkbox", "Check"):
        if isinstance(value, str):
            v = value.strip().lower()
            return v in ("1", "true", "yes", "checked", "on")
        return bool(value)
    if fieldtype in ("Number", "Currency", "Float", "Int", "Percent"):
        try:
            if isinstance(value, str):
                value = value.replace(",", "").strip()
            return float(value)
        except (TypeError, ValueError):
            return None
    return str(value).strip()


def _evaluate_conditions(conditions: list[dict], form_data: dict, field_map: dict) -> bool:
    """Evaluate AND-joined conditions against submitted form data."""
    for condition in conditions:
        fieldname = condition.get("fieldname")
        operator = condition.get("operator")
        expected_raw = condition.get("value")
        field = field_map.get(fieldname)
        if not field:
            return False

        actual = _coerce_field_value(form_data.get(fieldname), field.fieldtype)
        expected = _coerce_field_value(expected_raw, field.fieldtype)

        is_bool = field.fieldtype in ("Switch", "Checkbox", "Check")
        is_num = isinstance(actual, (int, float)) and isinstance(expected, (int, float))

        if operator == "Is":
            if is_bool or is_num:
                if actual != expected:
                    return False
            else:
                if str(actual or "").strip().lower() != str(expected or "").strip().lower():
                    return False
        elif operator == "Is Not":
            if is_bool or is_num:
                if actual == expected:
                    return False
            else:
                if str(actual or "").strip().lower() == str(expected or "").strip().lower():
                    return False
        elif operator == "Is Empty":
            if actual is not None and actual != "" and actual is not False:
                return False
        elif operator in ("Is Not Empty", "Is Set"):
            if actual is None or actual == "" or actual is False:
                return False
        elif operator == "Contains":
            if actual is None:
                return False
            if str(expected or "").lower() not in str(actual).lower():
                return False
        elif operator == "Does Not Contain":
            if actual is not None and str(expected or "").lower() in str(actual).lower():
                return False
        elif operator == "Is Less Than":
            if actual is None or expected is None or not (actual < expected):
                return False
        elif operator == "Is Less Than Or Equal To":
            if actual is None or expected is None or not (actual <= expected):
                return False
        elif operator == "Is Greater Than":
            if actual is None or expected is None or not (actual > expected):
                return False
        elif operator == "Is Greater Than Or Equal To":
            if actual is None or expected is None or not (actual >= expected):
                return False
        elif operator == "Starts With":
            if actual is None or not str(actual).lower().startswith(str(expected or "").lower()):
                return False
        elif operator == "Does Not Start With":
            if actual is not None and str(actual).lower().startswith(str(expected or "").lower()):
                return False
        elif operator == "Ends With":
            if actual is None or not str(actual).lower().endswith(str(expected or "").lower()):
                return False
        elif operator == "Does Not End With":
            if actual is not None and str(actual).lower().endswith(str(expected or "").lower()):
                return False
    return True


def _is_step_separator(fieldtype: str) -> bool:
    return fieldtype in ("Page Break", "Tab Break", "Section Break")


def _get_governed_fieldnames(separator_fieldname: str, fields: list, trigger_fieldnames: list[str]) -> list[str]:
    """
    The fields a rule reaches when it points at a step / section.

    Targeting a step means the whole step. A rule triggered from inside the
    step it targets is self-referential -- answering the question would hide
    the question -- so it governs nothing. Kept in step with
    `getGovernedFieldnames` in frontend/src/utils/conditionals.ts; the two
    disagreeing means a field the visitor never saw is demanded on submit.
    """
    in_section = False
    fields_in_section = []
    for f in fields:
        ftype = getattr(f, "fieldtype", None) or (f.get("fieldtype") if isinstance(f, dict) else "")
        fname = getattr(f, "fieldname", None) or (f.get("fieldname") if isinstance(f, dict) else "")
        if _is_step_separator(ftype):
            if fname == separator_fieldname:
                in_section = True
                continue
            elif in_section:
                break
        elif in_section:
            fields_in_section.append(fname)

    if any(t in fields_in_section for t in trigger_fieldnames):
        return []

    return fields_in_section


def _format_error(field, value) -> str | None:
    if value in (None, "", []):
        return None

    text = str(value).strip()

    if field.fieldtype == "Email":
        from frappe.utils import validate_email_address

        if not validate_email_address(text):
            return _("{0} must be a valid email address").format(field.label)

    if field.fieldtype == "Phone":
        from frappe.utils import validate_phone_number_with_country_code

        try:
            validate_phone_number_with_country_code(text, field.label or field.fieldname)
        except Exception as e:
            msg = str(e).replace("<strong>", "").replace("</strong>", "").strip()
            return msg or _("Phone Number {0} set in field {1} is not valid.").format(
                text, field.label or field.fieldname
            )

    limit = int(getattr(field, "max_length", 0) or 0)
    if limit and len(text) > limit:
        return _("{0} must be {1} characters or fewer").format(field.label, limit)

    if field.fieldtype == "Currency":
        try:
            num = float(text.replace(",", ""))
        except (TypeError, ValueError):
            return _("{0} must be an amount").format(field.label)

        allow_neg = getattr(field, "allow_negative", 0) if not isinstance(field, dict) else field.get("allow_negative", 0)
        if isinstance(allow_neg, str):
            allow_neg = allow_neg in ("1", "true", "True")
        if not allow_neg and num < 0:
            return _("{0} cannot be negative").format(field.label)

    if field.fieldtype == "URL":
        candidate = text if "://" in text else f"https://{text}"
        parsed = urlparse(candidate)
        if not parsed.netloc or "." not in parsed.netloc:
            return _("{0} must be a valid URL").format(field.label)

    if field.fieldtype == "Number":
        try:
            num = float(text)
        except (TypeError, ValueError):
            return _("{0} must be a number").format(field.label)

        allow_neg = getattr(field, "allow_negative", 0) if not isinstance(field, dict) else field.get("allow_negative", 0)
        if isinstance(allow_neg, str):
            allow_neg = allow_neg in ("1", "true", "True")
        if not allow_neg and num < 0:
            return _("{0} cannot be negative").format(field.label)

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

        targeting_rules = []
        for other in form.fields:
            if not other.conditional_logic:
                continue
            try:
                logic = json.loads(other.conditional_logic)
            except (json.JSONDecodeError, TypeError):
                continue

            raw_target = logic.get("target_field") or other.fieldname
            targets = raw_target if isinstance(raw_target, list) else [raw_target]
            trigger_fields = [c.get("fieldname") for c in logic.get("conditions", []) if c.get("fieldname")]

            is_targeted = field.fieldname in targets
            if not is_targeted:
                for tgt in targets:
                    governed = _get_governed_fieldnames(tgt, form.fields, trigger_fields)
                    if field.fieldname in governed:
                        is_targeted = True
                        break

            if is_targeted:
                targeting_rules.append(logic)

        show_rules = [r for r in targeting_rules if r.get("action") == "Show Field"]
        hide_rules = [r for r in targeting_rules if r.get("action") == "Hide Field"]
        require_rules = [r for r in targeting_rules if r.get("action") == "Require Answer"]

        # Base visibility from field.hidden
        is_visible = not field.hidden

        # 1. Any Hide Field rule satisfied -> hide the field
        for rule in hide_rules:
            if _evaluate_conditions(rule.get("conditions", []), form_data, field_map):
                is_visible = False
                break
        else:
            # 2. If Show Field rules target this field, it is ONLY visible if at least one Show rule passes
            if show_rules:
                is_visible = any(
                    _evaluate_conditions(rule.get("conditions", []), form_data, field_map)
                    for rule in show_rules
                )

        if not is_visible:
            continue

        is_required = bool(field.reqd) and not getattr(field, "read_only", 0)
        for rule in require_rules:
            if _evaluate_conditions(rule.get("conditions", []), form_data, field_map):
                is_required = True
                break

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

        # Guard before any work is done, so a rejected request never creates a
        # submission row or touches the target DocType.
        check_rate_limit(form.route or form_id)
        verify_captcha(captcha_token, action="submit")

        form_data_dict = {item["fieldname"]: item["value"] for item in form_data}

        # Whitelist to declared form fields only
        allowed_fieldnames = {f.fieldname for f in form.fields}
        form_data_dict = {k: v for k, v in form_data_dict.items() if k in allowed_fieldnames}

        if status == SubmissionStatus.SUBMITTED:
            _validate_form_response(form, form_data_dict)

        engine = FormMappingEngine(form_id=form_id)
        submission = engine.process_submission(form_data_dict, status.value)

        # Share the submission with the owner (FP Form Submission)
        add_docshare(
            doctype="FP Form Submission",
            name=submission.name,
            user=frappe.session.user,
            read=1,
            write=1,
            flags={
                "ignore_share_permission": True,
            },
        )
        
        # If the target document was created, share it too
        if submission.target_doctype and getattr(submission, "target_document", None):
            add_docshare(
                doctype=submission.target_doctype,
                name=submission.target_document,
                user=frappe.session.user,
                read=1,
                write=1,
                flags={
                    "ignore_share_permission": True,
                },
            )

        return submission.name
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
    form: Form = frappe.get_doc("Form", form_id)
    target_doctype = form.target_doctype

    submissions = frappe.get_all(
        doctype=target_doctype,
        filters={"owner": frappe.session.user},
        fields=["name", "creation", "modified", "fp_submission_status", "owner"],
        order_by="creation",
    )

    return [UserSubmissionResponse.model_validate(submission).model_dump() for submission in submissions]


@frappe.whitelist()
def get_submission_response(submission_id: str, doctype: str) -> dict[str, Any]:
    """
    Get a full submission response by ID.
    This API checks if the user is the team member / the form is shared with the user.

    Args:
        submission_id: The name/ID of the submission document
        doctype: The submission's doctype (target_doctype of the form)

    Returns:
        The submission document as a dict
    """
    linked_form = frappe.db.get_value(doctype, submission_id, "fp_linked_form")
    if not linked_form:
        frappe.throw(_("Submission not found."), frappe.DoesNotExistError)

    form_data = frappe.db.get_value("Form", linked_form, ["linked_team_id", "target_doctype"], as_dict=True)

    if form_data.target_doctype != doctype:
        frappe.throw(_("Invalid doctype for this submission."), frappe.PermissionError)

    if not frappe.has_permission(
        doctype="FP Team", ptype="write", doc=form_data.linked_team_id, user=frappe.session.user
    ):
        frappe.throw(
            _("You do not have permission to read this form's submissions."),
            frappe.PermissionError,
        )

    submission = frappe.get_doc(form_data.target_doctype, submission_id)
    return submission.as_dict()


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
    Get all submissions for a form

    Args:
        form_id: The ID of the form

    Returns:
        A list of submissions for the form
    """
    form: Form = frappe.get_doc("Form", form_id)
    target_doctype = form.target_doctype

    submissions = frappe.get_all(
        doctype=target_doctype,
        fields=["name", "creation", "modified", "fp_submission_status", "owner"],
        filters={"fp_submission_status": "Submitted"},
        order_by="creation",
    )

    return [UserSubmissionResponse.model_validate(submission).model_dump() for submission in submissions]
