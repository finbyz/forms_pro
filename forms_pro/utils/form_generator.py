from enum import Enum

import frappe
from frappe import _
from frappe.custom.doctype.custom_field.custom_field import CustomField
from frappe.share import add_docshare

FORMS_PRO_ROLE = "Forms Pro User"


@frappe.whitelist(methods=["POST"])
def create_form_with_doctype(team_id: str, doctype: str, form_name: str | None = None):
    roles = frappe.get_roles(frappe.session.user)
    if FORMS_PRO_ROLE not in roles:
        frappe.throw(
            _("You are not authorized to create a form"),
            frappe.PermissionError,
        )

    try:
        form_generator = FormGenerator(
            team_id=team_id, target_doctype=doctype, form_name=form_name
        )
        form_generator.generate()
    except (frappe.DuplicateEntryError, frappe.ValidationError):
        raise
    except Exception as e:
        frappe.log_error(f"Error creating form with doctype: {doctype} - {e}")
        frappe.throw(
            _("Error creating form with doctype: {0} - {1}").format(doctype, str(e)),
        )

    return {
        "doctype": form_generator.doctype.name,
        "form_document": form_generator.form_document.name,
    }


@frappe.whitelist(methods=["POST"])
def create_form(team_id: str, form_name: str):
    roles = frappe.get_roles(frappe.session.user)
    if FORMS_PRO_ROLE not in roles:
        frappe.throw(
            _("You are not authorized to create a form"),
            frappe.PermissionError,
        )

    try:
        form_generator = FormGenerator(team_id=team_id, form_name=form_name)
        form_generator.generate()
    except (frappe.DuplicateEntryError, frappe.ValidationError):
        raise
    except Exception as e:
        frappe.log_error(f"Error creating form: {e}")
        frappe.throw(
            _("Error creating form: {0}").format(str(e)),
        )

    return {
        "doctype": form_generator.doctype.name,
        "form_document": form_generator.form_document.name,
    }


USER_FORM_MODULE = "User Forms"


class SubmissionStatus(str, Enum):
    DRAFT = "Draft"
    SUBMITTED = "Submitted"





LINKED_FORM_FIELDOPTIONS = {
    "label": "Linked Form",
    "fieldname": "fp_linked_form",
    "fieldtype": "Link",
    "options": "Form",
    "read_only": 1,
}

SUBMISSION_STATUS_FIELDOPTIONS = {
    "label": "Submission Status (Form)",
    "fieldname": "fp_submission_status",
    "fieldtype": "Select",
    "options": "\n".join([status.value for status in SubmissionStatus]),
    "default": SubmissionStatus.DRAFT.value,
    "read_only": 1,
    "in_list_view": 1,
}

def normalize_form_name(form_name: str) -> str:
    """The form name doubles as the DocType name, so collapse whitespace only."""
    name = " ".join((form_name or "").split()).strip()
    if not name:
        frappe.throw(_("Please enter a form name."), frappe.ValidationError)
    return name


@frappe.whitelist()
def check_form_name_available(form_name: str) -> dict:
    """Used by the create dialog to validate before submitting."""
    name = normalize_form_name(form_name)
    return {"name": name, "available": not bool(frappe.db.exists("DocType", name))}


class FormGenerator:
    def __init__(
        self,
        team_id: str,
        target_doctype: str | None = None,
        form_name: str | None = None,
    ) -> None:
        self.doctype = None
        self.team_id = team_id
        self.form_name = form_name
        if target_doctype:
            self.doctype = frappe.get_doc("DocType", target_doctype)

    def generate(self) -> None:
        self._initialize_doctype()
        self._initialize_form_document()
        frappe.clear_document_cache("DocType", self.doctype.name)

    def _initialize_doctype(self) -> None:
        if self.doctype:
            return

        # The DocType is named after the form so the desk shows something
        # meaningful, rather than a wall of generated formspro_* tables.
        doctype_name = normalize_form_name(self.form_name)
        if frappe.db.exists("DocType", doctype_name):
            frappe.throw(
                _("A DocType named {0} already exists. Please choose another form name.").format(
                    doctype_name
                ),
                frappe.DuplicateEntryError,
            )

        placeholder_doctype = frappe.new_doc("DocType")
        placeholder_doctype.name = doctype_name
        placeholder_doctype.module = "User Forms"
        placeholder_doctype.custom = True
        placeholder_doctype.track_changes = True
        placeholder_doctype.track_views = True
        placeholder_doctype.index_web_pages_for_search = False
        placeholder_doctype.is_submittable = 0
        placeholder_doctype.istable = 0
        placeholder_doctype.editable_grid = 0
        placeholder_doctype.issingle = 0
        placeholder_doctype.is_tree = 0
        placeholder_doctype.is_virtual = 0

        # Add permissions
        placeholder_doctype.append(
            "permissions",
            {
                "create": 1,
                "delete": 1,
                "email": 1,
                "export": 1,
                "print": 1,
                "read": 1,
                "report": 1,
                "role": "System Manager",
                "share": 1,
                "write": 1,
                "submit": 0,
            },
        )

        # Add fields
        placeholder_doctype.append("fields", {"fieldtype": "Section Break"})

        placeholder_doctype.insert(ignore_permissions=True)

        add_docshare(
            "DocType",
            placeholder_doctype.name,
            read=1,
            write=1,
            share=1,
            submit=0,
            flags={
                "ignore_share_permission": True,
            },
        )

        self.doctype = placeholder_doctype

    def _initialize_form_document(self) -> None:
        form_document = frappe.new_doc("Form")
        form_document.target_doctype = self.doctype.name
        form_document.title = self.form_name or self.doctype.name
        form_document.status = "Draft"
        form_document.linked_team_id = self.team_id
        form_document.document_type = "System"
        form_document.insert(ignore_permissions=True)

        add_docshare(
            "Form",
            form_document.name,
            read=1,
            write=1,
            share=1,
            submit=0,
            flags={
                "ignore_share_permission": True,
            },
        )
        self.form_document = form_document

    def _generate_doctype_name(self) -> str:
        """
        Generate a unique DocType name with format: formspro_XXXXXX_YYYYYY
        where XXXXXX is a random 6-character string and YYYYYY is a serialized number
        """
        # Count existing formspro_* DocTypes from Forms Pro module
        count = frappe.db.count("DocType", filters={"module": "Forms Pro", "name": ["like", "formspro_%"]})

        # Next number is count + 1
        next_number = count + 1

        # Generate random 6-character string
        random_string = frappe.utils.random_string(6)

        # Format the name with random string and 6-digit padding
        doctype_name = f"formspro_{random_string}{next_number:06d}".lower()

        return doctype_name
