import frappe

def execute():
    frappe.reload_doc("forms_pro", "doctype", "form")
    
    # Check if is_published column still exists in DB
    if frappe.db.has_column("Form", "is_published"):
        forms = frappe.get_all("Form", fields=["name", "is_published"])
        for form in forms:
            status = "Published" if form.is_published else "Draft"
            frappe.db.set_value("Form", form.name, "status", status, update_modified=False)
