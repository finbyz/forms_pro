"""
A rich-text answer must survive being opened in the desk.

The desk's Text Editor is Quill, which cannot represent what the form's editor
produces -- header cells, paragraphs inside table cells, task lists -- and it
writes its own lossy version back as soon as the record is saved for any
reason. On a form-owned DocType the column is therefore read-only: the desk
shows the stored HTML and never loads it into Quill.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from forms_pro.tests.factories.form_factory import FormFactory


class TestRichTextColumnIsReadOnly(FrappeTestCase):
    def test_a_text_editor_column_on_an_owned_doctype_is_read_only(self):
        form = FormFactory.create()
        self.assertTrue(form.owns_target_doctype())

        form.append(
            "fields",
            {"label": "Details", "fieldname": "details", "fieldtype": "Text Editor"},
        )
        form.save(ignore_permissions=True)

        column = frappe.get_meta(form.target_doctype, cached=False).get_field("details")
        self.assertEqual(column.fieldtype, "Text Editor")
        self.assertTrue(column.read_only)

    def test_other_columns_are_left_editable(self):
        form = FormFactory.create()
        form.append("fields", {"label": "Name", "fieldname": "full_name", "fieldtype": "Data"})
        form.save(ignore_permissions=True)

        column = frappe.get_meta(form.target_doctype, cached=False).get_field("full_name")
        self.assertFalse(column.read_only)
