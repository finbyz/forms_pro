"""Public surface of the team API.

Frappe resolves `forms_pro.api.team.<name>` as an attribute of this package, so
anything the client calls has to be re-exported here. `add_team_member` and
`get_users_for_team_addition` were missing, which made "Add member" and its user
picker fail with AttributeError.
"""

from .endpoints import (
    add_member_to_team_via_invitation,
    add_team_member,
    create_team,
    delete_team,
    get_team_for_manage,
    get_team_forms,
    get_team_members,
    get_users_for_team_addition,
    invite_team_members,
    leave_team,
    remove_member_from_team,
    save,
    set_member_role,
    switch_team,
    toggle_can_edit_team,
)

__all__ = [
    "add_member_to_team_via_invitation",
    "add_team_member",
    "create_team",
    "delete_team",
    "get_team_for_manage",
    "get_team_forms",
    "get_team_members",
    "get_users_for_team_addition",
    "invite_team_members",
    "leave_team",
    "remove_member_from_team",
    "save",
    "set_member_role",
    "switch_team",
    "toggle_can_edit_team",
]
