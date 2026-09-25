import frappe

# FP Team Member gained a `role`. Existing rows predate it, so everyone would
# read as a plain Member — including owners, who would lose admin access to
# their own team. Owners become Admin; everyone else keeps Member.
def execute():
    frappe.reload_doc("forms_pro", "doctype", "fp_team_member")
    frappe.reload_doc("forms_pro", "doctype", "fp_team")

    frappe.db.sql(
        """update `tabFP Team Member`
           set role = 'Member'
           where role is null or role = ''"""
    )

    owners = frappe.db.sql(
        """update `tabFP Team Member` m
           join `tabFP Team` t on t.name = m.parent
           set m.role = 'Admin'
           where m.user = t.owner"""
    )
    return owners
