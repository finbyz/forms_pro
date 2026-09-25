"""Team management.

Two roles: Admin and Member.

  * Member — can see the team and its forms.
  * Admin  — everything a member can do, plus rename the team and manage members.
  * Owner  — always an Admin, cannot be removed or demoted.

Authorisation goes through forms_pro.utils.team_access rather than
frappe.has_permission, because the `Forms Pro User` role grants doctype-level
read/write on FP Team to every Forms Pro user, member or not.
"""

import frappe
from frappe import _
from frappe.core.api.user_invitation import invite_by_email
from frappe.core.doctype.user_invitation.user_invitation import UserInvitation

from forms_pro.forms_pro.doctype.fp_team.fp_team import (
    ROLE_ADMIN,
    ROLE_MEMBER,
    FPTeam,
    GetTeamMembersResponse,
)
from forms_pro.utils.team_access import (
    assert_role_value,
    require_admin,
    require_member,
    require_owner,
)
from forms_pro.utils.teams import (
    GetTeamFormsResponseSchema,
    set_current_team,
)
from forms_pro.utils.teams import (
    get_team_forms as get_team_forms_utils,
)

# ---------------------------------------------------------------- reading


@frappe.whitelist()
def get_team_for_manage(team_id: str) -> dict:
    """Team details plus the caller's own role, so the UI knows what to show."""
    team = require_member(team_id)
    me = frappe.session.user
    return {
        "name": team.name,
        "team_name": team.team_name,
        "logo": team.logo,
        "owner": team.owner,
        "my_role": team.get_role(me) or ROLE_ADMIN,
        "is_owner": team.owner == me,
        "member_count": len(team.users or []),
    }


@frappe.whitelist()
def get_team_members(team_id: str) -> list[GetTeamMembersResponse]:
    """The team roster. Members only."""
    team = require_member(team_id)
    return team.team_members


@frappe.whitelist()
def get_team_forms(team_id: str) -> list[GetTeamFormsResponseSchema]:
    """Forms belonging to the team. Members only — this used to be unguarded."""
    require_member(team_id)
    return get_team_forms_utils(team_id=team_id)


@frappe.whitelist()
def get_users_for_team_addition(team_id: str | None = None) -> list[dict]:
    """Active system users who are not yet members. Admins only."""
    if not team_id:
        from forms_pro.utils.teams import get_current_team_id
        team_id = get_current_team_id(frappe.session.user)
    if not team_id:
        return []

    team = require_admin(team_id)

    existing_members = {member.user for member in (team.users or [])}
    existing_members.add("Guest")

    users = frappe.get_all(
        "User",
        filters={"enabled": 1, "name": ["!=", "Guest"]},
        fields=["name", "full_name", "user_image"],
        order_by="full_name asc",
    )

    return [
        {
            "label": u.full_name or u.name,
            "value": u.name,
            "email": u.name,
            "user_image": u.user_image,
        }
        for u in users
        if u.name not in existing_members
    ]


# ---------------------------------------------------------------- lifecycle


@frappe.whitelist(methods=["POST"])
def create_team(team_name: str, logo_url: str | None = None) -> FPTeam:
    """Create a team. The creator becomes its owner and first admin."""
    team_name = (team_name or "").strip()
    if not team_name:
        frappe.throw(_("Please enter a team name."), frappe.ValidationError)

    team: FPTeam = frappe.new_doc("FP Team")
    team.team_name = team_name
    if logo_url:
        team.logo = logo_url
    team.insert()
    return team


@frappe.whitelist(methods=["POST"])
def save(team_id: str, fields: dict) -> None:
    """Update team details. Admins only."""
    ALLOWED_SAVE_FIELDS = ("team_name", "logo")

    team = require_admin(team_id)

    for key, value in (fields or {}).items():
        if key not in ALLOWED_SAVE_FIELDS:
            frappe.throw(_("Field '{0}' is not allowed").format(key), frappe.ValidationError)
        if key == "team_name" and not (value or "").strip():
            frappe.throw(_("Team name cannot be empty."), frappe.ValidationError)
        setattr(team, key, value)

    team.save(ignore_permissions=True)


@frappe.whitelist(methods=["POST"])
def delete_team(team_id: str) -> dict:
    """
    Delete a team. Owner only.

    Refuses while forms still belong to it — deleting would orphan them and
    their submissions.
    """
    team = require_owner(team_id)

    form_count = frappe.db.count("Form", {"linked_team_id": team_id})
    if form_count:
        frappe.throw(
            _("This team still has {0} form(s). Move or delete them first.").format(form_count),
            frappe.ValidationError,
        )

    members = [m.user for m in team.users or []]
    frappe.delete_doc("FP Team", team_id, ignore_permissions=True)

    # Anyone whose current team was this one gets re-pointed on next read.
    for user in members:
        if frappe.defaults.get_user_default("current_team", user) == team_id:
            frappe.defaults.clear_user_default("current_team", user)

    return {"deleted": team_id}


