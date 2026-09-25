"""
Create form fields on an *existing* DocType as Custom Fields.

A form pointed at a DocType Forms Pro generated owns that DocType outright and
mirrors every field onto it. A form pointed at a DocType that already exists --
Contact, Lead, Customer -- is different: only the fields the author explicitly
mapped land on the record, and every other answer lives in the submission
payload alone. That is fine when the form is a questionnaire, and wrong when
the answers belong on the record.

So it is a per-form choice (`Form.create_target_fields`). When it is on, the
unmapped fields are added to the target DocType as Custom Fields, grouped in
their own tab so they never get mixed up with the DocType's own layout, and the
form field is re-pointed at the column that was created.

Fieldnames are generated, not dictated: the label is what the author cares
about, and the DocType may already use the obvious name for something else.
"""

import frappe
from frappe import _

from forms_pro.utils.form_generator import (
    LINKED_FORM_FIELDOPTIONS,
    SUBMISSION_STATUS_FIELDOPTIONS,
    normalize_form_name,
)

#: Custom Fields created here are attributed to this module, so they are easy
#: to find and to remove, and so they never look like core schema.
OWNED_MODULE = "User Forms"

#: Layout-only field types have no column to create.
_NO_COLUMN = ("Heading 1", "Heading 2", "Heading 3", "Page Break")

#: Frappe reserves these; a form field labelled "Name" must not collide.
_RESERVED = {
    "name",
    "owner",
    "creation",
    "modified",
    "modified_by",
    "docstatus",
    "idx",
    "parent",
    "parentfield",
    "parenttype",
    "doctype",
}


def _scrub(label: str) -> str:
    """A label turned into a legal fieldname, or "" if nothing usable is left."""
    out = "".join(c.lower() if c.isalnum() else "_" for c in (label or ""))
    out = "_".join(part for part in out.split("_") if part)
    if out and out[0].isdigit():
        out = f"f_{out}"
    return out


def _unique_fieldname(base: str, taken: set[str]) -> str:
    """
    A fieldname not already used on the DocType.

    The author never sees this, so a suffix is harmless; what matters is that
    an existing column is never silently reused for different data.
    """
    base = base or "field"
    if base in _RESERVED:
        base = f"{base}_field"

    candidate = base
    n = 2
    while candidate in taken:
        candidate = f"{base}_{n}"
        n += 1
    return candidate


#: One tab per DocType, shared by every form that targets it. Everything Forms
#: Pro adds lives here, so a DocType's own layout is never rearranged.
FORMS_PRO_TAB = "fp_tab_forms_pro"
FORMS_PRO_TAB_LABEL = "Forms Pro"

#: The tab only shows on records a form actually produced. Adding it to a
#: DocType puts it on *every* record of that DocType, including the thousands
#: nobody submitted -- an empty tab on each one. Frappe evaluates `depends_on`
#: per record, so the tab simply is not rendered unless the record carries the
#: stamp.
#:
#: Both markers are checked rather than the submission link alone: records
#: created before the link columns existed still carry `fp_linked_form`, and
#: hiding their status would lose information that is genuinely there.
FORMS_PRO_TAB_CONDITION = "eval:doc.fp_submission_link || doc.fp_linked_form"

#: The two links point at the Vue app, not the desk: the desk can only show the
#: columns that exist on the record, while the app shows every answer that was
#: submitted. Built from the form and submission ids at submission time.
FORM_LINK_FIELD = {
    "fieldname": "fp_form_link",
    "fieldtype": "Data",
    "label": "Form",
    "options": "URL",
    "read_only": 1,
}

SUBMISSION_LINK_FIELD = {
    "fieldname": "fp_submission_link",
    "fieldtype": "Data",
    "label": "Form Submission",
    "options": "URL",
    "read_only": 1,
}


def last_fieldname(doctype: str) -> str | None:
    """
    The DocType's own final field, ignoring anything Forms Pro added.

    A Custom Field with no `insert_after` is placed at the *top*, which put the
    Forms Pro tab ahead of the DocType's own first tab. Anchoring to the last
    field puts it where it belongs: at the end.
    """
    own = [
        df.fieldname
        for df in frappe.get_meta(doctype).fields
        if not df.fieldname.startswith("fp_")
    ]
    return own[-1] if own else None


def ensure_forms_pro_tab(doctype: str) -> None:
    """Create the Forms Pro tab on this DocType if it is not there yet."""
    if frappe.get_meta(doctype).has_field(FORMS_PRO_TAB):
        return

    spec = {
        "fieldname": FORMS_PRO_TAB,
        "fieldtype": "Tab Break",
        "label": FORMS_PRO_TAB_LABEL,
        "depends_on": FORMS_PRO_TAB_CONDITION,
    }
    anchor = last_fieldname(doctype)
    if anchor:
        spec["insert_after"] = anchor

    _insert_custom_field(doctype, spec)
    frappe.clear_cache(doctype=doctype)


