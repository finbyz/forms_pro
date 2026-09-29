"""Target Adapter interface and GenericAdapter for mapping form data to target DocTypes.

Each adapter encapsulates how a specific category of DocType receives mapped
form data. The GenericAdapter handles standard/custom DocTypes with ordinary
fields (Data, Text, Numeric, Select, Check, Link, Attach, child tables).

Specialized adapters should be added only when a DocType has non-standard
persistence semantics.
"""
from __future__ import annotations

from typing import Any

import json

import frappe
from frappe.model.document import Document

from forms_pro.utils.media_links import add_media_links


def _as_json_column(value: Any) -> str | None:
    """
    A value fit for a JSON column.

    MariaDB gives a JSON column a `CHECK (json_valid(...))` constraint, and it
    rejects anything that is not valid JSON -- including the empty string a
    Multiselect sends when the visitor picks nothing. That came back as
    `OperationalError (4025) CONSTRAINT ... failed`, a 500 with nothing in it
    for the person filling the form, and no submission saved.

    Blank means no answer, so the column is left NULL, which the constraint
    allows. Anything else is stored as JSON: already-encoded JSON is passed
    through unchanged rather than being encoded a second time.
    """
    if value is None or value == "" or value == []:
        return None

    if isinstance(value, (list, dict)):
        return json.dumps(value)

    if isinstance(value, str):
        try:
            json.loads(value)
        except (TypeError, ValueError):
            # A bare answer like "ERP" is one choice, not malformed JSON.
            return json.dumps([value])
        return value

    return json.dumps(value)


class TargetAdapter:
    """Abstract interface for form-to-target mapping adapters."""

    supports_create: bool = True
    supports_update: bool = False
    supports_submit: bool = False

    def __init__(self, doctype: str) -> None:
        self.target_doctype = doctype
        self.target_meta = frappe.get_meta(doctype)

    def inspect_capabilities(self) -> dict[str, Any]:
        return {
            "target_doctype": self.target_doctype,
            "supports_create": self.supports_create,
            "supports_update": self.supports_update,
            "supports_submit": self.supports_submit,
            "is_submittable": self.target_meta.is_submittable,
            "issingle": self.target_meta.issingle,
            "mandatory_fields": self._get_mandatory_fieldnames(),
        }

    def validate_mapping(self, mapped_fields: list[dict[str, Any]]) -> list[str]:
        errors: list[str] = []
        mandatory_fields = self._get_mandatory_fieldnames()
        mapped_fieldnames = {f.get("target_fieldname") for f in mapped_fields if f.get("target_fieldname")}
        for mf in mandatory_fields:
            if mf not in mapped_fieldnames:
                df = self.target_meta.get_field(mf)
                label = df.label if df else mf
                errors.append(f"Mandatory target field '{label}' ({mf}) is not mapped.")
        return errors

    def prepare_document(self, mapped_data: dict[str, Any]) -> Document:
        doc = frappe.new_doc(self.target_doctype)
        for fieldname, value in mapped_data.items():
            if self.target_meta.has_field(fieldname):
                df = self.target_meta.get_field(fieldname)
                if df.fieldtype == "Table" and isinstance(value, list):
                    self._set_child_rows(doc, fieldname, value, df.options)
                elif df.fieldtype == "JSON":
                    doc.set(fieldname, _as_json_column(value))
                elif df.fieldtype in ("Text Editor", "HTML Editor"):
                    # A video stored here is dropped by the desk's own editor,
                    # so a plain link to the same file goes in beside it.
                    doc.set(fieldname, add_media_links(value))
                elif isinstance(value, (list, dict)):
                    # Frappe refuses a list on anything but a Table field
                    # ("Value for X cannot be a list"), so serialise it here --
                    # the one place that knows the column's real type.
                    doc.set(fieldname, json.dumps(value))
                else:
                    doc.set(fieldname, value)
        return doc

    def after_mapping(self, doc: Document, mapped_data: dict[str, Any]) -> None:
        pass

    def persist(self, doc: Document, strategy: str) -> Document:
        ignore_perms = True
        if strategy == "Create New":
            doc.insert(ignore_permissions=ignore_perms)
        elif strategy == "Update Existing":
            doc.save(ignore_permissions=ignore_perms)
        return doc

    def find_existing(self, match_rules: dict[str, Any]) -> Document | None:
        return None

    def _get_mandatory_fieldnames(self) -> set[str]:
        return {
            df.fieldname
            for df in self.target_meta.fields
            if df.reqd and not df.default and df.fieldtype not in (
                "Section Break", "Column Break", "Tab Break",
                "Table", "HTML", "Button", "Image",
            )
        }

    def _set_child_rows(self, parent: Document, fieldname: str, rows: list[dict[str, Any]], child_doctype: str) -> None:
        parent.set(fieldname, [])
        for row_data in rows:
            child = parent.append(fieldname, {})
            for key, val in row_data.items():
                child.set(key, val)


class GenericAdapter(TargetAdapter):
    """Default adapter for standard and custom DocTypes."""

    supports_create = True
    supports_update = True

    def __init__(self, doctype: str) -> None:
        super().__init__(doctype)
        if self.target_meta.is_submittable:
            self.supports_submit = True


def get_adapter(doctype: str) -> TargetAdapter:
    """Factory: returns the appropriate adapter for a target DocType."""
    return GenericAdapter(doctype)