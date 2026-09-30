"""The fields a submission is held to: the published version's, not the draft's."""

from __future__ import annotations

import frappe

#: How a field reaches the target record. Snapshotted since these were added to
#: `FormCompiler.SCHEMA_FIELD_PROPS`; a version published before that is
#: completed from the draft's field of the same name.
_MAPPING_PROPS = ("target_field", "source_type", "mapping_type")


def resolve_version(form, requested: str | None = None) -> str | None:
    """
    The version a submission belongs to.

    The one the visitor's page was rendered from when it names a version of
    this form -- publishing again while someone is filling the form in must not
    change the rules their answers are checked against. Otherwise the version
    that is live now.
    """
    if requested and frappe.db.get_value("FP Form Version", requested, "form") == form.name:
        return requested
    return form.get("active_version") or None


def published_fields(form, version: str | None = None) -> list:
    """
    The field list of a published version, shaped like `Form.fields` rows.

    Visitors are served the published snapshot, while the draft is what the
    author is still editing. Validating and mapping against the draft meant an
    unpublished new required field refused every live response, and an
    unpublished removal silently dropped an answer the visitor had given.

    Falls back to the draft only for a form with no readable snapshot -- one
    published before versioning existed -- which is also what its visitors are
    served.
    """
    version = version or form.get("active_version")
    schema_json = version and frappe.db.get_value("FP Form Version", version, "schema_json")
    try:
        schema = frappe.parse_json(schema_json) if schema_json else None
    except Exception:
        schema = None
    if not schema or not schema.get("fields"):
        return list(form.fields)

    draft = {f.fieldname: f for f in form.fields}
    fields = []
    for snapshot in schema["fields"]:
        field = frappe._dict(snapshot)
        if not all(prop in snapshot for prop in _MAPPING_PROPS):
            current = draft.get(field.fieldname)
            for prop in _MAPPING_PROPS:
                if prop not in snapshot:
                    field[prop] = current.get(prop) if current else None
        fields.append(field)
    return fields
