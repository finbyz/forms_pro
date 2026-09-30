"""
The analytics cards have to add up.

A draft -- "Save draft" on a form that allows partial submissions -- is stored
with status "Processing". It was counted in "Records Created" although no
record exists, and shown nowhere else, so one submission always looked lost.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from forms_pro.api.v1.builder.analytics import summary
from forms_pro.services.publishing.compiler import FormCompiler
from forms_pro.tests.factories.form_factory import FormFactory


class TestAnalyticsSummary(FrappeTestCase):
    def setUp(self):
        self.form = FormFactory.create()
        # A submission is always tied to the version it was made against.
        FormCompiler(self.form.name).publish()
        self.version = frappe.db.get_value("Form", self.form.name, "active_version")
        self.addCleanup(self._cleanup)

    def _cleanup(self):
        for name in frappe.get_all("FP Form Submission", {"form": self.form.name}, pluck="name"):
            frappe.delete_doc("FP Form Submission", name, force=True, ignore_permissions=True)
        frappe.delete_doc("Form", self.form.name, force=True, ignore_permissions=True)

    def _submission(self, status, operation="Create"):
        doc = frappe.new_doc("FP Form Submission")
        doc.form = self.form.name
        doc.form_version = self.version
        doc.status = status
        doc.operation = operation
        doc.submitted_at = frappe.utils.now_datetime()
        doc.payload = "{}"
        doc.insert(ignore_permissions=True)

    def test_a_draft_is_counted_as_a_draft_not_a_record(self):
        for _ in range(3):
            self._submission("Success")
        self._submission("Processing", operation="Create")

        result = summary(form_name=self.form.name)

        self.assertEqual(result["total"], 4)
        self.assertEqual(result["success"], 3)
        self.assertEqual(result["drafts"], 1)
        self.assertEqual(result["created"], 3, "a draft created no record")

    def test_a_failure_created_no_record_either(self):
        self._submission("Success")
        self._submission("Failed", operation="Create")

        result = summary(form_name=self.form.name)
        self.assertEqual(result["created"], 1)
        self.assertEqual(result["failed"], 1)

    def test_the_cards_add_up_to_the_total(self):
        self._submission("Success")
        self._submission("Failed")
        self._submission("Processing")

        result = summary(form_name=self.form.name)
        self.assertEqual(result["success"] + result["failed"] + result["drafts"], result["total"])

    def test_drafts_do_not_drag_the_conversion_rate_down(self):
        self._submission("Success")
        self._submission("Processing")
        self.assertEqual(summary(form_name=self.form.name)["conversion_rate"], 100.0)
