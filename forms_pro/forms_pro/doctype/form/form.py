# Copyright (c) 2025, harsh@buildwithhussain.com and contributors
# For license information, please see license.txt

from typing import Any

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.share import get_users


class Form(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        from forms_pro.forms_pro.doctype.form_field.form_field import FormField

        allow_incomplete: DF.Check
        description: DF.TextEditor | None
        fields: DF.Table[FormField]
        is_published: DF.Check
        target_doctype: DF.Link
        linked_team_id: DF.Link
        login_required: DF.Check
        metadata: DF.Code | None
        route: DF.Data | None
        success_description: DF.TextEditor | None
        success_title: DF.Data | None
        title: DF.Data
    # end: auto-generated types

    pass

    @property
    def target_doctype_doc(self) -> Document:
        return frappe.get_doc("DocType", self.target_doctype)

    @frappe.whitelist()
    def shared_with(self) -> list[dict[str, Any]]:
        """
        Get list of users with which this form is shared
        """
        if not frappe.has_permission("Form", "read", self.name):
            frappe.throw(_("You do not have read access to this form"))
        users_shared_with = get_users(self.doctype, self.name)
        return users_shared_with

    def generate_initial_route(self) -> str:
        return "forms_pro_" + frappe.utils.random_string(8)

    def before_insert(self) -> None:
        self.is_published = False
        self.route = self.generate_initial_route()
        if not self.title:
            self.title = "Untitled Form"

    # DocTypes generated for a form live in this module; everything else
    # (Contact, Lead, ...) belongs to the app and must never be rewritten here.
    OWNED_MODULE = "User Forms"

    def owns_target_doctype(self) -> bool:
        if not self.target_doctype or not frappe.db.exists("DocType", self.target_doctype):
            return False
        module, custom, istable = frappe.db.get_value(
            "DocType", self.target_doctype, ["module", "custom", "istable"]
        )
        return module == self.OWNED_MODULE and bool(custom) and not istable

    def on_update(self) -> None:
        if self.target_doctype:
            # Traceability plumbing: without these the desk cannot link a record
            # back to its submission and export finds nothing.
            from forms_pro.services.authoring.target_fields import ensure_tracking_fields

            ensure_tracking_fields(self)

        if self.owns_target_doctype():
            self.sync_owned_doctype()
        elif self.create_target_fields:
            # Opt-in: mirror unmapped fields onto a DocType we do not own
            # (Contact, Lead, ...) as Custom Fields in their own tab.
            from forms_pro.services.authoring.target_fields import sync_target_custom_fields

            sync_target_custom_fields(self)

    def sync_owned_doctype(self) -> None:
        """
        Mirror the form's fields onto the DocType the form owns, so submissions
        land in real columns instead of an empty record.

        A column whose field has been removed from the form is hidden, not
        dropped: the submissions already collected into it must survive, but
        leaving it visible meant the DocType still listed fields the form no
        longer has, which is confusing when checking a record in the desk.
        Re-adding the field to the form brings its column back into view.
        """
        from forms_pro.forms_pro.doctype.form_field.form_field import _DISPLAY_ONLY_FIELDTYPES

        doctype_doc = frappe.get_doc("DocType", self.target_doctype)
        existing = {f.fieldname: f for f in doctype_doc.fields}
        changed = False
        wanted_fieldnames: set[str] = set()

        # Link/Table columns are invalid without a target DocType, and Frappe
        # rejects the whole DocType save with DoctypeLinkError. A freshly added
        # Table field has no child DocType yet, so skip it until it is
        # configured rather than failing every save in between.
        NEEDS_OPTIONS = ("Link", "Table", "Table MultiSelect")

        for field in self.fields:
            if field.fieldtype in _DISPLAY_ONLY_FIELDTYPES or not field.fieldname:
                continue

            wanted = field.to_frappe_field

            if wanted["fieldtype"] in NEEDS_OPTIONS and not (wanted.get("options") or "").strip():
                continue
            current = existing.get(field.fieldname)

            if current is None:
                doctype_doc.append("fields", wanted)
                changed = True
            else:
                for prop in ("label", "fieldtype", "reqd", "options"):
                    if prop in wanted and current.get(prop) != wanted[prop]:
                        current.set(prop, wanted[prop])
                        changed = True
                # Back on the form, so visible again on the DocType.
                if current.get("hidden"):
                    current.set("hidden", 0)
                    changed = True

            wanted_fieldnames.add(field.fieldname)

            # A field on a form-owned DocType is always bound to its own column.
            if field.source_type != "Target Field" or field.target_field != field.fieldname:
                field.db_set("source_type", "Target Field", update_modified=False)
                field.db_set("target_field", field.fieldname, update_modified=False)
                field.db_set("mapping_type", "Direct", update_modified=False)

        # Columns whose field is no longer on the form: hide rather than drop,
        # so submitted values survive but the DocType stops advertising fields
        # the form does not have. Layout rows and Forms Pro's own tracking
        # columns are not ours to touch.
        from forms_pro.utils.constants import FORMS_PRO_SYSTEM_FIELDNAMES

        LAYOUT = ("Section Break", "Column Break", "Tab Break", "HTML")
        for df in doctype_doc.fields:
            if df.fieldname in wanted_fieldnames:
                continue
            if df.fieldname in FORMS_PRO_SYSTEM_FIELDNAMES or df.fieldtype in LAYOUT:
                continue
            if not df.hidden:
                df.set("hidden", 1)
                # A hidden column that is still mandatory blocks every save.
                df.set("reqd", 0)
                changed = True

        if changed:
            doctype_doc.save(ignore_permissions=True)
            frappe.clear_document_cache("DocType", self.target_doctype)

    def validate(self) -> None:
        # Access Mode is the control users actually see; login_required is what
        # the router enforces. Keeping them in step here stops a form reading
        # "Public" in the builder while bouncing visitors to /login.
        self.login_required = 0 if (self.access_mode or "Public") == "Public" else 1

        if self.target_doctype:
            if not frappe.db.exists("DocType", self.target_doctype):
                frappe.throw(_("Target DocType {0} does not exist").format(self.target_doctype))
        
        if self.route:
            filters = {"route": self.route, "name": ["!=", self.name]}
            if frappe.db.exists("Form", filters):
                frappe.throw(_("Form with route {0} already exists").format(self.route))
