# Copyright (c) 2025, harsh@buildwithhussain.com and contributors
# For license information, please see license.txt

from typing import Any

import re

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
            (df.fieldname, df.idx, df.label, df.fieldtype, df.reqd, df.options, df.read_only)
            for df in doctype_doc.fields
        ),
    )

def to_naming_series(pattern: str) -> str:
    """
    Turn `CR-{YYYY}-{######}` into Frappe's naming series `CR-.YYYY.-.######`.

    The pattern used to be stored as a `format:` rule, and that is where the
    counter went wrong. Frappe resolves each braced part of a `format:` rule on
    its own, so `{######}` is looked up with nothing in front of it -- and every
    such pattern on the site shares the one counter kept under an empty key.
    A form expecting CR-2026-000001 got CR-2026-067163, the 67,163rd number
    handed out to anyone.

    A naming series resolves left to right and keys the counter on everything
    before the number, so `CR-2026-` gets a counter of its own that starts at 1
    and starts again each year -- the way ERPNext's own series behave.
    """
    parts = []
    for piece in re.split(r"(\{[^}]*\})", pattern):
        if not piece:
            continue
        if piece.startswith("{") and piece.endswith("}"):
            token = piece[1:-1]
            # Date tokens and the counter are bare; a fieldname keeps its braces
            # so Frappe reads it from the document rather than as literal text.
            if set(token) == {"#"} or token in Form.NAMING_TOKENS:
                parts.append(token)
            else:
                parts.append(piece)
        else:
            parts.append(piece)
    return ".".join(parts)


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

            # A rich-text answer is read-only in the desk. The desk's editor is
            # Quill, which cannot represent what this form's editor produces --
            # header cells, paragraphs inside table cells, task lists -- and it
            # writes its own lossy version back the moment the record is saved
            # for any reason. A read-only field is never loaded into Quill; the
            # desk just shows the stored HTML, exactly as it was submitted.
            if current.fieldtype == "Text Editor" and not current.read_only:
                current.read_only = 1

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
        Name submissions from a pattern, the way Frappe's own naming works.

        Naming by a single field (`field:email`) makes that answer the primary
        key, so the second person to use the same address cannot submit at all.
        A pattern avoids that, with an incrementing counter keeping every name
        unique.

        Supported inside braces:
          {#####}      an incrementing number, one digit per #
          {YYYY} {YY}  year        {MM} month     {DD} day
          {WW}         week        {JJJ} day of year
          {timestamp}  full timestamp
          {fieldname}  the answer given for that field

        A blank pattern leaves the DocType's naming alone, so a rule set by
        hand in the desk is never overwritten.
        """
        pattern = (self.naming_pattern or "").strip()
        if not pattern:
            return

        # Frappe derives `naming_rule` from `autoname` itself; setting it here
        # only risks disagreeing with what it decides.
        doctype_doc.autoname = to_naming_series(pattern)

    #: Tokens Frappe's naming series understands on its own, so a pattern using
    #: them is valid even though they are not fields on this form.
    NAMING_TOKENS = frozenset(
        {"YYYY", "YY", "MM", "DD", "JJJ", "WW", "timestamp"}
    )

    def validate_naming_pattern(self) -> None:
        """
        Catch a broken pattern while the form is being built.

        Left unchecked, a typo only shows up when a visitor submits and the
        record cannot be named -- by which time the submission has failed.
        """
        pattern = (self.naming_pattern or "").strip()
        if not pattern:
            return

        if "." in pattern:
            frappe.throw(
                _(
                    "Record name pattern {0} contains a dot. Frappe uses dots to "
                    "separate the parts of a name, so use a dash or slash instead."
                ).format(pattern),
                frappe.ValidationError,
            )

        if pattern.count("{") != pattern.count("}"):
            frappe.throw(
                _("Record name pattern has an unclosed brace: {0}").format(pattern),
                frappe.ValidationError,
            )

        tokens = re.findall(r"\{([^}]*)\}", pattern)
        if not tokens:
            frappe.throw(
                _(
                    "Record name pattern {0} has nothing variable in it, so every "
                    "submission would want the same name. Add {1} for a counter."
                ).format(pattern, "{#####}"),
                frappe.ValidationError,
            )

        fieldnames = {f.fieldname for f in self.fields if f.fieldname}
        for token in tokens:
            if not token:
                frappe.throw(_("Record name pattern has an empty {} placeholder."), frappe.ValidationError)
            if set(token) == {"#"} or token in self.NAMING_TOKENS or token in fieldnames:
                continue
            frappe.throw(
                _(
                    "Record name pattern refers to {0}, which is neither a field on "
                    "this form nor one of {1}."
                ).format(f"{{{token}}}", ", ".join(sorted(self.NAMING_TOKENS))),
                frappe.ValidationError,
            )

    def validate(self) -> None:
        self.validate_naming_pattern()

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
