import json

import frappe
from frappe.tests.utils import FrappeTestCase

from forms_pro.services.submissions import listing


class TestSubmissionListing(FrappeTestCase):
    """A form's submissions are always read one bounded, filtered page at a time."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        team = frappe.db.get_value("FP Team", {}, "name") or frappe.get_doc(
            {"doctype": "FP Team", "team_name": "Listing team"}
        ).insert(ignore_permissions=True).name
        form = frappe.new_doc("Form")
        form.title = "Listing fixture"
        form.target_doctype = "Lead"
        form.record_strategy = "Create New"
        form.linked_team_id = team
        form.append(
            "fields",
            {
                "fieldname": "city",
                "field_key": "city",
                "label": "City",
                "fieldtype": "Data",
                "target_field": "city",
                "mapping_type": "Direct",
            },
        )
        form.insert(ignore_permissions=True)
        cls.form = form.name
        for index in range(45):
            submission = frappe.new_doc("FP Form Submission")
            submission.form = cls.form
            submission.status = "Failed" if index % 5 == 0 else "Success"
            submission.utm_source = "newsletter" if index % 3 == 0 else "ads"
            submission.payload = json.dumps({"city": "Zurich" if index % 2 == 0 else "Bern"})
            submission.insert(ignore_permissions=True, ignore_mandatory=True)

    def test_a_page_is_bounded_and_reports_the_true_total(self):
        page = listing.list_form_submissions(self.form, limit_page_length=20)
        self.assertEqual(len(page["rows"]), 20)
        self.assertEqual(page["total"], 45)
        self.assertTrue(page["has_more"])

    def test_the_last_page_reports_no_more(self):
        page = listing.list_form_submissions(self.form, limit_page_length=20, limit_start=40)
        self.assertEqual(len(page["rows"]), 5)
        self.assertFalse(page["has_more"])

    def test_pages_never_repeat_or_skip_a_row(self):
        """Ties on the sort column must not shuffle rows across page boundaries."""
        first = {row["name"] for row in listing.list_form_submissions(self.form, limit_page_length=20)["rows"]}
        second = {
            row["name"]
            for row in listing.list_form_submissions(self.form, limit_page_length=20, limit_start=20)["rows"]
        }
        self.assertEqual(len(first & second), 0)
        self.assertEqual(len(first | second), 40)

    def test_page_length_is_clamped(self):
        self.assertEqual(listing.coerce_page_length(10_000), listing.MAX_PAGE_LENGTH)
        self.assertEqual(listing.coerce_page_length(0), listing.DEFAULT_PAGE_LENGTH)
        self.assertEqual(listing.coerce_page_length("nonsense"), listing.DEFAULT_PAGE_LENGTH)
        self.assertEqual(listing.coerce_start(-9), 0)

    def test_total_counts_the_filtered_set_not_the_form(self):
        page = listing.list_form_submissions(self.form, filters=[["status", "=", "Failed"]])
        self.assertEqual(page["total"], 9)

    def test_an_answer_filter_reads_the_stored_payload(self):
        page = listing.list_form_submissions(self.form, answer_filters=[["city", "=", "Zurich"]])
        self.assertEqual(page["total"], 23)

    def test_filters_combine(self):
        page = listing.list_form_submissions(
            self.form,
            filters=[["utm_source", "=", "newsletter"]],
            answer_filters=[["city", "=", "Zurich"]],
        )
        self.assertLess(page["total"], 23)
        self.assertGreater(page["total"], 0)

    def test_the_form_pin_cannot_be_widened_by_a_filter(self):
        page = listing.list_form_submissions(self.form, filters=[["form", "=", "another-form"]])
        self.assertEqual(page["total"], 0)

    def test_an_unknown_field_is_refused(self):
        for bad in ("password", "name; drop table x", ""):
            with self.assertRaises(listing.SubmissionQueryError):
                listing.list_form_submissions(self.form, filters=[[bad, "=", "x"]])

    def test_an_unknown_operator_is_refused(self):
        with self.assertRaises(listing.SubmissionQueryError):
            listing.list_form_submissions(self.form, filters=[["status", "; drop table x", "1"]])

    def test_sorting_is_restricted_to_known_columns_and_directions(self):
        with self.assertRaises(listing.SubmissionQueryError):
            listing.list_form_submissions(self.form, order_by="(select 1) desc")
        with self.assertRaises(listing.SubmissionQueryError):
            listing.list_form_submissions(self.form, order_by="status sideways")
        self.assertTrue(listing.list_form_submissions(self.form, order_by="status asc")["rows"])

    def test_a_crafted_answer_key_matches_nothing_rather_than_everything(self):
        page = listing.list_form_submissions(self.form, answer_filters=[["x' or '1'='1", "=", "y"]])
        self.assertEqual(page["total"], 0)

    def test_an_empty_in_list_matches_nothing(self):
        page = listing.list_form_submissions(self.form, filters=[["status", "in", []]])
        self.assertEqual(page["total"], 0)

    def test_payload_is_only_returned_when_asked_for(self):
        lean = listing.list_form_submissions(self.form, limit_page_length=1)["rows"][0]
        self.assertNotIn("payload", lean)
        fat = listing.list_form_submissions(self.form, limit_page_length=1, include_payload=True)["rows"][0]
        self.assertIn("payload", fat)

    def test_filter_catalogue_offers_columns_and_the_form_questions(self):
        catalogue = listing.submission_filter_fields(self.form)
        columns = {entry["field"] for entry in catalogue["columns"]}
        self.assertIn("status", columns)
        self.assertIn("utm_source", columns)
        # The form pin is not something an operator may filter on.
        self.assertNotIn("form", columns)
        self.assertEqual([entry["field"] for entry in catalogue["answers"]], ["city"])
        self.assertEqual(catalogue["page_lengths"], [20, 100, 500])

    def test_the_legacy_endpoint_is_capped(self):
        from forms_pro.api.submission.endpoints import _list_submissions

        self.assertLessEqual(len(_list_submissions(self.form)), listing.MAX_PAGE_LENGTH)
