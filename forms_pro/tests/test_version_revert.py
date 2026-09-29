"""
Reverting a draft to a published version has to actually restore it.

The endpoint used to read the snapshot, throw it away and flip the form to
Draft, so the builder showed "Reverted to v2" over an unchanged form -- and a
published form started reporting itself as a draft.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from forms_pro.api.v1.builder.data import revert_to_version
from forms_pro.services.publishing.compiler import FormCompiler
from forms_pro.tests.factories.form_factory import FormFactory


class TestRevertToVersion(FrappeTestCase):
    def setUp(self):
        self.form = FormFactory.create()
        self.form.append(
            "fields",
            {"label": "Original Label", "fieldname": "kept_field", "fieldtype": "Data"},
        )
        self.form.title = "Original Title"
        self.form.save(ignore_permissions=True)

        self.version = FormCompiler(self.form.name).publish()
        self.baseline = frappe.db.get_value("Form", self.form.name, "active_version")

    def _reload(self):
        return frappe.get_doc("Form", self.form.name)

    def test_revert_restores_the_fields_and_text_of_the_snapshot(self):
        form = self._reload()
        form.title = "Edited Title"
        form.fields[-1].label = "Edited Label"
        form.append(
            "fields",
            {"label": "Added Later", "fieldname": "added_later", "fieldtype": "Data"},
        )
        form.save(ignore_permissions=True)

        revert_to_version(form_name=self.form.name, version_name=self.baseline)

        reverted = self._reload()
        self.assertEqual(reverted.title, "Original Title")
        self.assertEqual(
            [f.label for f in reverted.fields if f.fieldname == "kept_field"],
            ["Original Label"],
        )
        self.assertNotIn(
            "added_later",
            [f.fieldname for f in reverted.fields],
            "a field added after the version must not survive the revert",
        )

    def test_the_reverted_draft_matches_the_version_it_came_from(self):
        """
        The compiler's hash is the whole schema, mapping, theme and success page
        in one value. Equal hashes is the strongest statement that the revert
        was faithful, and it is what makes "Publish changes" go quiet again.
        """
        published_hash = frappe.db.get_value("FP Form Version", self.baseline, "schema_hash")

        form = self._reload()
        form.fields[-1].reqd = 1
        form.append(
            "fields", {"label": "Noise", "fieldname": "noise", "fieldtype": "Data"}
        )
        form.save(ignore_permissions=True)
        self.assertNotEqual(
            FormCompiler(self.form.name).compile()["schema_hash"],
            published_hash,
            "the edit should have moved the draft away from the published version",
        )

        revert_to_version(form_name=self.form.name, version_name=self.baseline)

        self.assertEqual(
            FormCompiler(self.form.name).compile()["schema_hash"],
            published_hash,
        )

    def test_revert_does_not_unpublish_the_form(self):
        """Visitors keep the live version; reverting the draft is not a takedown."""
        before = frappe.db.get_value(
            "Form", self.form.name, ["status", "active_version"], as_dict=True
        )

        form = self._reload()
        form.title = "Edited Title"
        form.save(ignore_permissions=True)

        revert_to_version(form_name=self.form.name, version_name=self.baseline)

        after = frappe.db.get_value(
            "Form", self.form.name, ["status", "active_version"], as_dict=True
        )
        self.assertEqual(before.status, after.status)
        self.assertEqual(before.active_version, after.active_version)

    def test_revert_leaves_the_route_alone(self):
        """
        The route is the form's address. Links and embeds already point at it,
        so restoring an older one would break them to fix nothing.
        """
        form = self._reload()
        form.route = f"forms_pro_revert_{frappe.generate_hash(length=8)}"
        form.save(ignore_permissions=True)

        revert_to_version(form_name=self.form.name, version_name=self.baseline)

        self.assertEqual(self._reload().route, form.route)

    def test_a_version_of_another_form_is_refused(self):
        other = FormFactory.create()
        with self.assertRaises(frappe.ValidationError):
            revert_to_version(form_name=other.name, version_name=self.baseline)
