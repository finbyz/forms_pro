"""
A submission is held to the version the visitor filled in (FB-LOG-01), and the
legacy public submit endpoint is gone (FB-SEC-02).

Visitors are served the published snapshot while the author keeps editing the
draft. Validating and mapping against the draft meant an unpublished new
required field refused every live response, and an unpublished removal dropped
an answer the visitor had given.
"""

import importlib
import json
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from forms_pro.api.submission.endpoints import submit_form_response
from forms_pro.services.publishing.compiler import FormCompiler
from forms_pro.services.publishing.published_fields import published_fields, resolve_version
from forms_pro.tests.factories.form_factory import FormFactory


class TestSubmissionUsesPublishedVersion(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        # CAPTCHA and the per-IP limit guard the endpoint, not what is tested here.
        for name in ("verify_captcha", "check_rate_limit"):
            patcher = patch(f"forms_pro.api.submission.endpoints.{name}")
            patcher.start()
            self.addCleanup(patcher.stop)
        self.form = FormFactory.create()
        self.addCleanup(
            frappe.delete_doc, "Form", self.form.name, force=True, ignore_permissions=True
        )
        self.form.append("fields", {"label": "Full Name", "fieldname": "full_name", "fieldtype": "Data"})
        self.form.append("fields", {"label": "City", "fieldname": "city", "fieldtype": "Data"})
        self.form.save(ignore_permissions=True)
        self.v1 = FormCompiler(self.form.name).publish().name

    def _draft(self):
        return frappe.get_doc("Form", self.form.name)

    def _submit(self, values, **kwargs):
        return submit_form_response(
            form_id=self.form.name,
            form_data=[{"fieldname": k, "value": v} for k, v in values.items()],
            **kwargs,
        )

    def test_an_unpublished_required_field_does_not_block_visitors(self):
        draft = self._draft()
        draft.append(
            "fields", {"label": "Phone", "fieldname": "phone_no", "fieldtype": "Data", "reqd": 1}
        )
        draft.save(ignore_permissions=True)

        # Must not raise "Phone is required": the live form has no such field.
        name = self._submit({"full_name": "Asha", "city": "Pune"})
        self.assertEqual(frappe.db.get_value("FP Form Submission", name, "form_version"), self.v1)

    def test_an_unpublished_removal_keeps_the_visitors_answer(self):
        draft = self._draft()
        draft.set("fields", [f for f in draft.fields if f.fieldname != "city"])
        draft.save(ignore_permissions=True)

        name = self._submit({"full_name": "Asha", "city": "Pune"})
        payload = json.loads(frappe.db.get_value("FP Form Submission", name, "payload"))
        self.assertEqual(payload.get("city"), "Pune")

    def test_the_version_the_page_was_rendered_from_wins(self):
        draft = self._draft()
        draft.append(
            "fields", {"label": "Phone", "fieldname": "phone_no", "fieldtype": "Data", "reqd": 1}
        )
        draft.save(ignore_permissions=True)
        v2 = FormCompiler(self.form.name).publish().name

        # Someone who opened the page before v2 went live is held to v1.
        name = self._submit({"full_name": "Asha"}, form_version=self.v1)
        self.assertEqual(frappe.db.get_value("FP Form Submission", name, "form_version"), self.v1)

        # Without a version, the live one applies.
        with self.assertRaises(frappe.ValidationError):
            self._submit({"full_name": "Asha"})
        self.assertEqual(resolve_version(self._draft()), v2)

    def test_another_forms_version_is_ignored(self):
        other = FormFactory.create()
        self.addCleanup(frappe.delete_doc, "Form", other.name, force=True, ignore_permissions=True)
        other_version = FormCompiler(other.name).publish().name

        self.assertEqual(resolve_version(self._draft(), other_version), self.v1)

    def test_an_older_snapshot_takes_its_mapping_from_the_draft(self):
        schema = json.loads(frappe.db.get_value("FP Form Version", self.v1, "schema_json"))
        for field in schema["fields"]:
            for prop in ("target_field", "source_type", "mapping_type"):
                field.pop(prop, None)
        frappe.db.set_value("FP Form Version", self.v1, "schema_json", json.dumps(schema))

        draft = self._draft()
        by_name = {f.fieldname: f for f in published_fields(draft, self.v1)}
        self.assertEqual(by_name["city"].target_field, draft.get("fields", {"fieldname": "city"})[0].target_field)
        self.assertEqual(by_name["city"].mapping_type, draft.get("fields", {"fieldname": "city"})[0].mapping_type)

    def test_the_snapshot_records_each_fields_mapping(self):
        schema = json.loads(frappe.db.get_value("FP Form Version", self.v1, "schema_json"))
        for field in schema["fields"]:
            self.assertIn("target_field", field)
            self.assertIn("mapping_type", field)


class TestLegacySubmitEndpointIsGone(FrappeTestCase):
    def test_the_module_no_longer_exists(self):
        with self.assertRaises(ModuleNotFoundError):
            importlib.import_module("forms_pro.api.v1.public.submissions")
