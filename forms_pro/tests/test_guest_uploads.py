"""
A visitor has to be able to see the file they just uploaded.

Frappe never serves a private file to a guest, so a form upload is made public
-- and a public file is served with no permission check at all, which makes its
name the only thing protecting it. Frappe adds a random suffix only on a name
collision, so without this every first upload sat at a predictable URL.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from forms_pro.services.uploads.guest_files import (
    FORM_UPLOAD_DOCTYPE,
    PREFIX_LENGTH,
    already_prefixed,
    public_upload_name,
)


def _upload(file_name: str, doctype: str | None) -> "frappe.Document":
    """Mirror what frappe.handler.upload_file builds for an uploaded file."""
    frappe.form_dict["doctype"] = doctype
    return frappe.get_doc(
        {
            "doctype": "File",
            "attached_to_doctype": doctype,
            "attached_to_name": None,
            "folder": "Home/Attachments",
            "file_name": file_name,
            "file_url": None,
            "is_private": 1,  # what the uploader historically asked for
            "content": b"probe",
        }
    ).save(ignore_permissions=True)


class TestFormUploadNaming(FrappeTestCase):
    def test_a_token_is_prepended(self):
        name = public_upload_name("report.pdf")
        self.assertTrue(name.endswith("-report.pdf"))
        self.assertEqual(len(name), len("report.pdf") + PREFIX_LENGTH + 1)

    def test_a_name_is_not_prefixed_twice(self):
        once = public_upload_name("report.pdf")
        self.assertEqual(public_upload_name(once), once)
        self.assertTrue(already_prefixed(once))

    def test_an_ordinary_name_is_not_mistaken_for_a_prefixed_one(self):
        self.assertFalse(already_prefixed("report.pdf"))
        self.assertFalse(already_prefixed("quarterly-report.pdf"))


class TestFormUploadVisibility(FrappeTestCase):
    def tearDown(self):
        frappe.form_dict.pop("doctype", None)

    def test_a_form_upload_is_public_and_renamed(self):
        uploaded = _upload("research person and company.mp4", FORM_UPLOAD_DOCTYPE)
        self.addCleanup(
            frappe.delete_doc, "File", uploaded.name, force=True, ignore_permissions=True
        )

        self.assertFalse(
            uploaded.is_private,
            "a private file is never served to a guest, so the visitor could not see it",
        )
        self.assertTrue(uploaded.file_url.startswith("/files/"))
        self.assertNotEqual(uploaded.file_name, "research person and company.mp4")
        self.assertTrue(uploaded.file_name.endswith("-research person and company.mp4"))

    def test_every_other_upload_is_left_alone(self):
        uploaded = _upload("unrelated.txt", None)
        self.addCleanup(
            frappe.delete_doc, "File", uploaded.name, force=True, ignore_permissions=True
        )

        self.assertTrue(uploaded.is_private)
        self.assertEqual(uploaded.file_name, "unrelated.txt")