def sync_target_custom_fields(form) -> list[dict]:
    """
    Add this form's unmapped fields to its target DocType as Custom Fields.

    Returns the list of fields created, so the caller can report them. Does
    nothing when the option is off, when the form owns its target DocType
    (that path mirrors fields already), or when there is nothing to add.
    """
    if not form.create_target_fields or not form.target_doctype:
        return []
    if not frappe.db.exists("DocType", form.target_doctype):
        return []
    # A generated DocType already receives every field; adding Custom Fields on
    # top would duplicate each column.
    if form.owns_target_doctype():
        return []

    meta = frappe.get_meta(form.target_doctype)
    taken = {df.fieldname for df in meta.fields}
    created: list[dict] = []

    pending = [
        field
        for field in form.fields
        if field.fieldtype not in _NO_COLUMN
        and field.stores_value
        and not (field.target_field and meta.has_field(field.target_field))
    ]
    if not pending:
        return []

    # Everything Forms Pro adds shares one tab on the DocType.
    ensure_forms_pro_tab(form.target_doctype)
    taken.add(FORMS_PRO_TAB)

    for field in pending:
        wanted = field.to_frappe_field
        # A Link or Table with no target cannot be created as a column.
        if wanted["fieldtype"] in ("Link", "Table", "Table MultiSelect") and not (
            wanted.get("options") or ""
        ).strip():
            continue

        fieldname = _unique_fieldname(_scrub(field.label) or field.fieldname, taken)
        taken.add(fieldname)

        _insert_custom_field(
            form.target_doctype,
            {
                "fieldname": fieldname,
                "fieldtype": wanted["fieldtype"],
                "label": field.label,
                "options": wanted.get("options"),
                "description": field.description,
                "insert_after": FORMS_PRO_TAB,
                # The form owns validation; a required Custom Field would also
                # block every other way of editing the record.
                "reqd": 0,
            },
        )

        # Point the form field at the column that was just created, so
        # submissions actually land there.
        field.db_set("target_field", fieldname, update_modified=False)
        field.db_set("mapping_type", "Direct", update_modified=False)
        created.append({"label": field.label, "fieldname": fieldname})

    if created:
        frappe.clear_cache(doctype=form.target_doctype)

    return created


def _insert_custom_field(doctype: str, spec: dict) -> None:
    doc = frappe.new_doc("Custom Field")
    doc.dt = doctype
    doc.module = OWNED_MODULE
    for key, value in spec.items():
        if value is not None:
            doc.set(key, value)
    doc.insert(ignore_permissions=True)


def ensure_tracking_fields(form) -> None:
    """
    Give the target DocType its Forms Pro tab.

    Every target gets the same tab, whatever the DocType is and whether or not
    the author opted into custom fields, holding:

      * Submission Status   -- Draft or Submitted
      * Form                -- opens the form in the Forms Pro app
      * Form Submission     -- opens that submission's answers in the app
      * Linked Form         -- hidden; the id export and the desk link query on

    The two links point at the Vue app rather than the desk, because the desk
    can only ever show the columns that exist on the record while the app shows
    every answer that was submitted.

    Always Custom Fields, never DocFields -- including on DocTypes we generated.
    Appending to a DocType rewrites the owning app's JSON when developer mode is
    on, which is how Forms Pro fields ended up inside frappe's own contact.json,
    duplicated on every Contact and due to be lost at the next update.
    """
    target = form.target_doctype
    if not target or not frappe.db.exists("DocType", target):
        return

    ensure_forms_pro_tab(target)

    wanted = (
        dict(SUBMISSION_STATUS_FIELDOPTIONS),
        dict(FORM_LINK_FIELD),
        dict(SUBMISSION_LINK_FIELD),
        # Hidden: it is the key export filters on and the desk link resolves
        # through, not something to read on the record.
        {**LINKED_FORM_FIELDOPTIONS, "hidden": 1},
    )

    meta = frappe.get_meta(target)
    changed = False
    previous = FORMS_PRO_TAB

    for spec in wanted:
        fieldname = spec["fieldname"]
        if not meta.has_field(fieldname):
            _insert_custom_field(target, {**spec, "insert_after": previous})
            changed = True
        else:
            # Self-heal: a field whose anchor was lost (the tab deleted, a
            # cleanup run, a test teardown) drifts out of the tab and floats to
            # the top of the form. Re-anchor it rather than leaving it stranded.
            current = frappe.db.get_value(
                "Custom Field", {"dt": target, "fieldname": fieldname}, "insert_after"
            )
            # `None` is the broken case, not one to skip: an unanchored Custom
            # Field is rendered at the top of the form, outside the tab.
            if current != previous:
                frappe.db.set_value(
                    "Custom Field",
                    {"dt": target, "fieldname": fieldname},
                    "insert_after",
                    previous,
                    update_modified=False,
                )
                changed = True
        previous = fieldname

    if changed:
        frappe.clear_cache(doctype=target)


def build_links(form_id: str, submission_id: str | None = None) -> dict[str, str]:
    """
    The Forms Pro app URLs for a form and one of its submissions.

    Kept here so the submission processor and any backfill agree on the shape;
    the submissions view opens the matching drawer when given `?submission=`.
    """
    form_url = f"/forms/manage/{form_id}/overview"
    submission_url = f"/forms/manage/{form_id}/submissions"
    if submission_id:
        submission_url = f"{submission_url}?submission={submission_id}"
    return {"form_link": form_url, "submission_link": submission_url}
