"""
Critical findings from reviews/FORMS_PRO_SURVEY_PLATFORM_REVALIDATION_REVIEW_2026-09-25.md.

Each test follows the review's own "required test" for the finding.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from forms_pro.tests.factories.form_factory import FormFactory


class TestSec01NoGuestShares(FrappeTestCase):
    """FP-SEC-01: an anonymous submission must not be shared with `Guest`."""

    def test_sharing_is_skipped_for_guest(self):
        from forms_pro.services.submissions.processor import SubmissionProcessor

        form = FormFactory.create()
        processor = SubmissionProcessor.__new__(SubmissionProcessor)
        before = frappe.db.count("DocShare", {"user": "Guest"})

        frappe.set_user("Guest")
        try:
            processor._share_documents("not-a-real-submission", None)
        finally:
            frappe.set_user("Administrator")

        self.assertEqual(frappe.db.count("DocShare", {"user": "Guest"}), before)
        frappe.delete_doc("Form", form.name, force=True, ignore_permissions=True)


class TestSec04NoGuestDrafts(FrappeTestCase):
    """FP-SEC-04: guests get a minimal published view, never a draft."""

    def setUp(self):
        self.form = FormFactory.create()
        self.addCleanup(frappe.set_user, "Administrator")
        self.addCleanup(frappe.delete_doc, "Form", self.form.name, force=True, ignore_permissions=True)

    def test_a_guest_cannot_fetch_a_form_by_id(self):
        from forms_pro.api.form.endpoints import get_form

        frappe.set_user("Guest")
        with self.assertRaises(frappe.PermissionError):
            get_form(form_id=self.form.name)

    def test_the_public_view_leaves_out_internals(self):
        from forms_pro.api.form.endpoints import get_form_by_route

        self.form.append("fields", {"label": "Name", "fieldname": "full_name", "fieldtype": "Data"})
        self.form.is_published = 1
        self.form.access_mode = "Public"
        self.form.save(ignore_permissions=True)

        frappe.set_user("Guest")
        payload = get_form_by_route(route=frappe.db.get_value("Form", self.form.name, "route"))

        for key in ("owner", "linked_team_id", "linked_team_name", "record_strategy", "target_doctype"):
            self.assertNotIn(key, payload)
        for field in payload["fields"]:
            for key in ("target_field", "mapping_type", "source_type"):
                self.assertNotIn(key, field)
        self.assertTrue(payload["fields"], "the form's own fields are still served")


class TestSec05RestrictedTargets(FrappeTestCase):
    """FP-SEC-05: a form may not publish to, or submit into, a restricted DocType."""

    def test_restricted_doctypes_are_refused(self):
        from forms_pro.services.publishing.restrictions import target_problem

        for doctype in ("User", "Role", "System Settings", "DocType"):
            self.assertTrue(target_problem(doctype), doctype)
        self.assertIsNone(target_problem("Lead"))

    def test_publishing_a_user_form_is_refused(self):
        from forms_pro.services.publishing.compiler import FormCompiler

        form = FormFactory.create()
        self.addCleanup(frappe.delete_doc, "Form", form.name, force=True, ignore_permissions=True)
        frappe.db.set_value("Form", form.name, "target_doctype", "User", update_modified=False)

        with self.assertRaises(frappe.PermissionError):
            FormCompiler(form.name).publish()


class TestSec06ChildTableOwnership(FrappeTestCase):
    """FP-SEC-06: only someone who may edit the owning form may reshape its table."""

    def setUp(self):
        from forms_pro.api.v1.builder.child_tables import create_child_table

        self.form = FormFactory.create()
        self.table = create_child_table(form_id=self.form.name, field_label="Rows")["doctype"]
        self.addCleanup(self._cleanup)

    def _cleanup(self):
        frappe.set_user("Administrator")
        frappe.delete_doc("DocType", self.table, force=True, ignore_permissions=True)
        frappe.delete_doc("Form", self.form.name, force=True, ignore_permissions=True)

    def test_a_user_without_the_form_is_refused(self):
        from forms_pro.api.v1.builder.child_tables import set_child_table_columns
        from forms_pro.tests.factories.user_factory import UserFactory

        outsider = UserFactory.create()
        frappe.set_user(outsider.name)
        with self.assertRaises(frappe.PermissionError):
            set_child_table_columns(doctype=self.table, columns=[{"label": "X", "fieldtype": "Data"}])

    def test_the_forms_editor_may_change_it(self):
        from forms_pro.api.v1.builder.child_tables import set_child_table_columns

        out = set_child_table_columns(doctype=self.table, columns=[{"label": "X", "fieldtype": "Data"}])
        self.assertEqual([c["label"] for c in out["columns"]], ["X"])
