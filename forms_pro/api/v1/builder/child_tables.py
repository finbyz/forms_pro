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
    frappe.cache.hset(_CHILD_TABLE_OWNER, name, form_id)

    return {"doctype": name, "columns": get_child_table_columns(name)["columns"]}


#: How a stored column comes back to the builder.
#:
#: `FORM_TO_FRAPPE_FIELDTYPE` is lossy: Textarea is stored as Text, Number as
#: Int, Time Picker as Time, Checkbox as Check. Handing those raw names back to
#: the builder put a value in the type dropdown that is not one of its options,
#: and posting it again was refused -- "Column type Text is not supported" --
#: so a table containing a Textarea could never be saved a second time.
#:
#: Written out rather than inverted, because several form types share one
#: Frappe type (Check is both Checkbox and Switch) and the choice of which one
#: comes back has to be deliberate.
_FRAPPE_TO_FORM_COLUMN_TYPE = {
    "Data": "Data",
    "Int": "Number",
    "Float": "Number",
    "Currency": "Currency",
    "Date": "Date",
    "Datetime": "Date Time",
    "Time": "Time Picker",
    "Select": "Select",
    "Check": "Checkbox",
    "Text": "Textarea",
    "Small Text": "Textarea",
    "Long Text": "Textarea",
    "Link": "Link",
    "Phone": "Phone",
    "Attach": "Attach",
    "Attach Image": "Attach",
}


def form_column_type(fieldtype: str, options: str | None = None) -> str:
    """The name the builder's type dropdown uses for a stored column."""
    # Frappe marks an email or a URL as a Data column with `options` naming the
    # semantic, so the options decide before the fieldtype does.
    semantic = (options or "").strip()
    if fieldtype == "Data" and semantic in ("Email", "URL"):
        return semantic
    return _FRAPPE_TO_FORM_COLUMN_TYPE.get(fieldtype, "Data")


def is_form_owned(doctype: str) -> bool:
    """
    Whether the builder may rewrite this child table's columns.

    A Table field can point at a child DocType the form created, or at one that
    already belongs to an app -- "Allowed To Transact With" and "Party Account"
    on Supplier are ERPNext's, shared by every supplier on the site. Only the
    former is ours to change.
    """
    if not doctype or not frappe.db.exists("DocType", doctype):
        return False
    row = frappe.db.get_value("DocType", doctype, ["module", "custom", "istable"], as_dict=True)
    return bool(row and row.module == MODULE and row.custom and row.istable)


@frappe.whitelist()
def get_child_table_columns(doctype: str) -> dict:
    if not doctype or not frappe.db.exists("DocType", doctype):
        return {"doctype": doctype, "columns": [], "editable": False}

    meta = frappe.get_meta(doctype)
    columns = [
        {
            "label": f.label,
            "fieldname": f.fieldname,
            "fieldtype": form_column_type(f.fieldtype, f.options),
            "options": f.options,
            "reqd": f.reqd,
        }
        for f in meta.fields
        if f.fieldtype not in UNSUPPORTED_FRAPPE_FIELDTYPES
    ]
    # The builder used to offer "Add column" and "Save columns" for every table,
    # including ones it is not allowed to touch: the author typed their columns,
    # pressed save, and the server refused -- losing the work with a toast.
    return {"doctype": doctype, "columns": columns, "editable": is_form_owned(doctype)}


#: Which form created each child table, until the form itself records it.
_CHILD_TABLE_OWNER = "forms_pro_child_table_owner"


def _require_write_on_owning_form(doctype: str) -> None:
    """
    Only someone who may edit the form using this table may reshape it.

    The module check above proves the table is a form-owned one, not whose. So
    anyone signed in could replace the columns of another team's table -- and
    with them the answers every future submission can store.
    """
    owners = frappe.get_all(
        "Form Field",
        filters={"parenttype": "Form", "fieldtype": "Table", "options": doctype},
        pluck="parent",
        distinct=True,
    )
    # A table created moments ago is not on its form yet -- the builder writes
    # the Table field on its next autosave -- so the creator is remembered too.
    creator = frappe.cache.hget(_CHILD_TABLE_OWNER, doctype)
    if creator:
        owners.append(creator)
    if any(frappe.has_permission("Form", "write", doc=form) for form in owners):
        return
    if not owners and "System Manager" in frappe.get_roles():
        # A table no form points at any more can still be tidied by an admin.
        return
    frappe.throw(
        _("You do not have permission to change the columns of {0}.").format(doctype),
        frappe.PermissionError,
    )


@frappe.whitelist(methods=["POST"])
def set_child_table_columns(doctype: str, columns: list[dict]) -> dict:
    """Replace the column list of a form-owned child DocType."""
    if not frappe.db.exists("DocType", doctype):
        frappe.throw(_("{0} does not exist").format(doctype), frappe.DoesNotExistError)

    if not is_form_owned(doctype):
        # Never let the builder rewrite a DocType that belongs to an app: its
        # columns are shared by every record on the site, not just this form's.
        frappe.throw(
            _(
                "{0} belongs to another app and is shared across the site, so its "
                "columns cannot be changed from the form builder."
            ).format(doctype),
            frappe.PermissionError,
        )

    _require_write_on_owning_form(doctype)

    doc = frappe.get_doc("DocType", doctype)

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
            # A column saved before the round-trip was fixed comes back naming
            # its Frappe type; translate rather than refuse the whole table.
            form_type = form_column_type(form_type, col.get("options"))
        if form_type not in ALLOWED_COLUMN_TYPES:
            frappe.throw(_("Column type {0} is not supported").format(col.get("fieldtype")))

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
