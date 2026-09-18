import frappe

def execute():
    frappe.reload_doc("forms_pro", "doctype", "form_field")
    
    fields = frappe.get_all("Form Field", fields=["name", "parent", "fieldname"])
    
    for fld in fields:
        form = frappe.get_value("Form", fld.parent, "target_doctype")
        if not form:
            continue
            
        if frappe.db.exists("DocType", form):
            meta = frappe.get_meta(form)
            if meta.has_field(fld.fieldname):
                frappe.db.set_value("Form Field", fld.name, {
                    "source_type": "Target Field",
                    "mapping_type": "Direct",
                    "target_fieldname": fld.fieldname
                }, update_modified=False)
            else:
                frappe.db.set_value("Form Field", fld.name, {
                    "source_type": "Form Field"
                }, update_modified=False)
