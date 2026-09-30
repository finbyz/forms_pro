"""
A form's record-name pattern must count from 1, per prefix.

The pattern used to be stored as a Frappe `format:` rule. Frappe resolves each
braced part of those on its own, so `{######}` was looked up with nothing in
front of it -- and every such pattern on the site shared one counter under an
empty key. A form expecting CR-2026-000001 got CR-2026-067163.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from forms_pro.forms_pro.doctype.form.form import to_naming_series


class TestToNamingSeries(FrappeTestCase):
    def test_braces_become_series_parts(self):
        self.assertEqual(to_naming_series("CR-{YYYY}-{######}"), "CR-.YYYY.-.######")

    def test_several_date_tokens(self):
        self.assertEqual(to_naming_series("ENQ-{YY}{MM}-{#####}"), "ENQ-.YY.MM.-.#####")

    def test_a_fieldname_keeps_its_braces(self):
        """Without braces Frappe would print the fieldname as literal text."""
        self.assertEqual(to_naming_series("SUP/{company}/{####}"), "SUP/.{company}./.####")

    def test_the_counter_is_keyed_on_everything_before_it(self):
        """The whole point: `CR-2026-` gets a counter of its own."""
        from frappe.model.naming import parse_naming_series

        seen = {}

        def counter(key, digits):
            seen["key"] = key
            return "1".zfill(digits)

        name = parse_naming_series(to_naming_series("CR-{YYYY}-{######}"), number_generator=counter)
        year = frappe.utils.now_datetime().strftime("%Y")
        self.assertEqual(seen["key"], f"CR-{year}-")
        self.assertEqual(name, f"CR-{year}-000001")


class TestExistingDocTypeNaming(FrappeTestCase):
    """An existing DocType keeps ERPNext's naming, described as ERPNext applies it."""

    def test_supplier_follows_buying_settings_not_its_definition(self):
        from forms_pro.api.form.endpoints import describe_naming

        chosen = frappe.db.get_single_value("Buying Settings", "supp_master_name")
        naming = describe_naming("Supplier")
        if chosen and chosen != "Naming Series":
            self.assertEqual(naming["summary"], f"By {chosen}")
            self.assertEqual(naming["series"], [])
        else:
            self.assertEqual(naming["summary"], "By naming series")
        self.assertIn("Buying Settings", naming["configured_in"])

    def test_a_naming_series_doctype_lists_its_series(self):
        from forms_pro.api.form.endpoints import describe_naming

        naming = describe_naming("Lead")
        self.assertEqual(naming["summary"], "By naming series")
        self.assertTrue(naming["series"])
