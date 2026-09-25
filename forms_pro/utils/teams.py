from datetime import datetime
from typing import Any

import frappe
from frappe.defaults import get_user_default, set_user_default
from frappe.query_builder import Case
from pydantic import BaseModel, Field, field_validator


class GetTeamFormsResponseSchema(BaseModel):
    """
    Schema for the response of the get_team_forms function
    """

    name: str = Field(description="ID of the form")
    title: str = Field(description="Title of the form")
    description: str | None = Field(default="", description="Description of the form")
    route: str | None = Field(default="", description="Route of the form")
    is_published: bool = Field(description="Whether the form is published")
    creation: datetime = Field(description="Creation date of the form")
    modified: datetime = Field(description="Modification date of the form")
    linked_team_id: str = Field(description="Team ID of the form")
    target_doctype: str | None = Field(default=None, description="Where submissions are stored")
    submission_count: int = Field(default=0, description="Successful submissions")
    last_submission_at: datetime | None = Field(
        default=None, description="When the most recent submission arrived"
    )

    @field_validator("last_submission_at", mode="before")
    @classmethod
    def parse_optional_datetime(cls, v: Any) -> datetime | None:
        if v in (None, ""):
            return None
        if isinstance(v, str):
            return frappe.utils.get_datetime(v)
        return v

    @field_validator("creation", "modified", mode="before")
    @classmethod
    def parse_datetime(cls, v: Any) -> datetime:
        """Convert datetime string to datetime object."""
        if isinstance(v, str):
            return frappe.utils.get_datetime(v)
        if isinstance(v, datetime):
            return v
        raise ValueError(f"Invalid datetime value: {v}")

    @field_validator("is_published", mode="before")
    @classmethod
    def parse_boolean(cls, v: Any) -> bool:
        """Convert 0/1 to boolean."""
        if isinstance(v, bool):
            return v
        if isinstance(v, int):
            return bool(v)
        if v is None:
            return False
        raise ValueError(f"Invalid boolean value: {v}")

    @field_validator("description", "route", mode="before")
    @classmethod
    def handle_none_strings(cls, v: Any) -> str | None:
        """Handle None values for optional string fields."""
        if v is None:
            return ""
        return v


def get_user_teams(user: str | None = None, create_if_empty: bool = False):
    """
    Get all Forms Pro teams for a user
    """
    if user is None:
        user = getattr(frappe.session, "user", None)
    if not user or user == "Guest":
        return []

    FP_TEAM = frappe.qb.DocType("FP Team")
    FP_TEAM_MEMBER = frappe.qb.DocType("FP Team Member")

    user_default_team = get_user_default("current_team", user)

    query = (
        frappe.qb.from_(FP_TEAM)
        .join(FP_TEAM_MEMBER)
        .on(FP_TEAM.name == FP_TEAM_MEMBER.parent)
        .where(FP_TEAM_MEMBER.user == user)
        .select(
            FP_TEAM.team_name,
            FP_TEAM.logo,
            FP_TEAM.name,
            Case().when(FP_TEAM.name == user_default_team, True).else_(False).as_("is_current"),
        )
        .orderby(FP_TEAM.creation)
    )
    teams = query.run(as_dict=True)

    # Deduplicate and filter out test artifacts left behind by automated test runs
    filtered_teams = []
    seen = set()
    for team in teams:
        t_id = team.get("name")
        t_name = team.get("team_name") or ""
        if t_id in seen:
            continue
        if t_name.lower().startswith(("zz.", "zz2.", "test_", "test-")):
            continue
        seen.add(t_id)
        filtered_teams.append(team)

    teams = filtered_teams

    if not teams and user != "Guest" and create_if_empty:
        # Create default team for user so they are never stranded without a team
        user_first_name = frappe.db.get_value("User", user, "first_name") or user
        team = frappe.new_doc("FP Team")
        team.team_name = f"{user_first_name}'s Team"
        team.owner = user
        team.insert(ignore_permissions=True)
        set_current_team(team.name, user)
        return [{
            "team_name": team.team_name,
            "logo": None,
            "name": team.name,
            "is_current": True,
        }]

    # The stored default can point at a team the user has been removed from,
    # or one that no longer exists (or filtered out test team). Treat that as "unset"
    # instead of leaving every team flagged not-current.
    known_teams = {team["name"] for team in teams}
    if teams and (user_default_team is None or user_default_team not in known_teams):
        for t in teams:
            t["is_current"] = False
        teams[0]["is_current"] = True
        set_user_default("current_team", teams[0]["name"])

    return teams or []


def set_current_team(team_name: str, user: str | None = None):
    if user is None:
        user = getattr(frappe.session, "user", None)
    set_user_default("current_team", team_name, user)


def get_team_forms(team_id: str) -> list[GetTeamFormsResponseSchema]:
    """
    Forms for a team, with the numbers that tell you whether each one is alive.

    Stats are gathered with two grouped queries rather than per-form lookups,
    so the dashboard stays O(1) in round trips however many forms there are.
    """
    forms = frappe.get_all(
        "Form",
        filters={"linked_team_id": team_id},
        fields=[
            "name",
            "title",
            "description",
            "route",
            "is_published",
            "creation",
            "modified",
            "linked_team_id",
            "target_doctype",
        ],
        order_by="modified desc",
    )
    if not forms:
        return []

    form_ids = [f.name for f in forms]
    stats = _submission_stats(form_ids)

    data = []
    for form in forms:
        stat = stats.get(form.name, {})
        form["submission_count"] = stat.get("count", 0)
        form["last_submission_at"] = stat.get("last")
        data.append(GetTeamFormsResponseSchema.model_validate(form).model_dump())

    return data


def _submission_stats(form_ids: list[str]) -> dict[str, dict]:
    """Successful submission count and latest timestamp, per form."""
    if not form_ids:
        return {}

    # get_all rejects SQL functions in `fields` on this version, and one grouped
    # query beats a count per form.
    rows = frappe.db.sql(
        """
        select form, count(name) as `count`, max(submitted_at) as `last`
        from `tabFP Form Submission`
        where status = 'Success' and form in %(forms)s
        group by form
        """,
        {"forms": tuple(form_ids)},
        as_dict=True,
    )
    return {r["form"]: {"count": r["count"], "last": r["last"]} for r in rows}
