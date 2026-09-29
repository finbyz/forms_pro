import frappe
from frappe import _
from frappe.share import add_docshare, remove

from forms_pro.services.security import captcha as captcha_service
from forms_pro.api.user import get_user
from forms_pro.forms_pro.doctype.form.form import Form
from forms_pro.utils.constants import FORMS_PRO_SYSTEM_FIELDNAMES, UNSUPPORTED_FRAPPE_FIELDTYPES
from forms_pro.utils.permissions import require_permission

from .schema import FormSharedWithResponse


@frappe.whitelist(allow_guest=True)  # nosemgrep: frappe-semgrep-rules.rules.security.guest-whitelisted-method
def is_login_required(route: str) -> bool:
    """
    Check if login is enabled for a form.

    args:
        route: str - The route of the form to check.

    returns:
        bool - True if login is required, False otherwise.
    """
    login_enabled = frappe.db.get_value(
        doctype="Form",
        filters={"route": route},
        fieldname="login_required",
    )
    return bool(login_enabled)


@frappe.whitelist(allow_guest=True)  # nosemgrep: frappe-semgrep-rules.rules.security.guest-whitelisted-method
def get_form_by_route(route: str) -> dict:
    """
    The public form.

    Serves the published snapshot (Form.active_version) rather than the draft,
    so editing a live form does not change what visitors see until it is
    published again. Falls back to the draft only for forms published before
    versioning existed, otherwise an older form would go blank.
    """
    form_id = frappe.db.get_value("Form", {"route": route}, pluck="name")
    if not form_id:
        frappe.throw(_("Form not found"), frappe.DoesNotExistError)

    payload = get_form(form_id)

    active_version = payload.get("active_version")
    if not active_version:
        return payload

    published = _published_schema(active_version)
    if published:
        payload.update(published)

    return payload


def _published_schema(version_name: str) -> dict | None:
    """Unpack a version snapshot into the shape the renderer expects."""
    version = frappe.db.get_value(
        "FP Form Version", version_name, ["schema_json", "theme_json"], as_dict=True
    )
    schema_json = version.schema_json if version else None
    if not schema_json:
        return None

    try:
        schema = frappe.parse_json(schema_json)
    except Exception:
        frappe.log_error(f"Unreadable schema_json on {version_name}", "Forms Pro publishing")
        return None

    if not schema.get("fields"):
        return None

    return {
        "title": schema.get("title"),
        "description": schema.get("description"),
        "fields": schema.get("fields"),
        "success_title": schema.get("success_title"),
        "success_description": schema.get("success_description"),
        "allow_incomplete": schema.get("allow_incomplete"),
        "login_required": schema.get("login_required"),
        # Visitors get the theme that was live when this version was published,
        # not whatever the builder happens to be editing.
        "theme_overrides_json": version.theme_json or None,
    }


@frappe.whitelist(allow_guest=True)  # nosemgrep: frappe-semgrep-rules.rules.security.guest-whitelisted-method
def get_form(form_id: str) -> dict:
    form: Form = frappe.get_doc(
        "Form",
        form_id,
    )
    return {
        "name": form.name,
        "title": form.title,
        "description": form.description,
        "fields": form.fields,
        "route": form.route,
        "is_published": form.is_published,
        "allow_incomplete": form.allow_incomplete,
        "target_doctype": form.target_doctype,
        "success_title": form.success_title,
        "success_description": form.success_description,
        # The Design and Success tabs write these; without them in the payload
        # the builder reloads to defaults and the work looks unsaved.
        "theme_overrides_json": form.get("theme_overrides_json"),
        "success_schema_json": form.get("success_schema_json"),
        "success_redirect_url": form.get("success_redirect_url"),
        # Public key only — the browser needs it to execute reCAPTCHA. The
        # secret never leaves the server.
        "captcha_enabled": captcha_service.is_enabled(),
        "captcha_site_key": captcha_service.get_site_key(),
        "creation": str(form.creation) if getattr(form, "creation", None) else None,
        "modified": str(form.modified) if getattr(form, "modified", None) else None,
        "owner": getattr(form, "owner", None),
        "modified_by": getattr(form, "modified_by", None),
        "status": getattr(form, "status", "Published" if form.is_published else "Draft"),
        "access_mode": getattr(form, "access_mode", "Public"),
        "record_strategy": getattr(form, "record_strategy", "Create New"),
        "create_target_fields": getattr(form, "create_target_fields", 0),
        "naming_pattern": getattr(form, "naming_pattern", ""),
        "login_required": getattr(form, "login_required", 0),
        "linked_team_id": getattr(form, "linked_team_id", None),
        "linked_team_name": (
            frappe.db.get_value("FP Team", form.linked_team_id, "team_name")
            if getattr(form, "linked_team_id", None)
            else None
        ),
        "theme": getattr(form, "theme", None),
        "active_version": getattr(form, "active_version", None),
        "success_mode": getattr(form, "success_mode", "Designed Page"),
    }


