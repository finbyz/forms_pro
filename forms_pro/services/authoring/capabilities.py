import frappe

@frappe.whitelist()
def inspect_doctype(doctype):
    """
    Returns the capabilities of the selected target DocType.
    """
    if not frappe.db.exists("DocType", doctype):
        frappe.throw(f"DocType {doctype} does not exist.")
        
    meta = frappe.get_meta(doctype)
    
    # System/Security-Sensitive DocTypes
    denylist = ["User", "Role", "System Settings", "DocType", "Custom Field", "Server Script", "OAuth Client"]
    if doctype in denylist:
        return {
            "supported": False,
            "reason": "This is a system/security-sensitive DocType and cannot be used as a public form target."
        }
        
    capabilities = {
        "supported": True,
        "is_submittable": meta.is_submittable,
        "issingle": meta.issingle,
        "istable": meta.istable,
        "is_virtual": meta.is_virtual,
        "can_create": not meta.issingle and not meta.istable,
        "can_update": True,
        "supports_attachments": True,
    }
    
    return capabilities
