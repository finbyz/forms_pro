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

from forms_pro.services.authoring.target_fields import build_links
from forms_pro.services.mapping.adapters import get_adapter
from forms_pro.utils.form_generator import (
    LINKED_FORM_FIELDOPTIONS,
    SUBMISSION_STATUS_FIELDOPTIONS,
)
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
                self._notify_submitted(submission.name, None, "Collect Only")
                return {"submission_id": submission.name, "status": "Success"}

            self._update_processing_status(submission.name, "Creating")
            adapter = get_adapter(self.form_doc.target_doctype)
            target_doc = adapter.prepare_document(mapped_data)
            adapter.after_mapping(target_doc, mapped_data)
            self._stamp_tracking_fields(target_doc, submission.name)
            target_doc = adapter.persist(target_doc, self.form_doc.record_strategy or "Create New")

            self._update_target_ref(submission.name, target_doc.name, self.form_doc.record_strategy or "Create")
            self._update_processing_status(submission.name, "Completed")
            self._mark_success(submission.name, mapped_data)

            self._share_documents(submission.name, target_doc)
            self._notify_submitted(submission.name, target_doc, self.form_doc.record_strategy or "Create")

            return {
                "submission_id": submission.name,
                "status": "Success",
                "target_name": target_doc.name,
                "target_doctype": self.form_doc.target_doctype,
            }
        except Exception as e:
            self._mark_failed(submission.name, str(e))
            raise

    def _notify_submitted(self, submission_name: str, target_doc: Any, operation: str) -> None:
        """Announce a completed submission to whoever subscribed to it.

        Consumers register under the ``fp_form_submitted`` hook. Forms Pro does
        not import them, so an app can react to submissions without this one
        knowing it exists.

        This runs last, once the target record is persisted and its reference is
        written back onto the submission. A consumer that reads the submission
        therefore always sees a settled row, never a half-written one.

        A subscriber must never be able to fail a submission: the visitor's
        record is already saved, and a broken listener is our problem, not
        theirs. Every consumer is isolated and its failure is logged.
        """
        payload = {
            "form": self.form_id,
            "submission": submission_name,
            "route": self.form_doc.route,
            "operation": operation,
            "target_doctype": self.form_doc.target_doctype if target_doc else None,
            "target_name": target_doc.name if target_doc else None,
            "metadata": self.metadata,
        }
        for handler in frappe.get_hooks("fp_form_submitted") or []:
            try:
                frappe.call(handler, **payload)
            except Exception:
                frappe.log_error(
                    title=f"fp_form_submitted subscriber failed: {handler}",
                    message=frappe.get_traceback(),
                )

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

    def _stamp_tracking_fields(self, target_doc: Any, submission_id: str | None = None) -> None:
        """
        Record which form produced this document, on the document itself.

        `fp_linked_form` and `fp_submission_status` are created on the target
        DocType when a form is generated, but nothing ever filled them in: every
        record came out with a null form link and a status stuck at the field's
        "Draft" default. That broke two things -- CSV export filters on
        `fp_linked_form`, so it returned no rows, and someone looking at a
        Contact in the desk had no way to tell it came from a form at all.

        Only set on DocTypes that actually carry the fields, so a form pointed
        at a DocType Forms Pro never generated is unaffected.
        """
        meta = frappe.get_meta(self.form_doc.target_doctype)

        if meta.has_field(LINKED_FORM_FIELDOPTIONS["fieldname"]):
            target_doc.set(LINKED_FORM_FIELDOPTIONS["fieldname"], self.form_doc.name)

        if meta.has_field(SUBMISSION_STATUS_FIELDOPTIONS["fieldname"]):
            target_doc.set(SUBMISSION_STATUS_FIELDOPTIONS["fieldname"], self.status)

        # Links into the Forms Pro app, which shows every answer -- including
        # the ones that are not columns on this DocType.
        links = build_links(self.form_doc.name, submission_id)
        if meta.has_field("fp_form_link"):
            target_doc.set("fp_form_link", links["form_link"])
        if meta.has_field("fp_submission_link"):
            target_doc.set("fp_submission_link", links["submission_link"])

    def _resolve_version(self) -> str | None:
        latest = frappe.get_all("FP Form Version", filters={"form": self.form_id}, order_by="creation desc", limit=1)
        return latest[0].name if latest else None

    def _validate_form(self) -> None:
        if not self.form_doc.target_doctype:
            frappe.throw(_("Form has no target DocType configured."))
        if not frappe.db.exists("DocType", self.form_doc.target_doctype):
            frappe.throw(_("Target DocType {0} does not exist.").format(self.form_doc.target_doctype))

        # Mandatory fields are checked by the API endpoints, but the processor
        # is the one place every submission path goes through, so enforce it
        # here too: a caller that reaches the processor directly must not be
        # able to write a record that the form says is incomplete. Drafts are
        # deliberately exempt -- they are in-progress work.
        if self.status == "Submitted":
            # Imported late: the validator lives in the API layer, and importing
            # it at module scope would make services depend on api at import time.
            from forms_pro.api.submission.endpoints import _validate_form_response

            _validate_form_response(self.form_doc, self.form_data)

    def _map_to_target(self) -> dict[str, Any]:
        """
        Build the target document's values from the submission.

        A hidden field is set by whoever built the form, not by the visitor:
        "set language to German and hide it, so every contact who fills this in
        gets German". So its value comes from the field's default and the
        submitted payload is ignored for it. Previously the browser supplied
        that value, which meant an edited request could store anything, and a
        payload that simply omitted the field stored nothing at all.

        A hidden field with no default is skipped rather than written as None,
        so it cannot blank an existing value under the "Update Existing"
        strategy.
        """
        target_meta = frappe.get_meta(self.form_doc.target_doctype)
        mapped: dict[str, Any] = {}

        for field in self.form_doc.fields:
            # A field added from the palette carries no `target_field`; the
            # builder only fills that in when a DocType column is picked. When
            # the form's own fieldname matches a column on the target, that is
            # plainly the column meant, so use it. Without this a hidden field
            # with a preset value was dropped on the floor -- the whole point of
            # "set it, hide it, every submission gets it" silently did nothing.
            target = field.target_field
            if not target and target_meta.has_field(field.fieldname):
                target = field.fieldname
            if not (target and field.mapping_type):
                continue

            if field.mapping_type == "Constant":
                mapped[target] = field.default
            elif field.mapping_type == "Direct":
                # Hidden and read-only fields are both set by whoever built the
                # form, never by the visitor, so the payload is ignored for them.
                if field.hidden or getattr(field, "read_only", 0):
                    if field.default not in (None, ""):
                        mapped[target] = field.default
                else:
                    mapped[target] = self.form_data.get(
                        field.fieldname
                    ) or self.form_data.get(field.field_key)
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