@frappe.whitelist()
@require_permission("Form", "read", param="form_id")
def get_form_for_view(form_id: str) -> dict:
    """Return the form document for the Manage Form page along with overview statistics.

    Requires ``read`` permission on the Form. Returns HTTP 404 when the
    form does not exist and HTTP 403 when the user lacks permission.
    """
    form_data = get_form(form_id)

    total_submissions = 0
    submissions_this_week = 0
    recent_submissions = []

    try:
        total_submissions = frappe.db.count("FP Form Submission", {"form": form_id})
    except Exception:
        total_submissions = 0

    try:
        seven_days_ago = frappe.utils.add_days(frappe.utils.now(), -7)
        submissions_this_week = frappe.db.count(
            "FP Form Submission",
            {"form": form_id, "creation": [">=", seven_days_ago]},
        )
    except Exception:
        submissions_this_week = 0

    try:
        subs = frappe.get_all(
            "FP Form Submission",
            filters={"form": form_id},
            fields=["name", "creation", "modified", "status", "owner", "target_doctype", "target_name"],
            order_by="creation desc",
            limit=5,
        )
        for s in subs:
            recent_submissions.append({
                "name": s.name,
                "creation": str(s.creation) if s.get("creation") else None,
                "modified": str(s.modified) if s.get("modified") else None,
                "status": s.get("status") or "Submitted",
                "owner": s.get("owner"),
                "target_doctype": s.get("target_doctype"),
                "target_name": s.get("target_name"),
            })
    except Exception:
        recent_submissions = []

    latest_submission_date = recent_submissions[0]["creation"] if recent_submissions else None

    form_data["overview_stats"] = {
        "total_submissions": total_submissions,
        "submissions_this_week": submissions_this_week,
        "total_fields": len(form_data.get("fields") or []),
        "latest_submission_date": latest_submission_date,
        "recent_submissions": recent_submissions,
    }

    return form_data


@frappe.whitelist(methods=["POST"])
@require_permission("Form", "write", param="form_id")
def toggle_form_published(form_id: str, is_published: bool | None = None) -> dict:
    """Toggle or set the published status of a form."""
    form = frappe.get_doc("Form", form_id)
    if is_published is None:
        form.is_published = 0 if form.is_published else 1
    else:
        form.is_published = 1 if is_published else 0

    form.status = "Published" if form.is_published else "Draft"
    form.save(ignore_permissions=True)
    return {
        "is_published": form.is_published,
        "status": form.status,
    }


@frappe.whitelist()
@require_permission("Form", "write", param="form_id")
def get_form_for_edit(form_id: str) -> dict:
    """Return the form document for the Edit Form page.

    Requires ``write`` permission on the Form. Returns HTTP 404/403 accordingly.
    """
    return get_form(form_id)


#: Nobody needs more than this to pick a value, and it stops one request
#: walking a whole table.
_MAX_LINK_OPTIONS = 100


def _public_form_field_options(fieldtypes: tuple[str, ...]) -> set[str]:
    """The `options` of the given field types across published, guest-facing forms."""
    rows = frappe.db.sql(
        """
        SELECT DISTINCT ff.options
        FROM `tabForm Field` ff
        INNER JOIN `tabForm` f ON f.name = ff.parent
        WHERE ff.parenttype = 'Form'
          AND ff.fieldtype IN %(fieldtypes)s
          AND ff.hidden = 0
          AND f.is_published = 1
          AND f.login_required = 0
        """,
        {"fieldtypes": fieldtypes},
    )
    return {row[0] for row in rows if row[0]}


def guest_visible_child_tables() -> set[str]:
    """Child DocTypes a published, guest-facing form asks visitors to fill in."""
    return _public_form_field_options(("Table",))


def _guest_readable_link_targets() -> set[str]:
    """
    Every DocType a visitor is genuinely being asked to choose from.

    A public form with a "Company" Link field has to show company names -- that
    is the field doing its job. So does a Company column *inside* a table on
    that form: the row cannot be filled in without it, and restricting this to
    the form's own fields left those dropdowns empty.

    Anything else is not the visitor's business, and the DocType arrives from
    the browser, so it cannot be taken on trust.
    """
    targets = _public_form_field_options(("Link", "Language"))

    for child in guest_visible_child_tables():
        if not frappe.db.exists("DocType", child):
            continue
        for df in frappe.get_meta(child).fields:
            if df.fieldtype in ("Link", "Table MultiSelect") and df.options:
                targets.add(df.options)
                # A Table MultiSelect stores its choices in a child table of
                # its own, whose single Link column names the real DocType.
                if df.fieldtype == "Table MultiSelect" and frappe.db.exists("DocType", df.options):
                    for inner in frappe.get_meta(df.options).fields:
                        if inner.fieldtype == "Link" and inner.options:
                            targets.add(inner.options)

    return targets


