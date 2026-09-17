import frappe
from frappe.tests.utils import FrappeTestCase
from forms_pro.utils.form_generator import create_form_with_doctype


class TestTargetImmutability(FrappeTestCase):
    def test_target_doctype_remains_unaltered(self):
        """
        Verify that generating a form and modifying it does not alter the target doctype's schema
        """
        # Create a fresh, temporary DocType to ensure it has no existing custom fields
        doctype_name = "formspro_test_immutability"
        if not frappe.db.exists("DocType", doctype_name):
            doc = frappe.new_doc("DocType")
            doc.name = doctype_name
            doc.module = "User Forms"
            doc.custom = True
            doc.append("fields", {"fieldname": "dummy_field", "fieldtype": "Data", "label": "Dummy"})
            doc.insert(ignore_permissions=True)
            
        # Get the original schema
        frappe.clear_document_cache("DocType", doctype_name)
        original_lead = frappe.get_doc("DocType", doctype_name)
        original_fields = [f.fieldname for f in original_lead.fields]
        
        # We need a team to create a form
        team = frappe.get_doc({
            "doctype": "FP Team",
            "team_name": "Test Team"
        }).insert(ignore_permissions=True)
        
        # Simulate creating a form for the new DocType
        result = create_form_with_doctype(team_id=team.name, doctype=doctype_name)
        form_name = result.get("form_document")
        
        # Now modify the form, add a field
        form = frappe.get_doc("Form", form_name)
        form.append("fields", {
            "fieldname": "test_form_field",
            "label": "Test Form Field",
            "fieldtype": "Data",
            "reqd": 1
        })
        form.save(ignore_permissions=True)
        
        # Verify the target doctype's schema has NOT changed
        frappe.clear_document_cache("DocType", doctype_name)
        updated_lead = frappe.get_doc("DocType", doctype_name)
        updated_fields = [f.fieldname for f in updated_lead.fields]
        
        self.assertEqual(len(original_fields), len(updated_fields))
        self.assertListEqual(original_fields, updated_fields)
        self.assertNotIn("fp_linked_form", updated_fields)
        self.assertNotIn("fp_submission_status", updated_fields)
        self.assertNotIn("test_form_field", updated_fields)
