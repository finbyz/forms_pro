"""Team authorisation.

The `Forms Pro User` role grants doctype-level read/write on FP Team with no
ownership condition, so frappe.has_permission() returns True for any Forms Pro
user whether or not they belong to the team. Membership is therefore checked
explicitly here rather than relying on doctype permissions.
"""

import frappe
from frappe import _

from forms_pro.forms_pro.doctype.fp_team.fp_team import FPTeam, ROLE_ADMIN


def get_team(team_id: str) -> FPTeam:
    if not team_id or not frappe.db.exists("FP Team", team_id):
        frappe.throw(_("Team not found"), frappe.DoesNotExistError)
    return frappe.get_doc("FP Team", team_id)


def require_member(team_id: str, user: str | None = None) -> FPTeam:
    """Any member may read the team."""
    user = user or frappe.session.user
    team = get_team(team_id)

    # System Managers keep desk-level oversight.
    if "System Manager" in frappe.get_roles(user):
        return team

    if not team.is_team_member(user):
        frappe.throw(_("You are not a member of this team"), frappe.PermissionError)
    return team


def require_admin(team_id: str, user: str | None = None) -> FPTeam:
    """Only admins (and the owner) may change the team or its members."""
    user = user or frappe.session.user
    team = get_team(team_id)

    if "System Manager" in frappe.get_roles(user):
        return team

    if not team.is_team_member(user):
        frappe.throw(_("You are not a member of this team"), frappe.PermissionError)

    if not team.is_admin(user):
        frappe.throw(
            _("Only team admins can do this. Ask an admin of this team for access."),
            frappe.PermissionError,
        )
    return team


def require_owner(team_id: str, user: str | None = None) -> FPTeam:
    user = user or frappe.session.user
    team = get_team(team_id)

    if "System Manager" in frappe.get_roles(user):
        return team

    if team.owner != user:
        frappe.throw(_("Only the team owner can do this"), frappe.PermissionError)
    return team


def assert_role_value(role: str) -> str:
    from forms_pro.forms_pro.doctype.fp_team.fp_team import TEAM_ROLES

    if role not in TEAM_ROLES:
        frappe.throw(_("Unknown team role: {0}").format(role), frappe.ValidationError)
    return role


__all__ = [
    "ROLE_ADMIN",
    "assert_role_value",
    "get_team",
    "require_admin",
    "require_member",
    "require_owner",
]