@frappe.whitelist(methods=["POST"])
def leave_team(team_id: str) -> dict:
    """Leave a team. The owner must transfer ownership or delete it instead."""
    team = require_member(team_id)
    me = frappe.session.user

    if team.owner == me:
        frappe.throw(
            _("You own this team. Delete it instead, or transfer it first."),
            frappe.ValidationError,
        )

    team.remove_from_team(me)
    if frappe.defaults.get_user_default("current_team", me) == team_id:
        frappe.defaults.clear_user_default("current_team", me)

    return {"left": team_id}


@frappe.whitelist(methods=["POST"])
def switch_team(team_id: str) -> None:
    """Make a team the caller's current team. Members only."""
    require_member(team_id)
    set_current_team(team_id, frappe.session.user)


# ---------------------------------------------------------------- membership


@frappe.whitelist(methods=["POST"])
def add_team_member(team_id: str | None = None, user_email: str | None = None, role: str = ROLE_MEMBER) -> None:
    """Add an existing Frappe user to the team. Admins only."""
    if not team_id:
        from forms_pro.utils.teams import get_current_team_id
        team_id = get_current_team_id(frappe.session.user)
    if not team_id:
        frappe.throw(_("Team ID is required"), frappe.ValidationError)

    team = require_admin(team_id)
    assert_role_value(role)

    if not user_email:
        frappe.throw(_("User email is required"), frappe.ValidationError)

    if not frappe.db.exists("User", user_email):
        frappe.throw(_("User {0} does not exist").format(user_email), frappe.DoesNotExistError)

    if team.is_team_member(user_email):
        frappe.throw(_("User is already a member of the team"), frappe.DuplicateEntryError)

    team.add_to_team(user_email, role=role)
    team.save(ignore_permissions=True)

    if not frappe.defaults.get_user_default("current_team", user_email):
        set_current_team(team_id, user_email)


@frappe.whitelist(methods=["POST"])
def remove_member_from_team(team_id: str, member_email: str) -> None:
    """Remove a member. Admins only. The owner cannot be removed."""
    team = require_admin(team_id)
    team.remove_from_team(member_email)

    if frappe.defaults.get_user_default("current_team", member_email) == team_id:
        frappe.defaults.clear_user_default("current_team", member_email)


@frappe.whitelist(methods=["POST"])
def set_member_role(team_id: str, member_email: str, role: str) -> None:
    """Promote or demote a member. Admins only."""
    team = require_admin(team_id)
    assert_role_value(role)
    team.set_member_role(member_email, role)


@frappe.whitelist(methods=["POST"])
def toggle_can_edit_team(team_id: str, member_email: str) -> None:
    """
    Flip a member between Admin and Member.

    Kept for the existing UI; set_member_role is the explicit version and is
    preferable because a toggle depends on state the caller cannot see.
    """
    team = require_admin(team_id)
    current = team.get_role(member_email)
    if current is None:
        frappe.throw(_("User is not a member of this team"), frappe.DoesNotExistError)

    team.set_member_role(
        member_email, ROLE_MEMBER if current == ROLE_ADMIN else ROLE_ADMIN
    )


# ---------------------------------------------------------------- invitations


@frappe.whitelist(methods=["POST"])
def invite_team_members(team_id: str, emails: list[str]) -> None:
    """Invite people by email. Admins only."""
    require_admin(team_id)

    if not emails:
        frappe.throw(_("Please provide at least one email address."), frappe.ValidationError)

    invite_by_email(
        emails=", ".join(emails),
        roles=["Forms Pro User"],
        redirect_to_path=(
            "/api/v2/method/forms_pro.api.team.add_member_to_team_via_invitation"
            f"?team_id={team_id}"
        ),
        app_name="forms_pro",
    )


@frappe.whitelist()
def add_member_to_team_via_invitation(team_id: str, invite_id: str | None = None) -> None:
    """
    Land here when an invitation is accepted.

    Reached by redirect (a GET), so this must not be POST-only. Authorisation
    comes from the invitation itself, not the caller's session.
    """
    invite_id = invite_id or frappe.form_dict.get("id")
    if not invite_id:
        frappe.throw(_("Invitation id is required"), frappe.PermissionError)

    invite: UserInvitation = frappe.get_doc("User Invitation", invite_id)

    if invite.status != "Accepted":
        frappe.throw(_("Invitation not accepted"), frappe.PermissionError)

    team: FPTeam = frappe.get_doc("FP Team", team_id)

    # The person who sent the invite must still be entitled to add members.
    if not team.is_admin(invite.invited_by):
        frappe.throw(
            _("Whoever sent this invitation can no longer add members to the team."),
            frappe.PermissionError,
        )

    if not frappe.db.exists("User", invite.email):
        frappe.throw(_("User not found"), frappe.DoesNotExistError)

    if not team.is_team_member(invite.email):
        team.add_to_team(invite.email, role=ROLE_MEMBER)
        team.save(ignore_permissions=True)
        set_current_team(team_id, invite.email)

    frappe.local.response["type"] = "redirect"
    frappe.local.response["location"] = "/forms"
