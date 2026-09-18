import frappe

def execute():
    frappe.reload_doc("forms_pro", "doctype", "form_field")
    
    fields = frappe.get_all("Form Field", fields=["name", "field_key"])
    for fld in fields:
        if not fld.field_key:
            frappe.db.set_value("Form Field", fld.name, "field_key", frappe.generate_hash(length=8), update_modified=False)
