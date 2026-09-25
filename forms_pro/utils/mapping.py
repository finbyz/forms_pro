import json
import frappe
from frappe.model.document import Document
from typing import Any, Dict, List, NamedTuple, Optional

class ChildRoute(NamedTuple):
    table_field: str
    value_field: str
    primary_flags: tuple[str, ...]


# Parent fields that are read_only and derived from a child table. Writing to
# them directly does nothing, so route the value into the child table instead.
CHILD_TABLE_ROUTES: Dict[tuple[str, str], ChildRoute] = {
    ("Contact", "email_id"): ChildRoute("email_ids", "email_id", ("is_primary",)),
    ("Contact", "mobile_no"): ChildRoute(
        "phone_nos", "phone", ("is_primary_mobile_no",)
    ),
    ("Contact", "phone"): ChildRoute("phone_nos", "phone", ("is_primary_phone",)),
}


class FormMappingEngine:
    def __init__(self, form_id: str, form_version_id: Optional[str] = None):
        self.form = frappe.get_doc("Form", form_id)
        # Ideally, we should fetch the specific version's schema.
        # For now, we use the active form's fields.
        self.fields = self.form.fields
        
    def process_submission(self, form_data_dict: Dict[str, Any], status: str) -> Document:
        """
        Creates an FP Form Submission record containing the raw payload.
        Then, if the status is SUBMITTED, attempts to map the data to the target DocType.
        """
        # Save raw submission
        submission = frappe.new_doc("FP Form Submission")
        submission.form = self.form.name
        # Find the latest Form Version
        latest_version = frappe.get_all("FP Form Version", filters={"form": self.form.name}, order_by="creation desc", limit=1)
        if latest_version:
            submission.form_version = latest_version[0].name
        else:
            submission.form_version = None

        submission.route = self.form.route
        submission.target_doctype = self.form.target_doctype
        submission.submitted_at = frappe.utils.now_datetime()
        # 'status' param is "Submitted" or "Draft" from frontend.
        # FP Form Submission doctype only accepts Success, Failed, Processing.
        submission.status = "Processing" if status == "Draft" else "Success"
        submission.processing_status = "Pending" if status == "Draft" else "Mapping"
        submission.payload = json.dumps(form_data_dict, default=str)
        submission.insert(ignore_permissions=True, ignore_mandatory=True)

        if status == "Submitted" and self.form.target_doctype:
            try:
                target_doc, mapped_values = self._map_to_target(form_data_dict)
                submission.target_document = target_doc.name
                submission.target_name = target_doc.name
                submission.response_json = json.dumps(mapped_values, default=str)
                submission.status = "Success"
                submission.processing_status = "Completed"
                submission.save(ignore_permissions=True)
            except Exception as e:
                submission.status = "Failed"
                submission.processing_status = "Failed"
                submission.error_summary = str(e)[:140]
                submission.validation_errors = json.dumps({"error": str(e)})
                submission.save(ignore_permissions=True)
                # We might want to bubble up the error or just return the submission
        elif status == "Submitted":
            # Collect-only form: nothing to map, the raw payload is the result.
            submission.processing_status = "Completed"
            submission.save(ignore_permissions=True)

        return submission

    def _map_to_target(self, form_data_dict: Dict[str, Any]) -> tuple[Document, Dict[str, Any]]:
        """
        Maps the raw payload to the target DocType based on form_field mapping_type.

        Returns the inserted target document and the values actually written to it,
        so the submission record can show what was mapped.
        """
        target_doc = frappe.new_doc(self.form.target_doctype)
        meta = frappe.get_meta(self.form.target_doctype)
        mapped_values: Dict[str, Any] = {}

        for field in self.fields:
            # Only fields explicitly bound to the target DocType are mapped.
            # "Form Field" / "Presentation" / "System" rows stay in the payload only.
            if field.source_type != "Target Field" or not field.target_field:
                continue
            val = form_data_dict.get(field.fieldname)
            if val is None or val == "" or val == []:
                continue

            written = self._apply_value(target_doc, meta, field.target_field, val)
            if written is not None:
                mapped_values[field.target_field] = written

        target_doc.insert(ignore_permissions=True, ignore_mandatory=True)
        return target_doc, mapped_values

    def _apply_value(
        self, target_doc: Document, meta, target_field: str, val: Any
    ) -> Any:
        """Write one mapped value, honouring child tables and derived fields."""
        # Contact keeps emails and phone numbers in child tables; email_id,
        # phone and mobile_no are read_only and recomputed from them, so a
        # direct set() is silently discarded on save.
        child_route = CHILD_TABLE_ROUTES.get((target_doc.doctype, target_field))
        if child_route:
            return self._append_child_row(target_doc, child_route, val)

        df = meta.get_field(target_field)

        if df and df.fieldtype in ("Table", "Table MultiSelect"):
            return self._set_table_rows(target_doc, df, val)

        # Anything else that arrives as a list (e.g. Multiselect -> JSON column)
        # is stored as a JSON string.
        if isinstance(val, list):
            val = json.dumps(val)

        target_doc.set(target_field, val)
        return val

    def _append_child_row(
        self, target_doc: Document, route: "ChildRoute", val: Any
    ) -> Any:
        """Append to a child table, reusing an existing row for the same value."""
        values = val if isinstance(val, list) else [val]
        written = []

        for item in values:
            item = str(item).strip()
            if not item:
                continue

            existing = next(
                (
                    row
                    for row in (target_doc.get(route.table_field) or [])
                    if (row.get(route.value_field) or "").strip().lower() == item.lower()
                ),
                None,
            )
            row = existing or target_doc.append(route.table_field, {route.value_field: item})
            row.set(route.value_field, item)

            # First row of its kind becomes the primary, which is what
            # populates the read-only scalar on the parent.
            is_first = len(target_doc.get(route.table_field)) == 1
            for flag in route.primary_flags:
                if is_first or not existing:
                    row.set(flag, 1)

            written.append(item)

        return written[0] if len(written) == 1 else (written or None)

    def _set_table_rows(self, target_doc: Document, df, val: Any) -> Any:
        """
        A Table form field collects a list of row dicts, which is exactly what a
        Frappe child table wants — but only the child DocType's own fields may
        be set, or insert() raises on unknown columns.
        """
        if isinstance(val, str):
            try:
                val = json.loads(val)
            except (ValueError, TypeError):
                return None
        if not isinstance(val, list):
            return None

        child_doctype = df.options
        if not child_doctype or not frappe.db.exists("DocType", child_doctype):
            return None

        allowed = {f.fieldname for f in frappe.get_meta(child_doctype).fields}
        rows = []
        for row in val:
            if not isinstance(row, dict):
                continue
            clean = {k: v for k, v in row.items() if k in allowed and v not in (None, "")}
            if clean:
                target_doc.append(df.fieldname, clean)
                rows.append(clean)

        return rows or None
