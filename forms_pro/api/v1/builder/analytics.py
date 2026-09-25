"""Analytics queries for Forms Pro."""
from __future__ import annotations

import frappe


@frappe.whitelist()
def summary(form_name: str, start_date: str | None = None, end_date: str | None = None):
    """Get submission KPIs for a form within a date range."""
    frappe.has_permission("Form", ptype="read", throw=True)

    filters: dict = {"form": form_name}
    if start_date and end_date:
        start_val = f"{start_date} 00:00:00" if len(start_date) == 10 else start_date
        end_val = f"{end_date} 23:59:59" if len(end_date) == 10 else end_date
        filters["submitted_at"] = ["between", [start_val, end_val]]

    submissions = frappe.get_all(
        "FP Form Submission",
        filters=filters,
        fields=["status", "operation"],
        order_by="submitted_at desc",
    )

    total = len(submissions)
    success = sum(1 for s in submissions if s.status == "Success")
    failed = sum(1 for s in submissions if s.status == "Failed")
    created = sum(1 for s in submissions if s.operation in ("Create", "Create New"))
    updated = sum(1 for s in submissions if s.operation in ("Update", "Update Existing"))

    return {
        "total": total,
        "success": success,
        "failed": failed,
        "created": created,
        "updated": updated,
        "conversion_rate": round((success / total * 100) if total > 0 else 0, 1),
    }


@frappe.whitelist()
def timeseries(form_name: str, start_date: str, end_date: str):
    """Get daily submission counts between dates."""
    frappe.has_permission("Form", ptype="read", throw=True)

    start_val = f"{start_date} 00:00:00" if len(start_date) == 10 else start_date
    end_val = f"{end_date} 23:59:59" if len(end_date) == 10 else end_date

    results = frappe.db.sql(
        """
        SELECT DATE(submitted_at) as date, COUNT(*) as count
        FROM `tabFP Form Submission`
        WHERE form = %s AND status = 'Success'
        AND submitted_at BETWEEN %s AND %s
        GROUP BY DATE(submitted_at)
        ORDER BY DATE(submitted_at)
        """,
        (form_name, start_val, end_val),
        as_dict=True,
    )

    return {
        "dates": [str(r.date) for r in results],
        "counts": [r.count for r in results],
    }


@frappe.whitelist()
def sources(form_name: str):
    """Get submission breakdown by source/UTM."""
    frappe.has_permission("Form", ptype="read", throw=True)

    utm_sources = frappe.db.sql(
        """
        SELECT utm_source as source, COUNT(*) as count
        FROM `tabFP Form Submission`
        WHERE form = %s AND status = 'Success' AND utm_source IS NOT NULL AND utm_source != ''
        GROUP BY utm_source
        ORDER BY count DESC LIMIT 10
        """,
        (form_name,),
        as_dict=True,
    )

    referrers = frappe.db.sql(
        """
        SELECT referrer as source, COUNT(*) as count
        FROM `tabFP Form Submission`
        WHERE form = %s AND status = 'Success' AND referrer IS NOT NULL AND referrer != ''
        GROUP BY referrer
        ORDER BY count DESC LIMIT 10
        """,
        (form_name,),
        as_dict=True,
    )

    return {"utm_sources": utm_sources, "referrers": referrers}