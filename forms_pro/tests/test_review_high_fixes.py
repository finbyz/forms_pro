"""
High findings FP-SEC-07 and FP-SEC-08 from
reviews/FORMS_PRO_SURVEY_PLATFORM_REVALIDATION_REVIEW_2026-09-25.md.
"""

import time

import frappe
from frappe.tests.utils import FrappeTestCase

from forms_pro.services.security import access, upload_claims
from forms_pro.tests.factories.form_factory import FormFactory


def _form(**values):
    return frappe._dict({"access_mode": "Public", "login_required": 0, **values})


class TestSec07AccessMode(FrappeTestCase):
    """Access Mode is decided by the server, not the browser's router."""

    def tearDown(self):
        frappe.set_user("Administrator")

    def test_public_admits_everyone(self):
        self.assertTrue(access.can_access(_form(), user="Guest"))

    def test_requires_login_refuses_guests_only(self):
        form = _form(access_mode="Requires Login")
        self.assertFalse(access.can_access(form, user="Guest"))
        self.assertTrue(access.can_access(form, user="Administrator"))

    def test_internal_only_admits_desk_users(self):
        form = _form(access_mode="Internal Only")
        self.assertFalse(access.can_access(form, user="Guest"))
        self.assertTrue(access.can_access(form, user="Administrator"))

    def test_an_older_form_is_read_from_login_required(self):
        self.assertFalse(access.can_access(frappe._dict({"login_required": 1}), user="Guest"))

    def test_a_guest_cannot_load_a_login_only_form(self):
        from forms_pro.api.form.endpoints import get_form_by_route

        form = FormFactory.create()
        self.addCleanup(frappe.delete_doc, "Form", form.name, force=True, ignore_permissions=True)
        form.is_published = 1
        form.access_mode = "Requires Login"
        form.save(ignore_permissions=True)

        frappe.set_user("Guest")
        with self.assertRaises(frappe.PermissionError):
            get_form_by_route(route=form.route)


class TestSec08UploadClaims(FrappeTestCase):
    """An anonymous upload must carry a signed, expiring claim for one form."""

    def setUp(self):
        self.form = FormFactory.create()
        self.form.append("fields", {"label": "CV", "fieldname": "cv", "fieldtype": "Attach"})
        self.form.append("fields", {"label": "Name", "fieldname": "full_name", "fieldtype": "Data"})
        self.form.is_published = 1
        self.form.access_mode = "Public"
        self.form.save(ignore_permissions=True)
        self.addCleanup(frappe.delete_doc, "Form", self.form.name, force=True, ignore_permissions=True)
        self.addCleanup(frappe.set_user, "Administrator")
        self.addCleanup(frappe.form_dict.clear)

    def _claim(self, **overrides):
        # As a guest, and before the claim: frappe.set_user() clears
        # form_dict, which is also the order a real request arrives in.
        frappe.set_user("Guest")
        frappe.form_dict.clear()
        frappe.form_dict.update(
            {
                "fp_form": self.form.name,
                "fp_upload_token": upload_claims.issue(self.form.name),
                "fp_field": "cv",
                **overrides,
            }
        )

    def test_a_valid_claim_is_accepted(self):
        self._claim()
        upload_claims.assert_guest_upload_allowed()  # must not raise

    def test_no_claim_is_refused(self):
        frappe.set_user("Guest")
        frappe.form_dict.clear()
        with self.assertRaises(frappe.PermissionError):
            upload_claims.assert_guest_upload_allowed()

    def test_a_forged_token_is_refused(self):
        self._claim(fp_upload_token=f"{int(time.time()) + 3600}.not-a-signature")
        with self.assertRaises(frappe.PermissionError):
            upload_claims.assert_guest_upload_allowed()

    def test_an_expired_token_is_refused(self):
        self.assertFalse(upload_claims.is_valid(self.form.name, f"{int(time.time()) - 1}.x"))

    def test_a_field_that_takes_no_files_is_refused(self):
        self._claim(fp_field="full_name")
        with self.assertRaises(frappe.PermissionError):
            upload_claims.assert_guest_upload_allowed()

    def test_a_token_only_works_for_its_own_form(self):
        other = FormFactory.create()
        self.addCleanup(frappe.delete_doc, "Form", other.name, force=True, ignore_permissions=True)
        self.assertFalse(upload_claims.is_valid(other.name, upload_claims.issue(self.form.name)))

    def test_an_unpublished_form_takes_no_uploads(self):
        frappe.db.set_value("Form", self.form.name, "is_published", 0)
        self._claim()
        with self.assertRaises(frappe.PermissionError):
            upload_claims.assert_guest_upload_allowed()

    def test_the_public_form_hands_out_a_claim(self):
        from forms_pro.api.form.endpoints import get_form_by_route

        frappe.set_user("Guest")
        payload = get_form_by_route(route=self.form.route)
        self.assertTrue(upload_claims.is_valid(self.form.name, payload["upload_token"]))
