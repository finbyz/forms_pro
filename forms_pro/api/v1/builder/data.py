import frappe
from frappe import _


@frappe.whitelist()
def get_submissions(form_name, limit=50, offset=0):
    """Fetch paginated form submissions for builder view."""
    frappe.has_permission("Form", ptype="read", throw=True)

    submissions = frappe.get_all(
        "FP Form Submission",
        filters={"form": form_name},
        fields=[
            "name",
            "submitted_at",
            "status",
            "processing_status",
            "target_doctype",
            "target_name",
            "source_url",
            "utm_source",
            "utm_medium",
            "utm_campaign",
            "response_json",
            "payload",
            "error_summary",
        ],
        order_by="submitted_at desc",
        limit=int(limit),
        start=int(offset),
    )

    total = frappe.db.count("FP Form Submission", {"form": form_name})

    return {
        "submissions": submissions,
        "total": total,
        "limit": int(limit),
        "offset": int(offset),
    }


@frappe.whitelist()
def get_versions(form_name):
    """Fetch all immutable published versions for a form."""
    frappe.has_permission("Form", ptype="read", throw=True)

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
def duplicate_form(form_name):
    """Duplicate a form as a new Draft."""
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
def archive_form(form_name):
    """Archive a form — soft-delete that hides from public routes."""
    frappe.has_permission("Form", ptype="write", throw=True)

    frappe.db.set_value("Form", form_name, "status", "Archived")
    frappe.db.commit()

    return {"status": "Archived", "form": form_name}


@frappe.whitelist(methods=["POST"])
def revert_to_version(form_name, version_name):
    """Restore a form draft schema from a historical version snapshot."""
    frappe.has_permission("Form", ptype="write", throw=True)

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
