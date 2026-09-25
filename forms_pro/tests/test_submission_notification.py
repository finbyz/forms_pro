from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from forms_pro.services.submissions.processor import SubmissionProcessor


class TestSubmissionNotification(FrappeTestCase):
    """Forms Pro announces a finished submission; it never depends on a listener."""

    def _processor(self, record_strategy="Create New", target_doctype="Lead"):
        processor = SubmissionProcessor.__new__(SubmissionProcessor)
        processor.form_id = "Contact us"
        processor.form_data = {}
        processor.metadata = {"utm_source": "newsletter"}
        processor.status = "Submitted"
        processor.form_doc = frappe._dict(
            route="contact-us",
            target_doctype=target_doctype,
            record_strategy=record_strategy,
        )
        return processor

    def test_subscribers_receive_the_target_record(self):
        processor = self._processor()
        target = frappe._dict(doctype="Lead", name="LEAD-0007")
        with patch.object(frappe, "get_hooks", return_value=["dummy.handler"]):
            with patch.object(frappe, "call") as call:
                processor._notify_submitted("FPS-0001", target, "Create New")
        call.assert_called_once()
        payload = call.call_args.kwargs
        self.assertEqual(payload["submission"], "FPS-0001")
        self.assertEqual(payload["target_doctype"], "Lead")
        self.assertEqual(payload["target_name"], "LEAD-0007")
        self.assertEqual(payload["operation"], "Create New")
        self.assertEqual(payload["metadata"]["utm_source"], "newsletter")

    def test_collect_only_reports_no_target(self):
        processor = self._processor(record_strategy="Collect Submission Only")
        with patch.object(frappe, "get_hooks", return_value=["dummy.handler"]):
            with patch.object(frappe, "call") as call:
                processor._notify_submitted("FPS-0002", None, "Collect Only")
        payload = call.call_args.kwargs
        self.assertIsNone(payload["target_doctype"])
        self.assertIsNone(payload["target_name"])

    def test_a_broken_subscriber_cannot_fail_the_submission(self):
        """The visitor's record is already saved. A bad listener is our problem."""
        processor = self._processor()
        target = frappe._dict(doctype="Lead", name="LEAD-0008")
        with patch.object(frappe, "get_hooks", return_value=["a.handler", "b.handler"]):
            with patch.object(frappe, "call", side_effect=Exception("boom")) as call:
                with patch.object(frappe, "log_error") as log_error:
                    processor._notify_submitted("FPS-0003", target, "Create New")
        # Both subscribers were attempted, and neither failure escaped.
        self.assertEqual(call.call_count, 2)
        self.assertEqual(log_error.call_count, 2)

    def test_no_subscribers_is_not_an_error(self):
        processor = self._processor()
        with patch.object(frappe, "get_hooks", return_value=None):
            processor._notify_submitted("FPS-0004", None, "Collect Only")
