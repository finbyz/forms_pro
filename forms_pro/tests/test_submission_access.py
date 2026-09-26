import frappe
from frappe.share import add_docshare
from frappe.tests.utils import FrappeTestCase

from forms_pro.api.v1.builder import data as builder


class TestSubmissionAccess(FrappeTestCase):
    """A builder endpoint must authorize the form it is handed, not the DocType.

    ``frappe.has_permission("Form", ptype="read")`` passes for anyone shared
    into any one form, so every builder read used to accept any form id and
    return another team's submissions, payload included.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        team = frappe.db.get_value("FP Team", {}, "name") or frappe.get_doc(
            {"doctype": "FP Team", "team_name": "Access team"}
        ).insert(ignore_permissions=True).name

        def make_form(title):
            form = frappe.new_doc("Form")
            form.title = title
            form.target_doctype = "Lead"
            form.record_strategy = "Create New"
            form.linked_team_id = team
            form.insert(ignore_permissions=True)
            return form.name

        cls.granted = make_form("Access granted form")
        cls.withheld = make_form("Access withheld form")
        submission = frappe.new_doc("FP Form Submission")
        submission.form = cls.withheld
        submission.status = "Success"
        submission.payload = '{"secret": "another team"}'
        submission.insert(ignore_permissions=True, ignore_mandatory=True)

        cls.user = "listing-access-probe@example.com"
        if not frappe.db.exists("User", cls.user):
            user = frappe.new_doc("User")
            user.email = cls.user
            user.first_name = "Probe"
            user.user_type = "System User"
            user.insert(ignore_permissions=True)
            if frappe.db.exists("Role", "Forms Pro User"):
                user.add_roles("Forms Pro User")
        add_docshare(
            doctype="Form",
            name=cls.granted,
            user=cls.user,
            read=1,
            flags={"ignore_share_permission": True},
        )

    def setUp(self):
        super().setUp()
        frappe.set_user(self.user)
        self.addCleanup(lambda: frappe.set_user("Administrator"))

    def test_the_old_doctype_level_check_would_have_passed(self):
        """Documents why the document-level check is the one that matters."""
        self.assertTrue(frappe.has_permission("Form", ptype="read"))

    def test_submissions_of_a_form_the_user_was_not_given_are_refused(self):
        with self.assertRaises(frappe.PermissionError):
            builder.get_submissions(form_name=self.withheld)

    def test_versions_of_a_form_the_user_was_not_given_are_refused(self):
        with self.assertRaises(frappe.PermissionError):
            builder.get_versions(form_name=self.withheld)

    def test_a_shared_form_still_reads_normally(self):
        page = builder.get_submissions(form_name=self.granted)
        self.assertEqual(page["total"], 0)
        self.assertIn("has_more", page)

    def test_a_missing_form_is_not_found_rather_than_forbidden(self):
        with self.assertRaises(frappe.DoesNotExistError):
            builder.get_submissions(form_name="no-such-form-id")
