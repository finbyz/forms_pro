"""Paged, filtered reads of a form's submissions.

A form that collects for a year holds more rows than any browser should be
handed at once, so every listing here is bounded and every filter is resolved
in SQL rather than over an already-truncated page. Filtering a loaded page is
worse than not filtering at all: it looks like a search and quietly answers
from the first fifty rows.

Authorization is the Form, not the row: a caller proves ``read`` on the form
and this module pins the query to it, so no argument can widen the result to
another team's submissions.
"""
from __future__ import annotations

import json
from typing import Any

import frappe
from frappe import _

# Frappe's own list view offers 20 / 100 / 500. Matching it keeps the ceiling
# somewhere an operator already understands.
PAGE_LENGTHS = (20, 100, 500)
MAX_PAGE_LENGTH = 500
DEFAULT_PAGE_LENGTH = 20

# Columns a caller may read, filter or sort by. Anything absent here is not a
# column this API exposes, whatever the table happens to hold.
LISTABLE_FIELDS = (
    "name",
    "form",
    "form_version",
    "route",
    "submitted_at",
    "creation",
    "modified",
    "owner",
    "status",
    "processing_status",
    "operation",
    "target_doctype",
    "target_name",
    "error_code",
    "error_summary",
    "retry_count",
    "source_url",
    "referrer",
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "gclid",
)

DEFAULT_FIELDS = (
    "name",
    "submitted_at",
    "creation",
    "modified",
    "owner",
    "status",
    "processing_status",
    "operation",
    "target_doctype",
    "target_name",
    "error_summary",
    "utm_source",
    "utm_campaign",
)

# Free-text search spans the columns an operator would actually type into.
SEARCH_FIELDS = ("name", "target_name", "source_url", "utm_source", "utm_campaign", "error_summary")

# Layout, not questions. A heading or page break stores no answer, so offering
# it as a filter would only produce a filter that can never match.
NON_ANSWER_FIELDTYPES = {"Heading 1", "Heading 2", "Heading 3", "Page Break"}

OPERATORS = {
    "=": "=",
    "!=": "!=",
    ">": ">",
    "<": "<",
    ">=": ">=",
    "<=": "<=",
    "like": "like",
    "not like": "not like",
    "in": "in",
    "not in": "not in",
    "is set": "is set",
    "is not set": "is not set",
    "between": "between",
}


class SubmissionQueryError(frappe.ValidationError):
    """A listing argument that cannot be honoured safely."""


def coerce_page_length(value: Any) -> int:
    """Clamp a requested page size into the supported range."""
    try:
        length = int(value)
    except (TypeError, ValueError):
        return DEFAULT_PAGE_LENGTH
    if length <= 0:
        return DEFAULT_PAGE_LENGTH
    return min(length, MAX_PAGE_LENGTH)


def coerce_start(value: Any) -> int:
    try:
        start = int(value)
    except (TypeError, ValueError):
        return 0
    return max(start, 0)


