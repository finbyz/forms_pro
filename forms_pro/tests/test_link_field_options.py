"""
A visitor may only list what the form in front of them actually asks for.

`get_link_field_options` allows guests and takes the DocType from the browser,
and `frappe.get_all` does not check permissions -- so it once answered
`doctype=User` for anyone who asked, handing out every account on the site. A
public form with a Company field still has to show company names; everything
else is refused.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from forms_pro.api.form.endpoints import get_doctype_fields, get_link_field_options
from forms_pro.tests.factories.form_factory import FormFactory


#: A DocType no form on this site links to, so a refusal proves the rule rather
#: than the data. Checked in setUp, because a form added later could offer it.
UNOFFERED_DOCTYPE = "Role"


def _offered_to_guests(doctype: str) -> bool:
    return bool(
        frappe.db.sql(
            """
            SELECT 1 FROM `tabForm Field` ff
            INNER JOIN `tabForm` f ON f.name = ff.parent
            WHERE ff.parenttype = 'Form' AND ff.fieldtype = 'Link'
              AND ff.options = %(doctype)s AND ff.hidden = 0
              AND f.is_published = 1 AND f.login_required = 0
            LIMIT 1
            """,
            {"doctype": doctype},
        )
    )


class TestLinkFieldOptions(FrappeTestCase):
    def setUp(self):
        # Only a *published, guest-facing* form opens a DocType up, which is the
        # same condition the endpoint applies. Checking anything broader made
        # this suite skip itself as soon as one of its own fixtures existed.
        if _offered_to_guests(UNOFFERED_DOCTYPE):
            self.skipTest(f"a public form on this site now links to {UNOFFERED_DOCTYPE}")

        self.form = FormFactory.create()
        self.form.append(
            "fields",
            {
                "label": "Language",
                "fieldname": "chosen_language",
                "fieldtype": "Link",
                "options": "Language",
            },
        )
        self.form.is_published = 1
        self.form.access_mode = "Public"
        self.form.save(ignore_permissions=True)
        self.addCleanup(frappe.set_user, "Administrator")
        self.addCleanup(
            frappe.delete_doc, "Form", self.form.name, force=True, ignore_permissions=True
        )

    def test_a_guest_may_list_a_doctype_a_public_form_links_to(self):
        frappe.set_user("Guest")
        self.assertTrue(get_link_field_options(doctype="Language", page_length=5))

    def test_a_guest_may_not_list_an_unrelated_doctype(self):
        frappe.set_user("Guest")
        with self.assertRaises(frappe.PermissionError):
            get_link_field_options(doctype=UNOFFERED_DOCTYPE, page_length=5)

    def _form_linking_to_unoffered(self, **flags):
        form = FormFactory.create()
        form.append(
            "fields",
            {
                "label": "Owner",
                "fieldname": "record_owner",
                "fieldtype": "Link",
                "options": UNOFFERED_DOCTYPE,
            },
        )
        for key, value in flags.items():
            form.set(key, value)
        form.save(ignore_permissions=True)
        # The factory commits, so a fixture outlives the test unless it is
        # removed here -- and a stray Role-linked form would skip this suite.
        self.addCleanup(
            frappe.delete_doc, "Form", form.name, force=True, ignore_permissions=True
        )
        return form

    def test_a_guest_may_not_list_a_doctype_only_a_login_only_form_links_to(self):
        self._form_linking_to_unoffered(is_published=1, access_mode="Requires Login")

        frappe.set_user("Guest")
        with self.assertRaises(frappe.PermissionError):
            get_link_field_options(doctype=UNOFFERED_DOCTYPE, page_length=5)

    def test_a_guest_may_not_list_a_doctype_behind_an_unpublished_form(self):
        self._form_linking_to_unoffered(is_published=0)

        frappe.set_user("Guest")
        with self.assertRaises(frappe.PermissionError):
            get_link_field_options(doctype=UNOFFERED_DOCTYPE, page_length=5)

    def test_a_guests_filters_are_ignored(self):
        """A filter is a query the caller writes; a visitor does not get to."""
        frappe.set_user("Guest")
        filtered = get_link_field_options(
            doctype="Language",
            filters={"name": ["like", "%definitely-no-such-language%"]},
            page_length=5,
        )
        self.assertTrue(filtered, "a crafted filter must not be applied")

    def test_the_page_length_is_capped(self):
        frappe.set_user("Guest")
        self.assertLessEqual(
            len(get_link_field_options(doctype="Language", page_length=100000)),
            100,
        )


class TestGuestTableColumns(FrappeTestCase):
    """
    Linking an existing table means its schema is the whole configuration, so a
    visitor has to be able to read that schema and look up its Link columns --
    and nothing else. Scoping this to the form's own fields left every dropdown
    inside a table row empty.
    """

    CHILD = "Contact Email"

    def setUp(self):
        self.form = FormFactory.create()
        self.form.append(
            "fields",
            {
                "label": "Emails",
                "fieldname": "email_rows",
                "fieldtype": "Table",
                "options": self.CHILD,
            },
        )
        self.form.is_published = 1
        self.form.access_mode = "Public"
        self.form.save(ignore_permissions=True)
        self.addCleanup(frappe.set_user, "Administrator")
        self.addCleanup(
            frappe.delete_doc, "Form", self.form.name, force=True, ignore_permissions=True
        )

    def test_a_guest_can_read_the_schema_of_a_table_the_form_uses(self):
        frappe.set_user("Guest")
        self.assertTrue(get_doctype_fields(doctype=self.CHILD))

    def test_a_guest_cannot_read_the_schema_of_anything_else(self):
        frappe.set_user("Guest")
        with self.assertRaises(frappe.PermissionError):
            get_doctype_fields(doctype="User")

    def test_a_guest_can_resolve_a_link_column_inside_that_table(self):
        link_targets = {
            df.options
            for df in frappe.get_meta(self.CHILD).fields
            if df.fieldtype == "Link" and df.options
        }
        if not link_targets:
            self.skipTest(f"{self.CHILD} has no Link column to resolve")

        frappe.set_user("Guest")
        for target in link_targets:
            # Must not raise: the row cannot be filled in without these.
            get_link_field_options(doctype=target, page_length=3)

    def test_nested_tables_and_hidden_columns_are_left_out(self):
        columns = get_doctype_fields(doctype=self.CHILD)
        self.assertFalse(
            [c for c in columns if c.fieldtype == "Table" or c.hidden],
            "a nested table has no renderer and a hidden column is not the visitor's to fill",
        )
