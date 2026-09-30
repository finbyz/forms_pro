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
    """Archive a form — soft-delete that hides from public routes.

    Sets both ``status`` and ``is_published`` so the form is completely
    offline: the public load endpoint rejects it on ``is_published``, and the
    submit endpoint rejects it on ``status == 'Archived'``.
    """

    frappe.db.set_value("Form", form_name, {"status": "Archived", "is_published": 0})
    frappe.db.commit()

    return {"status": "Archived", "form": form_name}


#: Everything a version snapshot records about one field. Kept in step with
#: `FormCompiler.SCHEMA_FIELD_PROPS`; a property missing here is a property the
#: revert silently drops.
_REVERTED_FIELD_PROPS = (
    "field_key",
    "fieldname",
    "label",
    "fieldtype",
    "reqd",
    "hidden",
    "read_only",
    "options",
    "default",
    "placeholder",
    "max_length",
    "description",
    "conditional_logic",
    "allow_negative",
    "row_index",
    "column_index",
    "cell_index",
)

#: Form-level properties the snapshot carries, under the names the Form uses.
_REVERTED_FORM_PROPS = (
    "title",
    "description",
    "success_title",
    "success_description",
    "allow_incomplete",
    "login_required",
)


@frappe.whitelist(methods=["POST"])
@require_permission("Form", "write", param="form_name")
def revert_to_version(form_name, version_name):
    """
    Put the draft back the way it was when this version was published.

    Restores the fields and their layout, the form's own text, the theme, the
    success page and the runtime settings -- everything the snapshot holds.

    Two things are deliberately left alone:

    * The route. It is the form's address, not its content: links, embeds and
      QR codes already out in the world point at it, and quietly moving them is
      a worse outcome than a route that no longer matches the version.
    * Publication. Visitors keep getting the version that is live until the
      author publishes again, so reverting the draft is never a way to take a
      form down by accident.

    This used to read the snapshot, discard it, and flip the form to Draft --
    which reported success while changing nothing the author could see, and
    made a published form look unpublished in the builder.
    """

    version_doc = frappe.get_doc("FP Form Version", version_name)

    if version_doc.form != form_name:
        frappe.throw(_("Version does not belong to this form."))

    schema = frappe.parse_json(version_doc.schema_json or "{}")
    if not schema.get("fields"):
        frappe.throw(
            _("Version {0} has no readable snapshot to restore.").format(
                version_doc.version_number
            )
        )

    mapping = frappe.parse_json(version_doc.mapping_json or "{}")
    runtime = frappe.parse_json(version_doc.runtime_settings_json or "{}")

    # How each field reached the target record lives in the mapping half of the
    # snapshot, keyed by field_key, not in the schema half.
    mapped = {
        row.get("field_key"): row
        for row in (mapping.get("fields") or [])
        if row.get("field_key")
    }

    form_doc = frappe.get_doc("Form", form_name)

    for prop in _REVERTED_FORM_PROPS:
        if prop in schema:
            form_doc.set(prop, schema[prop])

    form_doc.theme_overrides_json = version_doc.theme_json or "{}"
    form_doc.success_schema_json = version_doc.success_schema_json or "{}"

    for prop in ("access_mode", "record_strategy", "success_mode"):
        if runtime.get(prop):
            form_doc.set(prop, runtime[prop])

    # The snapshot is the whole field list, so the draft's rows are replaced
    # rather than merged: a field added since the version has to disappear.
    form_doc.set("fields", [])
    for position, snapshot in enumerate(
        sorted(schema["fields"], key=lambda f: f.get("idx") or 0), start=1
    ):
        row = {prop: snapshot.get(prop) for prop in _REVERTED_FIELD_PROPS}
        row["idx"] = position

        mapping_row = mapped.get(snapshot.get("field_key"))
        if "target_field" in snapshot:
            # Snapshots carry each field's mapping themselves now; the mapping
            # half is keyed by field_key, which older rows never received.
            for prop in ("target_field", "source_type", "mapping_type"):
                row[prop] = snapshot.get(prop)
            row["source_type"] = row["source_type"] or "Form Field"
            row["mapping_type"] = row["mapping_type"] or "Direct"
        elif mapping_row:
            row["source_type"] = "Target Field"
            row["target_field"] = mapping_row.get("target_fieldname")
            row["mapping_type"] = mapping_row.get("mapping_type") or "Direct"
        else:
            # Only Target Field rows are recorded in the mapping, so anything
            # absent from it was not bound to a column.
            row["source_type"] = "Form Field"

        form_doc.append("fields", row)

    # No explicit commit: Frappe commits the request once it succeeds, so the
    # whole revert lands or none of it does. Committing here would also escape
    # the rollback tests rely on, leaving rows behind between runs.
    form_doc.save(ignore_permissions=True)

    return {
        "message": _("Draft reverted to version {0}").format(version_doc.version_number),
        "version_number": version_doc.version_number,
        "field_count": len(form_doc.fields),
    }
