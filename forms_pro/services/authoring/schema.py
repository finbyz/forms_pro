import frappe

def generate_field_key(doc, method=None):
    """
    Hook for before_insert or before_save on Form Field.
    Generates a unique, stable field_key if it does not exist.
    """
    if not doc.field_key:
        doc.field_key = "fld_" + frappe.generate_hash(length=8)
