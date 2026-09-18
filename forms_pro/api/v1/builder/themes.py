import frappe

@frappe.whitelist()
def list_themes():
    frappe.has_permission("FP Form Theme", ptype="read", throw=True)
    return frappe.get_all("FP Form Theme", fields=["name", "theme_name", "font_family", "primary_color", "background_color", "input_radius", "card_radius"], order_by="modified desc")

@frappe.whitelist()
def get_theme(theme_name):
    frappe.has_permission("FP Form Theme", ptype="read", throw=True)
    theme = frappe.get_doc("FP Form Theme", theme_name)
    return theme.as_dict()
