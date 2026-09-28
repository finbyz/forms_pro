import re
import unicodedata

import frappe
from frappe import _

from forms_pro.forms_pro.doctype.form_field.form_field import FORM_TO_FRAPPE_FIELDTYPE
from forms_pro.utils.constants import UNSUPPORTED_FRAPPE_FIELDTYPES

MODULE = "User Forms"

# Column types that make sense inside a form's repeating section.
ALLOWED_COLUMN_TYPES = (
    "Data",
    "Number",
    "Email",
    "Phone",
    "Date",
    "Date Time",
    "Time Picker",
    "Select",
    "Checkbox",
    "Textarea",
    "Link",
    # One file per row is how a form collects several uploads; there is no
    # multi-file field type, so a table of Attach rows is the way to do it.
    "Attach",
    "Currency",
    "URL",
)


# Frappe refuses these as fieldnames. It auto-suffixes when it derives the name
# from a label itself, but throws InvalidFieldNameError when the name is set
# explicitly — which is what we do — so handle them here.
RESERVED_FIELDNAMES = frozenset(
    {
        "name",
        "parent",
        "creation",
        "owner",
        "modified",
        "modified_by",
        "parentfield",
        "parenttype",
        "file_list",
        "flags",
        "docstatus",
        "idx",
    }
)


def _safe_fieldname(label: str, taken: set[str]) -> str:
    """A legal, unique fieldname for a user-supplied column label."""
    candidate = frappe.scrub(label or "")
    candidate = re.sub(r"[^a-z0-9_]", "", candidate).strip("_")

    if not candidate:
        candidate = "column"
    if candidate[0].isdigit():
        candidate = f"col_{candidate}"
    if candidate in RESERVED_FIELDNAMES:
        candidate = f"{candidate}_field"

    base = candidate
    suffix = 2
    while candidate in taken:
        candidate = f"{base}_{suffix}"
        suffix += 1

    return candidate


def _unique_doctype_name(base: str) -> str:
    # Frappe allows only letters, digits, spaces, underscores and hyphens in a
    # DocType name, and insists on a leading letter. Form titles are free text,
    # so "Solar Enquiry (Copy)" or "2026 Leads" would otherwise blow up the
    # moment the user drops a Table field onto them.
    # Fold accents to ASCII first, so "Café" becomes "Cafe" rather than "Caf".
    base = unicodedata.normalize("NFKD", base or "")
    base = "".join(c for c in base if not unicodedata.combining(c))
    base = re.sub(r"[^A-Za-z0-9 _-]+", " ", base)
    base = " ".join(base.split()).strip()
    if not base or not base[0].isalpha():
        base = f"Form {base}".strip()
    candidate = base
    n = 2
    while frappe.db.exists("DocType", candidate):
        candidate = f"{base} {n}"
        n += 1
    return candidate


@frappe.whitelist(methods=["POST"])
def create_child_table(form_id: str, field_label: str | None = None) -> dict:
    """
    Create the child DocType backing a Table field.

    Named after the form and the field so the desk stays readable, rather than
    asking the user to invent a DocType name for something they think of as
    "a table inside my form".
    """
    if not frappe.has_permission("Form", "write", form_id):
        frappe.throw(_("You do not have write access to this form"), frappe.PermissionError)

    form_title = frappe.db.get_value("Form", form_id, "title") or "Form"
    name = _unique_doctype_name(f"{form_title} {field_label or 'Table'}")

    doctype = frappe.new_doc("DocType")
    doctype.name = name
    doctype.module = MODULE
    doctype.custom = 1
    doctype.istable = 1
    doctype.editable_grid = 1
    doctype.append("fields", {"label": "Item", "fieldname": "item", "fieldtype": "Data"})
    doctype.insert(ignore_permissions=True)

    return {"doctype": name, "columns": get_child_table_columns(name)["columns"]}


@frappe.whitelist()
def get_child_table_columns(doctype: str) -> dict:
    if not doctype or not frappe.db.exists("DocType", doctype):
        return {"doctype": doctype, "columns": []}

    meta = frappe.get_meta(doctype)
    columns = [
        {"label": f.label, "fieldname": f.fieldname, "fieldtype": f.fieldtype, "reqd": f.reqd}
        for f in meta.fields
        if f.fieldtype not in UNSUPPORTED_FRAPPE_FIELDTYPES
    ]
    return {"doctype": doctype, "columns": columns}


@frappe.whitelist(methods=["POST"])
def set_child_table_columns(doctype: str, columns: list[dict]) -> dict:
    """Replace the column list of a form-owned child DocType."""
    if not frappe.db.exists("DocType", doctype):
        frappe.throw(_("{0} does not exist").format(doctype), frappe.DoesNotExistError)

    doc = frappe.get_doc("DocType", doctype)
    if doc.module != MODULE or not doc.istable:
        # Never let the builder rewrite a real application DocType.
        frappe.throw(
            _("{0} is not a form-owned child table and cannot be edited here.").format(doctype),
            frappe.PermissionError,
        )

    if isinstance(columns, str):
        columns = frappe.parse_json(columns)

    seen: set[str] = set()
    rows = []
    for col in columns or []:
        label = (col.get("label") or "").strip()
        if not label:
            continue
        form_type = col.get("fieldtype") or "Data"
        if form_type not in ALLOWED_COLUMN_TYPES:
            frappe.throw(_("Column type {0} is not supported").format(form_type))

        mapping = FORM_TO_FRAPPE_FIELDTYPE.get(form_type, {"fieldtype": "Data"})
        fieldname = _safe_fieldname(label, seen)
        seen.add(fieldname)

        rows.append(
            {
                "label": label,
                "fieldname": fieldname,
                "fieldtype": mapping.get("fieldtype", "Data"),
                "options": mapping.get("options") or col.get("options"),
                "reqd": 1 if col.get("reqd") else 0,
                "in_list_view": 1,
            }
        )

    if not rows:
        frappe.throw(_("A table needs at least one column."))

    doc.set("fields", [])
    for row in rows:
        doc.append("fields", row)
    doc.save(ignore_permissions=True)
    frappe.clear_document_cache("DocType", doctype)

    return get_child_table_columns(doctype)
