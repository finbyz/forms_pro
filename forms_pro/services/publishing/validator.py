"""Publish validation rules.

Blocks publishing if critical issues exist; emits warnings for non-blocking
concerns. Implements the validation checklist from plan.md §70.
"""
from __future__ import annotations

import frappe
from frappe import _

from forms_pro.services.mapping.adapters import get_adapter


class PublishValidator:
    def __init__(self, form_doc) -> None:
        self.form_doc = form_doc
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def validate(self) -> list[str]:
        self._check_target_doctype()
        if not self.errors:
            self._check_route()
            self._check_mandatory_fields_mapped()
            self._check_field_mapping_validity()
            self._check_duplicate_scalar_mappings()
            self._check_hidden_required_has_default()
            self._check_success_mode_complete()
            self._check_record_strategy()
            self._check_unsupported_mappings()

        if self.errors:
            frappe.throw("\n".join(self.errors), title=_("Publishing Failed"))

        return self.warnings

    def _check_target_doctype(self) -> None:
        dt = self.form_doc.target_doctype
        if not dt:
            self.errors.append(_("Target DocType is missing."))
            return
        if not frappe.db.exists("DocType", dt):
            self.errors.append(_("Target DocType {0} does not exist.").format(dt))
            return

        from forms_pro.services.publishing.restrictions import RESTRICTED_TARGETS

        if dt in RESTRICTED_TARGETS:
            self.errors.append(_("Target DocType {0} is restricted and cannot be used.").format(dt))

        meta = frappe.get_meta(dt)
        if meta.issingle:
            self.errors.append(_("Single DocTypes cannot be used as form targets."))
        if meta.istable:
            self.errors.append(_("Child table DocTypes cannot be used as standalone targets."))
        if meta.is_virtual:
            self.warnings.append(_("Virtual DocType {0} — test compatibility before publishing.").format(dt))

    def _check_route(self) -> None:
        route = self.form_doc.route
        if not route:
            self.errors.append(_("Form route is missing."))
            return
        existing = frappe.db.get_value(
            "Form",
            {"route": route, "name": ["!=", self.form_doc.name]},
        )
        if existing:
            self.errors.append(_("Route '{0}' is already used by another form.").format(route))

    def _check_mandatory_fields_mapped(self) -> None:
        dt = self.form_doc.target_doctype
        if not dt or not frappe.db.exists("DocType", dt):
            return
        adapter = get_adapter(dt)
        mapped_fields = self._get_mapped_fields()
        adapter_errors = adapter.validate_mapping(mapped_fields)
        self.errors.extend(adapter_errors)

    def _check_field_mapping_validity(self) -> None:
        dt = self.form_doc.target_doctype
        if not dt or not frappe.db.exists("DocType", dt):
            return
        meta = frappe.get_meta(dt)
        for field in self.form_doc.fields:
            if not field.target_field:
                continue
            if not meta.has_field(field.target_field):
                self.errors.append(
                    _("Field '{0}' maps to '{1}' which does not exist on {2}.").format(
                        field.label or field.fieldname, field.target_field, dt
                    )
                )

    def _check_duplicate_scalar_mappings(self) -> None:
        seen: set[str] = set()
        for field in self.form_doc.fields:
            if field.target_field and field.mapping_type in ("Direct", "Constant"):
                if field.target_field in seen:
                    self.errors.append(
                        _("Target field '{0}' is mapped by more than one form field.").format(field.target_field)
                    )
                seen.add(field.target_field)

    def _check_hidden_required_has_default(self) -> None:
        for field in self.form_doc.fields:
            if field.hidden and field.reqd and not field.default:
                self.errors.append(
                    _("Hidden required field '{0}' must have a default value.").format(
                        field.label or field.fieldname
                    )
                )

    def _check_success_mode_complete(self) -> None:
        mode = self.form_doc.success_mode
        if mode == "Designed Page" and not self.form_doc.success_schema_json:
            self.warnings.append(_("Success page schema is empty — a default success message will be shown."))
        elif mode == "Redirect to External URL":
            url = (getattr(self.form_doc, "success_redirect_url", None) or "").strip()
            if not url:
                self.warnings.append(_("Redirect URL is not set."))
            elif not url.lower().startswith(("http://", "https://")):
                self.warnings.append(
                    _("Redirect URL must start with http:// or https:// -- visitors will see the success page instead.")
                )

    def _check_record_strategy(self) -> None:
        strategy = self.form_doc.record_strategy
        if strategy == "Update Existing":
            self.warnings.append(_("Update Existing strategy requires a match rule — ensure it is configured."))

    def _check_unsupported_mappings(self) -> None:
        for field in self.form_doc.fields:
            mt = field.mapping_type
            if mt in ("Child Table", "Table MultiSelect"):
                self.warnings.append(
                    _("Field '{0}' uses {1} mapping — verify child table configuration.").format(
                        field.label or field.fieldname, mt
                    )
                )

    def _get_mapped_fields(self) -> list[dict]:
        return [
            {"target_fieldname": f.target_field, "mapping_type": f.mapping_type}
            for f in self.form_doc.fields
            if f.target_field and f.mapping_type
        ]