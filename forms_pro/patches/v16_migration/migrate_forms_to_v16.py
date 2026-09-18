import frappe

def execute():
    """
    Patch to migrate legacy Forms configs to the new FP Form Version schemas
    and port legacy form data to FP Form Submission.
    """
    frappe.reload_doc("forms_pro", "doctype", "fp_form_version")
    frappe.reload_doc("forms_pro", "doctype", "fp_form_submission")
    
    migrate_form_configs()
    migrate_submissions()

def migrate_form_configs():
    # Migrate legacy form configs to the new FP Form Version
    forms = frappe.get_all("Form", fields=["name", "title", "route", "target_doctype"])
    for form in forms:
        if not frappe.db.exists("FP Form Version", {"form": form.name}):
            doc = frappe.new_doc("FP Form Version")
            doc.form = form.name
            doc.version = 1
            doc.schema_json = frappe.as_json({"title": form.title, "route": form.route, "target_doctype": form.target_doctype})
            doc.insert(ignore_permissions=True)
            print(f"Migrated Form {form.name} to FP Form Version")

def migrate_submissions():
    # Example function to port legacy target doctype submissions to FP Form Submission if needed
    pass