def _doctype_is_offered_by_a_public_form(doctype: str) -> bool:
    return doctype in _guest_readable_link_targets()


@frappe.whitelist(allow_guest=True)  # nosemgrep: frappe-semgrep-rules.rules.security.guest-whitelisted-method
def get_link_field_options(
    doctype: str,
    filters: dict | None = None,
    page_length: int = 20,
) -> list[str]:
    """
    The choices behind a Link field.

    The DocType comes from the browser, so this used to be an open door: the
    endpoint allows guests and `frappe.get_all` does not check permissions, so
    anyone could ask for `User` and read every account on the site. Two things
    close it -- a guest may only list a DocType that a published, guest-facing
    form actually links to, and a signed-in user goes through `get_list`, which
    applies that user's own read permissions.
    """
    if not doctype or not frappe.db.exists("DocType", doctype):
        return []

    is_guest = frappe.session.user == "Guest"

    if is_guest and not _doctype_is_offered_by_a_public_form(doctype):
        frappe.throw(
            _("You are not permitted to list {0}.").format(doctype),
            frappe.PermissionError,
        )

    meta = frappe.get_meta(doctype)
    title_field = meta.title_field or "name"
    page_length = min(frappe.utils.cint(page_length) or 20, _MAX_LINK_OPTIONS)

    # Filters are a query the caller writes. A visitor filling in a form has no
    # business writing one, so theirs is dropped rather than trusted.
    if is_guest:
        filters = {}
    elif isinstance(filters, str):
        filters = frappe.parse_json(filters)

    query = frappe.get_all if is_guest else frappe.get_list
    return query(
        doctype=doctype,
        filters=filters or {},
        page_length=page_length,
        fields=["name as value", f"{title_field} as label"],
        order_by="modified desc",
    )


@frappe.whitelist()
@require_permission("Form", "read", param="form_id")
def get_form_shared_with(form_id: str) -> list[frappe.Any]:
    """Get list of users with whom a form is shared.

    Requires ``read`` permission on the Form (HTTP 403 otherwise, HTTP 404
    when the form does not exist).
    """
    form: Form = frappe.get_doc("Form", form_id)
    shared_with = form.shared_with()

    shared_with_responses = []

    # Always include the form owner first
    if form.owner:
        owner_user = get_user(form.owner) or {"full_name": form.owner, "user_image": None}
        shared_with_responses.append({
            "email": form.owner,
            "full_name": owner_user.get("full_name") or form.owner,
            "user_image": owner_user.get("user_image"),
            "read": True,
            "write": True,
            "share": True,
            "submit": True,
        })

    for user in shared_with:
        if user["user"] == form.owner:
            continue
        _user = get_user(user["user"])
        if _user is None:
            continue
        user.update(_user)
        shared_with_responses.append(FormSharedWithResponse.model_validate(user).model_dump())

    return shared_with_responses


@frappe.whitelist(methods=["POST"])
@require_permission("Form", "write", param="form_id")
def remove_form_access(form_id: str, user_email: str) -> None:
    """Remove access to a form for a user.

    Requires ``write`` permission on the Form (HTTP 403 otherwise, HTTP 404
    when the form does not exist).

    Args:
        form_id: The ID of the form to remove access from.
        user_email: The email of the user whose access is being removed.
    """
    return remove(doctype="Form", name=form_id, user=user_email, flags={"ignore_permissions": True})


@frappe.whitelist(methods=["POST"])
@require_permission("Form", "share", param="form_id")
def add_form_access(
    form_id: str,
    user: str,
    read: bool = True,
    write: bool = False,
    share: bool = False,
    submit: bool = False,
) -> None:
    """Grant a user access to a form with the specified permissions.

    Uses ``ignore_share_permission`` so the record can be shared regardless of
    the caller's role-level DocShare permissions — the ``@require_permission``
    decorator enforces that only users with share access on this particular form
    can invoke this endpoint.

    Args:
        form_id: Name of the Form document to share.
        user: Email of the user to grant access to.
        read: Allow the user to read the form (default True).
        write: Allow the user to edit the form (default False).
        share: Allow the user to share the form with others (default False).
        submit: Allow the user to submit the form (default False).

    Raises:
        frappe.PermissionError: HTTP 403, when the caller lacks share access.
        frappe.DoesNotExistError: HTTP 404, when the form does not exist.
    """
    add_docshare(
        doctype="Form",
        name=form_id,
        user=user,
        read=int(read),
        write=int(write),
        share=int(share),
        submit=int(submit),
        flags={"ignore_share_permission": True},
    )


