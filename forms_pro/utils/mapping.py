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
        # Find the latest Form Version
        latest_version = frappe.get_all("FP Form Version", filters={"form": self.form.name}, order_by="creation desc", limit=1)
        if latest_version:
            submission.form_version = latest_version[0].name
        else:
            submission.form_version = None

        submission.route = self.form.route
        submission.target_doctype = self.form.target_doctype
        # 'status' param is "Submitted" or "Draft" from frontend.
        # FP Form Submission doctype only accepts Success, Failed, Processing.
        submission.status = "Processing" if status == "Draft" else "Success"
        submission.payload = json.dumps(form_data_dict)
        submission.insert(ignore_permissions=True, ignore_mandatory=True)
        
        if status == "Submitted" and self.form.target_doctype:
            try:
                target_doc = self._map_to_target(form_data_dict)
                submission.target_document = target_doc.name
                submission.save(ignore_permissions=True)
            except Exception as e:
                submission.status = "Failed"
                submission.validation_errors = json.dumps({"error": str(e)})
                submission.save(ignore_permissions=True)
                # We might want to bubble up the error or just return the submission
        
        return submission

    def _map_to_target(self, form_data_dict: Dict[str, Any]) -> Document:
        """
        Maps the raw payload to the target DocType based on form_field mapping_type.
        """
        target_doc = frappe.new_doc(self.form.target_doctype)
        
        for field in self.fields:
            if field.target_field:
                val = form_data_dict.get(field.fieldname)
                if val is not None:
                    # JSON fields must be stored as a JSON string for Frappe if needed
                    # but typically Frappe handles setting lists to Table/Text
                    if isinstance(val, list):
                        val = json.dumps(val)
                    target_doc.set(field.target_field, val)
                    
        target_doc.insert(ignore_permissions=True, ignore_mandatory=True)
        return target_doc
