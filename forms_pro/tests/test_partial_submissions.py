"""
"Allow Partial Submissions" has to mean something on the server too.

The builder hides "Save draft" when the setting is off, but the endpoint took a
draft from anyone who sent one. And the rule a visitor is held to is the
published version's, not whatever the draft currently says.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from forms_pro.api.form.endpoints import toggle_form_published
from forms_pro.api.submission.endpoints import _allows_partial_submissions
from forms_pro.services.publishing.compiler import FormCompiler
from forms_pro.tests.factories.form_factory import FormFactory


class TestPartialSubmissionSetting(FrappeTestCase):
    def setUp(self):
        self.form = FormFactory.create()
        self.addCleanup(
            frappe.delete_doc, "Form", self.form.name, force=True, ignore_permissions=True
        )

    def _reload(self):
        return frappe.get_doc("Form", self.form.name)

    def test_off_means_no_drafts(self):
        self.form.allow_incomplete = 0
        self.form.save(ignore_permissions=True)
        FormCompiler(self.form.name).publish()
        self.assertFalse(_allows_partial_submissions(self._reload()))

    def test_on_means_drafts(self):
        self.form.allow_incomplete = 1
        self.form.save(ignore_permissions=True)
        FormCompiler(self.form.name).publish()
        self.assertTrue(_allows_partial_submissions(self._reload()))

    def test_visitors_are_held_to_the_published_value(self):
        """Ticking the box in the builder does nothing until it is published."""
        self.form.allow_incomplete = 0
        self.form.save(ignore_permissions=True)
        FormCompiler(self.form.name).publish()

        form = self._reload()
        form.allow_incomplete = 1
        form.save(ignore_permissions=True)

        self.assertFalse(_allows_partial_submissions(self._reload()))


class TestPublishFromOverview(FrappeTestCase):
    def setUp(self):
        self.form = FormFactory.create()
        self.addCleanup(
            frappe.delete_doc, "Form", self.form.name, force=True, ignore_permissions=True
        )

    def test_publishing_a_never_published_form_creates_a_version(self):
        self.assertFalse(frappe.db.get_value("Form", self.form.name, "active_version"))
        toggle_form_published(form_id=self.form.name, is_published=True)
        self.assertTrue(frappe.db.get_value("Form", self.form.name, "active_version"))

    def test_republishing_keeps_the_existing_version(self):
        FormCompiler(self.form.name).publish()
        version = frappe.db.get_value("Form", self.form.name, "active_version")

        toggle_form_published(form_id=self.form.name, is_published=False)
        toggle_form_published(form_id=self.form.name, is_published=True)

        self.assertEqual(frappe.db.get_value("Form", self.form.name, "active_version"), version)