def _parse(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (ValueError, TypeError):
            return value
    return value


def _field(name: Any) -> str:
    fieldname = str(name or "").strip()
    if fieldname not in LISTABLE_FIELDS:
        raise SubmissionQueryError(_("{0} is not a filterable submission field.").format(fieldname or "?"))
    return fieldname


def _operator(value: Any) -> str:
    operator = str(value or "=").strip().lower()
    if operator not in OPERATORS:
        raise SubmissionQueryError(_("{0} is not a supported filter operator.").format(operator))
    return operator


def _condition(column: str, operator: str, value: Any) -> tuple[str, list]:
    """One SQL fragment plus its bound values. Identifiers are allowlisted above."""
    if operator == "is set":
        return f"{column} is not null and {column} != ''", []
    if operator == "is not set":
        return f"({column} is null or {column} = '')", []
    if operator in ("in", "not in"):
        values = value if isinstance(value, (list, tuple)) else [value]
        values = [v for v in values if v is not None]
        if not values:
            # An empty set matches nothing; say so rather than emitting `in ()`.
            return ("1 = 0" if operator == "in" else "1 = 1"), []
        placeholders = ", ".join(["%s"] * len(values))
        return f"{column} {operator} ({placeholders})", list(values)
    if operator == "between":
        values = value if isinstance(value, (list, tuple)) else []
        if len(values) != 2:
            raise SubmissionQueryError(_("A between filter needs exactly two values."))
        return f"{column} between %s and %s", list(values)
    if operator in ("like", "not like"):
        text = str(value or "")
        if "%" not in text:
            text = f"%{text}%"
        return f"{column} {operator} %s", [text]
    return f"{column} {operator} %s", [value]


def _answer_condition(field_key: str, operator: str, value: Any) -> tuple[str, list]:
    """Filter on one of the form's own questions, stored inside the payload JSON.

    The key is bound as a value, never interpolated, so a crafted key cannot
    escape into the JSON path or the surrounding SQL.
    """
    column = "json_unquote(json_extract(payload, concat('$.', %s)))"
    if operator == "is set":
        return f"({column} is not null and {column} != '')", [field_key]
    if operator == "is not set":
        return f"({column} is null or {column} = '')", [field_key]
    if operator in ("in", "not in"):
        values = value if isinstance(value, (list, tuple)) else [value]
        values = [str(v) for v in values if v is not None]
        if not values:
            return ("1 = 0" if operator == "in" else "1 = 1"), []
        placeholders = ", ".join(["%s"] * len(values))
        return f"{column} {operator} ({placeholders})", [field_key, *values]
    if operator == "between":
        values = value if isinstance(value, (list, tuple)) else []
        if len(values) != 2:
            raise SubmissionQueryError(_("A between filter needs exactly two values."))
        return f"{column} between %s and %s", [field_key, *values]
    if operator in ("like", "not like"):
        text = str(value or "")
        if "%" not in text:
            text = f"%{text}%"
        return f"{column} {operator} %s", [field_key, text]
    return f"{column} {operator} %s", [field_key, value]


def _order_by(value: Any) -> str:
    raw = str(value or "").strip() or "submitted_at desc"
    parts = raw.replace(",", " ").split()
    if not parts:
        return "`submitted_at` desc"
    fieldname = _field(parts[0].strip("`"))
    direction = (parts[1].lower() if len(parts) > 1 else "desc")
    if direction not in ("asc", "desc"):
        raise SubmissionQueryError(_("Sort direction must be asc or desc."))
    # `name` keeps the page boundary stable when the sort column ties, so a row
    # cannot appear on two pages or be skipped between them.
    return f"`{fieldname}` {direction}, `name` {direction}"


def _fields(requested: Any) -> list[str]:
    values = _parse(requested)
    if not isinstance(values, (list, tuple)) or not values:
        return list(DEFAULT_FIELDS)
    chosen = [_field(item) for item in values]
    if "name" not in chosen:
        chosen.insert(0, "name")
    return chosen


def build_where(
    form_id: str,
    filters: Any = None,
    answer_filters: Any = None,
    search: Any = None,
) -> tuple[str, list]:
    """Compose the WHERE clause. The form pin is first and cannot be overridden."""
    clauses = ["`form` = %s"]
    values: list = [form_id]

    for entry in _parse(filters) or []:
        if isinstance(entry, dict):
            fieldname, operator, value = entry.get("field"), entry.get("operator"), entry.get("value")
        elif isinstance(entry, (list, tuple)) and len(entry) >= 2:
            fieldname, operator, value = entry[0], entry[1], (entry[2] if len(entry) > 2 else None)
        else:
            raise SubmissionQueryError(_("A filter must be a field, operator and value."))
        column = f"`{_field(fieldname)}`"
        clause, bound = _condition(column, _operator(operator), value)
        clauses.append(clause)
        values.extend(bound)

    for entry in _parse(answer_filters) or []:
        if isinstance(entry, dict):
            key, operator, value = entry.get("field"), entry.get("operator"), entry.get("value")
        elif isinstance(entry, (list, tuple)) and len(entry) >= 2:
            key, operator, value = entry[0], entry[1], (entry[2] if len(entry) > 2 else None)
        else:
            raise SubmissionQueryError(_("An answer filter must be a field, operator and value."))
        key = str(key or "").strip()
        if not key:
            raise SubmissionQueryError(_("An answer filter needs a form field."))
        clause, bound = _answer_condition(key, _operator(operator), value)
        clauses.append(clause)
        values.extend(bound)

    text = str(search or "").strip()
    if text:
        like = f"%{text}%"
        parts = [f"`{field}` like %s" for field in SEARCH_FIELDS]
        # The payload is searched too, so an operator can find a submission by
        # something the visitor typed rather than only by its id.
        parts.append("`payload` like %s")
        clauses.append("(" + " or ".join(parts) + ")")
        values.extend([like] * (len(SEARCH_FIELDS) + 1))

    return " and ".join(clauses), values


def list_form_submissions(
    form_id: str,
    filters: Any = None,
    answer_filters: Any = None,
    search: Any = None,
    order_by: Any = None,
    limit_start: Any = 0,
    limit_page_length: Any = DEFAULT_PAGE_LENGTH,
    fields: Any = None,
    include_payload: Any = False,
) -> dict:
    """One bounded page of a form's submissions, with the matching total."""
    page_length = coerce_page_length(limit_page_length)
    start = coerce_start(limit_start)
    selected = _fields(fields)
    if frappe.parse_json(include_payload) if isinstance(include_payload, str) else include_payload:
        selected = [*selected, "payload", "response_json"]

    where, values = build_where(form_id, filters, answer_filters, search)
    columns = ", ".join(f"`{field}`" for field in selected)

    rows = frappe.db.sql(
        f"select {columns} from `tabFP Form Submission` where {where} order by {_order_by(order_by)} limit %s offset %s",
        [*values, page_length, start],
        as_dict=True,
    )
    # Counted with the same predicate, so the pager reflects the filtered set
    # rather than the form's lifetime total.
    total = frappe.db.sql(
        f"select count(*) from `tabFP Form Submission` where {where}", values
    )[0][0]

    return {
        "rows": rows,
        "total": int(total),
        "limit_start": start,
        "limit_page_length": page_length,
        "has_more": start + len(rows) < int(total),
        "page_lengths": list(PAGE_LENGTHS),
    }


def submission_filter_fields(form_id: str) -> dict:
    """What an operator may filter by: the row's own columns, and the form's questions."""
    meta = frappe.get_meta("FP Form Submission")
    labels = {df.fieldname: df.label for df in meta.fields if df.fieldname}
    options = {df.fieldname: df.options for df in meta.fields if df.fieldname}
    fieldtypes = {df.fieldname: df.fieldtype for df in meta.fields if df.fieldname}
    standard = {"name": "ID", "owner": "Submitted By", "creation": "Created On", "modified": "Last Modified"}

    columns = [
        {
            "field": field,
            "label": labels.get(field) or standard.get(field) or field.replace("_", " ").title(),
            "fieldtype": fieldtypes.get(field) or ("Datetime" if field in ("creation", "modified") else "Data"),
            "options": options.get(field),
        }
        for field in LISTABLE_FIELDS
        if field != "form"
    ]

    answers = []
    for row in frappe.get_all(
        "Form Field",
        filters={
            "parent": form_id,
            "parenttype": "Form",
            "fieldtype": ("not in", sorted(NON_ANSWER_FIELDTYPES)),
        },
        fields=["fieldname", "field_key", "label", "fieldtype"],
        order_by="idx asc",
    ):
        key = row.get("field_key") or row.get("fieldname")
        if not key:
            continue
        answers.append(
            {
                "field": key,
                "label": row.get("label") or key,
                "fieldtype": row.get("fieldtype") or "Data",
            }
        )

    return {
        "columns": columns,
        "answers": answers,
        "operators": sorted(OPERATORS),
        "page_lengths": list(PAGE_LENGTHS),
    }
