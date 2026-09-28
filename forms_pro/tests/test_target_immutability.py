"""
A form must not rewrite the schema of a DocType it does not own.

A form can point at Lead, Supplier, Sales Order, Contact -- DocTypes that
belong to an app and are used by everyone on the site. Marking a field
mandatory, hidden or read-only *on the form* is a statement about the form, not
about the DocType: it must never reach the record as a Property Setter, a
Custom Field or an edit to an existing column, or one author's questionnaire
would start dictating how the whole site captures leads.

The one opt-in is `Form.create_target_fields`. With it on, answers that have
nowhere to land get a column of their own, inside the Forms Pro tab and nowhere
else -- and still without inheriting the form's validation.

The previous version of this test compared `DocType.fields`, which lists only
the DocType's own columns. Custom Fields and Property Setters are stored apart
and surface only through `frappe.get_meta`, so everything this file exists to
catch was invisible to it. It also built its target in the `Core` module, which
in developer mode wrote a DocType JSON into frappe's own source tree.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from forms_pro.services.authoring.target_fields import FORMS_PRO_TAB
from forms_pro.tests.factories.fp_team_factory import FPTeamFactory

#: Everything Forms Pro may add to a target for traceability: the tab and its
#: four columns, which render only on records a form actually produced.
TRACKING_FIELDNAMES = {
    FORMS_PRO_TAB,
    "fp_submission_status",
    "fp_form_link",
    "fp_submission_link",
    "fp_linked_form",
}


def _schema(doctype: str) -> dict:
    """Every field the desk would render, Custom Fields included."""
    frappe.clear_cache(doctype=doctype)
    return {
        df.fieldname: {
            "label": df.label,
            "fieldtype": df.fieldtype,
            "reqd": df.reqd,
            "hidden": df.hidden,
            "read_only": df.read_only,
            "options": df.options,
        }
        for df in frappe.get_meta(doctype, cached=False).fields
    }


def _property_setters(doctype: str) -> set:
    return set(frappe.get_all("Property Setter", filters={"doc_type": doctype}, pluck="name"))


class TestTargetImmutability(FrappeTestCase):
    def setUp(self):
        # A custom DocType outside the "User Forms" module is one Forms Pro does
        # not own -- what Lead, Supplier and Contact are to a form.
        self.target = "ZZ Immutability Target"
        self._drop_target()

        doc = frappe.new_doc("DocType")
        doc.name = self.target
        doc.module = "Contacts"
        doc.custom = 1
        doc.append("fields", {"fieldname": "given_name", "fieldtype": "Data", "label": "Given Name"})
        doc.append(
            "fields",
            {"fieldname": "kind", "fieldtype": "Select", "label": "Kind", "options": "A\nB"},
        )
        doc.append(
            "permissions",
            {"role": "System Manager", "read": 1, "write": 1, "create": 1, "delete": 1},
        )
        doc.insert(ignore_permissions=True)

        self.team = FPTeamFactory.create()
        self.addCleanup(self._drop_target)

    def _drop_target(self):
        for name in frappe.get_all("Form", filters={"target_doctype": self.target}, pluck="name"):
            frappe.delete_doc("Form", name, force=True, ignore_permissions=True)
        for name in frappe.get_all("Custom Field", filters={"dt": self.target}, pluck="name"):
            frappe.delete_doc("Custom Field", name, force=True, ignore_permissions=True)
        for name in _property_setters(self.target):
            frappe.delete_doc("Property Setter", name, force=True, ignore_permissions=True)
        if frappe.db.exists("DocType", self.target):
            frappe.delete_doc("DocType", self.target, force=True, ignore_permissions=True)

    def _form(self, create_target_fields: int = 0):
        form = frappe.new_doc("Form")
        form.target_doctype = self.target
        form.title = f"Immutability Probe {create_target_fields}"
        form.linked_team_id = self.team.name
        form.document_type = "System"
        form.create_target_fields = create_target_fields
        return form

    def test_form_metadata_never_reaches_a_doctype_it_does_not_own(self):
        before = _schema(self.target)
        setters_before = _property_setters(self.target)

        form = self._form()
        form.append(
            "fields",
            {
                "label": "Renamed On The Form Only",
                "fieldname": "given_name",
                "fieldtype": "Data",
                "source_type": "Target Field",
                "target_field": "given_name",
                "mapping_type": "Direct",
                "reqd": 1,
                "hidden": 1,
                "read_only": 1,
                "description": "help text that belongs to the form",
            },
        )
        form.append(
            "fields",
            {
                "label": "Kind",
                "fieldname": "kind",
                "fieldtype": "Select",
                "source_type": "Target Field",
                "target_field": "kind",
                "mapping_type": "Direct",
                "options": "A\nB\nC on the form only",
                "reqd": 1,
            },
        )
        form.insert(ignore_permissions=True)

        # And again after the fact: relabelling and re-flagging an existing form
        # is the case the author actually hits.
        form.reload()
        form.fields[0].reqd = 0
        form.fields[0].label = "Renamed Twice"
        form.fields[1].options = "A\nB\nD"
        form.save(ignore_permissions=True)

        after = _schema(self.target)

        self.assertEqual(
            setters_before,
            _property_setters(self.target),
            "a form must not write Property Setters onto a DocType it does not own",
        )
        for fieldname, original in before.items():
            self.assertEqual(
                original,
                after[fieldname],
                f"{fieldname} was altered on {self.target} by editing the form",
            )
        self.assertEqual(
            set(after) - set(before),
            TRACKING_FIELDNAMES,
            "only the Forms Pro tab and its tracking columns may be added",
        )

    def test_unmapped_answers_get_no_column_unless_the_author_opts_in(self):
        before = _schema(self.target)

        form = self._form(create_target_fields=0)
        form.append(
            "fields",
            {
                "label": "Where Did You Hear About Us",
                "fieldtype": "Data",
                "fieldname": "heard_from",
            },
        )
        form.insert(ignore_permissions=True)

        self.assertEqual(
            set(_schema(self.target)) - set(before),
            TRACKING_FIELDNAMES,
            "an answer with nowhere to land must not create a column on its own",
        )

    def test_opting_in_adds_the_column_without_the_forms_validation(self):
        form = self._form(create_target_fields=1)
        form.append(
            "fields",
            {
                "label": "Where Did You Hear About Us",
                "fieldtype": "Data",
                "fieldname": "heard_from",
                "reqd": 1,
                "hidden": 1,
                "read_only": 1,
            },
        )
        form.insert(ignore_permissions=True)

        added = frappe.get_all(
            "Custom Field",
            filters={"dt": self.target, "label": "Where Did You Hear About Us"},
            fields=["fieldname", "reqd", "hidden", "read_only", "insert_after"],
        )
        self.assertEqual(len(added), 1, "the opt-in should create exactly one column")
        column = added[0]

        # Mandatory here would block every other way of editing the record, and
        # hidden or read-only would bury an answer the record is meant to show.
        self.assertFalse(column.reqd)
        self.assertFalse(column.hidden)
        self.assertFalse(column.read_only)
        self.assertEqual(
            column.insert_after,
            FORMS_PRO_TAB,
            "columns Forms Pro adds belong inside its own tab, not the DocType's layout",
        )
        self.assertEqual(
            _property_setters(self.target),
            set(),
            "opting into columns is not permission to reorder or restyle the DocType",
        )
