# Copyright (c) 2025, harsh@buildwithhussain.com and contributors
# For license information, please see license.txt

from typing import Any

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.share import get_users


class Form(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        from forms_pro.forms_pro.doctype.form_field.form_field import FormField

        allow_incomplete: DF.Check
        description: DF.TextEditor | None
        fields: DF.Table[FormField]
        is_published: DF.Check
        target_doctype: DF.Link
        linked_team_id: DF.Link
        login_required: DF.Check
        metadata: DF.Code | None
        route: DF.Data | None
        success_description: DF.TextEditor | None
        success_title: DF.Data | None
        title: DF.Data
    # end: auto-generated types

    pass

    @property
    def target_doctype_doc(self) -> Document:
        return frappe.get_doc("DocType", self.target_doctype)

    @frappe.whitelist()
    def shared_with(self) -> list[dict[str, Any]]:
        """
        Get list of users with which this form is shared
        """
        if not frappe.has_permission("Form", "read", self.name):
            frappe.throw(_("You do not have read access to this form"))
        users_shared_with = get_users(self.doctype, self.name)
        return users_shared_with

    def generate_initial_route(self) -> str:
        return "forms_pro_" + frappe.utils.random_string(8)

    def before_insert(self) -> None:
        self.is_published = False
        self.route = self.generate_initial_route()

    def validate(self) -> None:
        if self.target_doctype:
            if not frappe.db.exists("DocType", self.target_doctype):
                frappe.throw(_("Target DocType {0} does not exist").format(self.target_doctype))
        
        if self.route:
            filters = {"route": self.route, "name": ["!=", self.name]}
            if frappe.db.exists("Form", filters):
                frappe.throw(_("Form with route {0} already exists").format(self.route))
