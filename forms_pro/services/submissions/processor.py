"""Submission processing pipeline.

Creates FP Form Submission records and executes the target mapping
through the TargetAdapter interface.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import frappe
from frappe import _

from forms_pro.services.mapping.adapters import get_adapter
from forms_pro.services.publishing.compiler import FormCompiler


class SubmissionProcessor:
    """Orchestrates form submission: validate, map, persist target, log result."""

    def __init__(self, form_id: str, form_data: dict[str, Any], metadata: dict[str, Any] | None = None, status: str = "Submitted") -> None:
        self.form_id = form_id
        self.form_data = form_data
        self.metadata = metadata or {}
        self.status = status
        self.form_doc = frappe.get_doc("Form", form_id)

    def process(self) -> dict[str, Any]:
        submission = self._create_submission_record()
        try:
            if self.status == "Draft":
                self._update_processing_status(submission.name, "Completed")
                return {"submission_id": submission.name, "status": "Draft"}

            self._update_processing_status(submission.name, "Validating")
            self._validate_form()

            self._update_processing_status(submission.name, "Mapping")
            mapped_data = self._map_to_target()

            if self.form_doc.record_strategy == "Collect Submission Only":
                self._update_processing_status(submission.name, "Completed")
                self._mark_success(submission.name, mapped_data)
                self._update_target_ref(submission.name, None, "Collect Only")
                return {"submission_id": submission.name, "status": "Success"}

            self._update_processing_status(submission.name, "Creating")
            adapter = get_adapter(self.form_doc.target_doctype)
            target_doc = adapter.prepare_document(mapped_data)
            adapter.after_mapping(target_doc, mapped_data)
            target_doc = adapter.persist(target_doc, self.form_doc.record_strategy or "Create New")

            self._update_target_ref(submission.name, target_doc.name, self.form_doc.record_strategy or "Create")
            self._update_processing_status(submission.name, "Completed")
            self._mark_success(submission.name, mapped_data)

            self._share_documents(submission.name, target_doc)

            return {
                "submission_id": submission.name,
                "status": "Success",
                "target_name": target_doc.name,
                "target_doctype": self.form_doc.target_doctype,
            }
        except Exception as e:
            self._mark_failed(submission.name, str(e))
            raise

    def _create_submission_record(self) -> Any:
        submission = frappe.new_doc("FP Form Submission")
        submission.form = self.form_id
        submission.form_version = self._resolve_version()
        submission.route = self.form_doc.route
        submission.target_doctype = self.form_doc.target_doctype
        submission.status = "Processing" if self.status == "Draft" else "Success"
        submission.processing_status = "Pending"
        submission.submitted_at = datetime.utcnow()
        submission.payload = json.dumps(self.form_data)
        submission.source_url = self.metadata.get("source_url")
        submission.referrer = self.metadata.get("referrer")
        submission.utm_source = self.metadata.get("utm_source")
        submission.utm_medium = self.metadata.get("utm_medium")
        submission.utm_campaign = self.metadata.get("utm_campaign")
        submission.utm_term = self.metadata.get("utm_term")
        submission.utm_content = self.metadata.get("utm_content")
        submission.gclid = self.metadata.get("gclid")
        submission.insert(ignore_permissions=True, ignore_mandatory=True)
        return submission

    def _resolve_version(self) -> str | None:
        latest = frappe.get_all("FP Form Version", filters={"form": self.form_id}, order_by="creation desc", limit=1)
        return latest[0].name if latest else None

    def _validate_form(self) -> None:
        if not self.form_doc.target_doctype:
            frappe.throw(_("Form has no target DocType configured."))
        if not frappe.db.exists("DocType", self.form_doc.target_doctype):
            frappe.throw(_("Target DocType {0} does not exist.").format(self.form_doc.target_doctype))

    def _map_to_target(self) -> dict[str, Any]:
        mapped: dict[str, Any] = {}
        for field in self.form_doc.fields:
            if field.target_field and field.mapping_type:
                value = self.form_data.get(field.fieldname) or self.form_data.get(field.field_key)
                if field.mapping_type == "Direct":
                    mapped[field.target_field] = value
                elif field.mapping_type == "Constant":
                    mapped[field.target_field] = field.default if hasattr(field, "default") else None
        return mapped

    def _mark_success(self, submission_name: str, mapped_data: dict[str, Any]) -> None:
        frappe.db.set_value("FP Form Submission", submission_name, {
            "status": "Success",
            "response_json": json.dumps(mapped_data),
        })

    def _mark_failed(self, submission_name: str, error: str) -> None:
        error_code = "SUBMISSION_FAILED"
        frappe.db.set_value("FP Form Submission", submission_name, {
            "status": "Failed",
            "processing_status": "Failed",
            "error_code": error_code,
            "error_summary": str(error)[:140],
        })

    def _update_processing_status(self, submission_name: str, status: str) -> None:
        frappe.db.set_value("FP Form Submission", submission_name, "processing_status", status)

    def _update_target_ref(self, submission_name: str, target_name: str | None, operation: str) -> None:
        values: dict[str, Any] = {"operation": operation}
        if target_name:
            values["target_document"] = target_name
            values["target_name"] = target_name
        frappe.db.set_value("FP Form Submission", submission_name, values)

    def _share_documents(self, submission_name: str, target_doc: Any) -> None:
        from frappe.share import add_docshare

        add_docshare(
            doctype="FP Form Submission",
            name=submission_name,
            user=frappe.session.user,
            read=1,
            write=1,
            flags={"ignore_share_permission": True},
        )
        if target_doc and target_doc.name:
            add_docshare(
                doctype=target_doc.doctype,
                name=target_doc.name,
                user=frappe.session.user,
                read=1,
                write=1,
                flags={"ignore_share_permission": True},
            )