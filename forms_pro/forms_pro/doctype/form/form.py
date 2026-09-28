# Copyright (c) 2025, harsh@buildwithhussain.com and contributors
# For license information, please see license.txt

from typing import Any

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.share import get_users



def _doctype_signature(doctype_doc) -> tuple:
    """
    Everything this sync is allowed to change, in one comparable value.

    Used to decide whether the DocType actually needs saving. `Document` has no
    `is_dirty()`, and comparing field order alone would miss a relabelled or
    retyped column.
    """
    return (
        doctype_doc.autoname,
        doctype_doc.naming_rule,
        doctype_doc.title_field,
        tuple(
            (df.fieldname, df.idx, df.label, df.fieldtype, df.reqd, df.options)
            for df in doctype_doc.fields
        ),
    )

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
        Mirror the form onto the DocType it owns -- fields, layout and order.

        Three things used to go wrong here. Page Breaks and Headings were
        skipped as "display only", so a multi-step form produced a DocType with
        everything in one tab. Existing columns were updated in place but never
        moved, so reordering fields on the form left the DocType in whatever
        order they were first added. And the form's own order was only ever
        applied to newly added columns.

        The field list is therefore rebuilt in form order on every sync. That
        only rearranges the layout; no column is dropped, so data already
        collected is untouched -- anything on the DocType that is not on the
        form (Forms Pro's tracking columns, fields added by hand in the desk)
        is kept and moved to the end.
        """
        doctype_doc = frappe.get_doc("DocType", self.target_doctype)
        existing = {f.fieldname: f for f in doctype_doc.fields}
        before = _doctype_signature(doctype_doc)

        # Link/Table columns are invalid without a target DocType, and Frappe
        # rejects the whole DocType save with DoctypeLinkError. A freshly added
        # Table field has no child DocType yet, so skip it until it is
        # configured rather than failing every save in between.
        NEEDS_OPTIONS = ("Link", "Table", "Table MultiSelect")
        SYNCED_PROPS = ("label", "fieldtype", "reqd", "options")

        ordered: list = []
        seen: set[str] = set()

        for field in self.fields:
            if not field.fieldname:
                continue

            wanted = field.to_frappe_field
            if wanted["fieldtype"] in NEEDS_OPTIONS and not (wanted.get("options") or "").strip():
                continue

            current = existing.get(field.fieldname)
            if current is None:
                current = doctype_doc.append("fields", wanted)
            else:
                for prop in SYNCED_PROPS:
                    if prop in wanted and current.get(prop) != wanted[prop]:
                        current.set(prop, wanted[prop])

            ordered.append(current)
            seen.add(field.fieldname)

            # A field on a form-owned DocType is always bound to its own column.
            if field.source_type != "Target Field" or field.target_field != field.fieldname:
                field.db_set("source_type", "Target Field", update_modified=False)
                field.db_set("target_field", field.fieldname, update_modified=False)
                field.db_set("mapping_type", "Direct", update_modified=False)

        self._apply_record_naming(doctype_doc)

        # Everything the form does not know about keeps its place at the end.
        trailing = [f for f in doctype_doc.fields if f.fieldname not in seen]

        doctype_doc.fields = ordered + trailing
        for position, df in enumerate(doctype_doc.fields, start=1):
            df.idx = position

        # Save only on a real difference, so an unchanged form does not churn
        # the DocType (every save rewrites its JSON in developer mode).
        if _doctype_signature(doctype_doc) != before:
            doctype_doc.save(ignore_permissions=True)
            frappe.clear_document_cache("DocType", self.target_doctype)

    def _apply_record_naming(self, doctype_doc) -> None:
        """
        Name records after one of the form's own answers.

        A generated DocType had no `autoname`, so Frappe fell back to a random
        hash and every submission came out as an unreadable id -- the author had
        to go into the desk and set naming by hand before the form was usable.
        Naming by a field the form already collects (an email, a reference) is
        what makes the list readable.
        """
        field = (self.naming_field or "").strip()

        if not field:
            # Explicitly blank: leave whatever the DocType already has, so a
            # naming rule set by hand in the desk is not overwritten.
            return

        if not any(df.fieldname == field for df in doctype_doc.fields):
            return

        doctype_doc.autoname = f"field:{field}"
        doctype_doc.naming_rule = "By fieldname"
        # A readable title makes link fields and list views legible too.
        if not doctype_doc.title_field:
            doctype_doc.title_field = field

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
