import json
import frappe
from frappe.model.document import Document
from typing import Any, Dict, List, Optional

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
        # Use a dummy version if we haven't implemented versioning freeze yet
        submission.form_version = self.form.name  # TODO: link to actual FP Form Version
        submission.route = self.form.route
        submission.target_doctype = self.form.linked_doctype
        submission.status = status
        submission.payload = json.dumps(form_data_dict)
        submission.insert(ignore_permissions=True)
        
        if status == "Submitted" and self.form.linked_doctype:
            try:
                target_doc = self._map_to_target(form_data_dict)
                submission.target_document = target_doc.name
                submission.save(ignore_permissions=True)
            except Exception as e:
                submission.status = "Sync Failed"
                submission.validation_errors = json.dumps({"error": str(e)})
                submission.save(ignore_permissions=True)
                # We might want to bubble up the error or just return the submission
        
        return submission

    def _map_to_target(self, form_data_dict: Dict[str, Any]) -> Document:
        """
        Maps the raw payload to the target DocType based on form_field mapping_type.
        """
        target_doc = frappe.new_doc(self.form.linked_doctype)
        
        for field in self.fields:
            if field.source_type == "Mapped" and field.target_field:
                val = form_data_dict.get(field.fieldname)
                if val is not None:
                    # JSON fields must be stored as a JSON string for Frappe if needed
                    # but typically Frappe handles setting lists to Table/Text
                    if isinstance(val, list):
                        val = json.dumps(val)
                    target_doc.set(field.target_field, val)
                    
        target_doc.insert(ignore_permissions=True, ignore_mandatory=True)
        return target_doc
