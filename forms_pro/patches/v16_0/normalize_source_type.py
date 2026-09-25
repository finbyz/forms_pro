import frappe

# The builder UI briefly wrote its own vocabulary ("Custom"/"Mapped") into
# Form Field.source_type, which is not in the doctype's Select options. Any form
# holding such a row fails to save with a ValidationError. Map the old values
# onto the real ones.
LEGACY_SOURCE_TYPES = {
    "Mapped": "Target Field",
    "Custom": "Form Field",
}

VALID_SOURCE_TYPES = {"Target Field", "Form Field", "Presentation", "System"}

PRESENTATION_FIELDTYPES = ("Heading 1", "Heading 2", "Heading 3", "Page Break")


def execute():
    frappe.reload_doc("forms_pro", "doctype", "form_field")

    for legacy, current in LEGACY_SOURCE_TYPES.items():
        frappe.db.sql(
            """update `tabForm Field` set source_type = %s where source_type = %s""",
            (current, legacy),
        )

    # Display-only rows never map to a target field.
    frappe.db.sql(
        """update `tabForm Field`
           set source_type = 'Presentation', target_field = NULL
           where fieldtype in %(fieldtypes)s""",
        {"fieldtypes": PRESENTATION_FIELDTYPES},
    )

    # Anything still outside the Select options would block the parent Form from
    # saving, so fall back to the safe, non-mapping value.
    frappe.db.sql(
        """update `tabForm Field`
           set source_type = 'Form Field'
           where source_type is null or source_type = '' or source_type not in %(valid)s""",
        {"valid": tuple(VALID_SOURCE_TYPES)},
    )

    _backfill_target_fields()
    _backfill_field_keys()


def _backfill_target_fields():
    """
    Rows converted from the legacy "Mapped" value carry no target_field. A form
    field historically mapped 1:1 onto the target DocType field of the same
    name, so restore that — and demote the row to a plain form field when the
    target DocType has no such field.
    """
    rows = frappe.get_all(
        "Form Field",
        filters={"source_type": "Target Field"},
        fields=["name", "parent", "fieldname", "target_field"],
    )

    target_by_form = {}
    for row in rows:
        if row.target_field:
            continue

        if row.parent not in target_by_form:
            target_by_form[row.parent] = frappe.db.get_value("Form", row.parent, "target_doctype")
        target_doctype = target_by_form[row.parent]

        has_field = bool(
            target_doctype
            and frappe.db.exists("DocType", target_doctype)
            and frappe.get_meta(target_doctype).has_field(row.fieldname)
        )

        if has_field:
            frappe.db.set_value(
                "Form Field",
                row.name,
                {"target_field": row.fieldname, "mapping_type": "Direct"},
                update_modified=False,
            )
        else:
            frappe.db.set_value(
                "Form Field", row.name, "source_type", "Form Field", update_modified=False
            )


def _backfill_field_keys():
    """field_key is the stable identity the compiled mapping refers to."""
    for row in frappe.get_all("Form Field", filters={"field_key": ("in", (None, ""))}, fields=["name"]):
        frappe.db.set_value(
            "Form Field", row.name, "field_key", frappe.generate_hash(length=8), update_modified=False
        )