@frappe.whitelist(methods=["POST"])
@require_permission("Form", "share", param="form_id")
def set_form_permission(
    form_id: str,
    user: str,
    permission_to: str,
    value: bool,
) -> None:
    """Toggle a single permission bit for a user on a form.

    Designed for per-toggle updates from the sharing UI — only the specified
    permission field is changed; all other existing permissions are preserved by
    Frappe's ``add_docshare`` merge behaviour.

    Args:
        form_id: Name of the Form document.
        user: Email of the user whose permission is being updated.
        permission_to: Which permission to update. Must be one of:
            ``"read"``, ``"write"``, ``"share"``, ``"submit"``.
        value: ``True`` to grant the permission, ``False`` to revoke it.

    Raises:
        frappe.PermissionError: HTTP 403, when the caller lacks share access.
        frappe.DoesNotExistError: HTTP 404, when the form does not exist.
        frappe.ValidationError: If ``permission_to`` is not a recognised
            permission type.
    """
    # Guard against arbitrary kwargs being forwarded to add_docshare
    allowed_permissions = {"read", "write", "share", "submit"}
    if permission_to not in allowed_permissions:
        frappe.throw(_("Invalid permission type"), frappe.ValidationError)

    add_docshare(
        doctype="Form",
        name=form_id,
        user=user,
        **{permission_to: int(bool(value))},
        flags={"ignore_share_permission": True},
    )


@frappe.whitelist()
def get_doctype_list() -> list[str]:
    if not frappe.has_permission("DocType", "read"):
        frappe.throw(_("You do not have read access to this doctype"))

    return frappe.db.get_list(
        "DocType",
        filters={"istable": 0},
        pluck="name",
        order_by="name",
        limit_page_length=99999,
    )


@frappe.whitelist(allow_guest=True)  # nosemgrep: frappe-semgrep-rules.rules.security.guest-whitelisted-method
def get_doctype_fields(doctype: str = "") -> list:
    """
    The fields of a DocType, for the builder and for rendering table rows.

    Guests reach this because a Table field on a public form draws its columns
    from the child DocType's own schema -- that is what makes linking an
    existing table work without any per-form configuration. They get *only*
    those child tables: the endpoint used to hand anyone the full schema of any
    DocType on the site, `User` and `Salary Slip` included.
    """
    if not doctype or not frappe.db.exists("DocType", doctype):
        return []

    if frappe.session.user == "Guest" and doctype not in guest_visible_child_tables():
        frappe.throw(
            _("You are not permitted to read {0}.").format(doctype),
            frappe.PermissionError,
        )

    doc = frappe.get_doc("DocType", doctype)
    fields = [
        field
        for field in doc.fields
        # A nested table has no renderer, and a hidden column is not the
        # visitor's to fill in.
        if field.fieldtype not in UNSUPPORTED_FRAPPE_FIELDTYPES
        and field.fieldname not in FORMS_PRO_SYSTEM_FIELDNAMES
        and not (doc.istable and (field.fieldtype == "Table" or field.hidden))
    ]
    return fields


@frappe.whitelist(allow_guest=True)  # nosemgrep: frappe-semgrep-rules.rules.security.guest-whitelisted-method
def get_languages() -> list[dict]:
    """
    Enabled languages, for the Language field.

    Frappe autonames Language by `language_code`, so `value` is the code that
    gets stored (matching how `User.language` works) and `label` is the native
    name a visitor recognises. Guest-accessible because public forms need it.
    """
    languages = frappe.get_all(
        "Language",
        filters={"enabled": 1},
        fields=["name", "language_name"],
        order_by="language_name asc",
        limit_page_length=0,
    )
    return [
        {"value": lang.name, "label": lang.language_name or lang.name} for lang in languages
    ]


@frappe.whitelist(allow_guest=True)  # nosemgrep: frappe-semgrep-rules.rules.security.guest-whitelisted-method
def validate_phone(phone_number: str = "", label: str = "") -> dict:
    """
    Validate a phone number using Frappe's exact country-code validator.
    Called by multi-step form navigation and field blur to ensure the validation
    error appears on the specific page where the field is located, not on final submit.
    """
    if not phone_number or not str(phone_number).strip():
        return {"valid": True}

    from frappe.utils import validate_phone_number_with_country_code

    phone = str(phone_number).strip()
    try:
        validate_phone_number_with_country_code(phone, label or "phone")
        return {"valid": True}
    except Exception as e:
        msg = str(e).replace("<strong>", "").replace("</strong>", "").strip()
        if not msg:
            msg = frappe._("Phone Number {0} set in field {1} is not valid.").format(
                phone, label or "phone"
            )
        return {"valid": False, "message": msg}

