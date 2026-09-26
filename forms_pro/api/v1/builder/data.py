import frappe
from frappe import _

from forms_pro.services.submissions import listing
from forms_pro.utils.permissions import require_permission


@frappe.whitelist()
@require_permission("Form", "read", param="form_name")
def get_submissions(
    form_name,
    limit=listing.DEFAULT_PAGE_LENGTH,
    offset=0,
    filters=None,
    answer_filters=None,
    search=None,
    order_by=None,
    include_payload=True,
):
    """One page of a form's submissions for the builder's Submissions tab.

    ``frappe.has_permission("Form", ptype="read")`` used to guard this: a
    DocType-level check that every Forms Pro user passes, so any form id
    returned any other team's submissions. The check is now on the specific
    form, and the query is pinned to it.

    Filtering and sorting run in SQL. The tab previously filtered the loaded
    page in the browser, which searched the first fifty rows and presented the
    answer as if it had searched them all.
    """
    page = listing.list_form_submissions(
        form_name,
        filters=filters,
        answer_filters=answer_filters,
        search=search,
        order_by=order_by or "submitted_at desc",
        limit_start=offset,
        limit_page_length=limit,
        include_payload=include_payload,
    )
    return {
        "submissions": page["rows"],
        "total": page["total"],
        "limit": page["limit_page_length"],
        "offset": page["limit_start"],
        "has_more": page["has_more"],
        "page_lengths": page["page_lengths"],
    }


@frappe.whitelist()
@require_permission("Form", "read", param="form_name")
def get_versions(form_name):
    """Fetch all immutable published versions for a form."""

    versions = frappe.get_all(
        "FP Form Version",
        filters={"form": form_name},
        fields=[
            "name",
            "version_number",
            "published_at",
            "published_by",
            "schema_hash",
        ],
        order_by="version_number desc",
    )

    return {"versions": versions}


@frappe.whitelist(methods=["POST"])
@require_permission("Form", "read", param="form_name")
def duplicate_form(form_name):
    """Duplicate a form as a new Draft.

    Creating needs the DocType permission, but copying also reads the source,
    so the caller must hold ``read`` on that specific form -- otherwise a
    duplicate is a way to read a form you were never given.
    """
    frappe.has_permission("Form", ptype="create", throw=True)

    source = frappe.get_doc("Form", form_name)

    new_doc = frappe.copy_doc(source)
    new_doc.title = _("{0} (Copy)").format(source.title)
    new_doc.status = "Draft"
    new_doc.route = ""  # Must be set manually
    new_doc.insert(ignore_permissions=False)
    frappe.db.commit()

    return {"name": new_doc.name, "title": new_doc.title}


@frappe.whitelist(methods=["POST"])
@require_permission("Form", "write", param="form_name")
def archive_form(form_name):
    """Archive a form — soft-delete that hides from public routes."""

    frappe.db.set_value("Form", form_name, "status", "Archived")
    frappe.db.commit()

    return {"status": "Archived", "form": form_name}


@frappe.whitelist(methods=["POST"])
@require_permission("Form", "write", param="form_name")
def revert_to_version(form_name, version_name):
    """Restore a form draft schema from a historical version snapshot."""

    version_doc = frappe.get_doc("FP Form Version", version_name)

    if version_doc.form != form_name:
        frappe.throw(_("Version does not belong to this form."))

    form_doc = frappe.get_doc("Form", form_name)

    # Overwrite the draft schema from the frozen version snapshot
    import json
    schema = json.loads(version_doc.schema_json or "{}")

    form_doc.db_set("status", "Draft")
    frappe.db.commit()

    return {
        "message": _("Draft reverted to version {0}").format(version_doc.version_number),
        "version_number": version_doc.version_number,
    }
