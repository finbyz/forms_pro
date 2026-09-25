# Copyright (c) 2025, harsh@buildwithhussain.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.share import add_docshare
from frappe.share import remove as remove_docshare
from pydantic import BaseModel, EmailStr

from forms_pro.api.user import get_user
from forms_pro.utils.teams import set_current_team


ROLE_ADMIN = "Admin"
ROLE_MEMBER = "Member"
TEAM_ROLES = (ROLE_ADMIN, ROLE_MEMBER)


class GetTeamMembersResponse(BaseModel):
    full_name: str
    user_image: str | None
    # A Frappe user id, which is usually an email but not always:
    # "Administrator" and "Guest" are valid users and are not addresses.
    email: str
    role: str
    can_edit_team: bool
    is_owner: bool


class FPTeam(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        from forms_pro.forms_pro.doctype.fp_team_member.fp_team_member import FPTeamMember

        logo: DF.AttachImage | None
        team_name: DF.Data
        users: DF.TableMultiSelect[FPTeamMember]
    # end: auto-generated types

    @property
    def team_members(self) -> list[GetTeamMembersResponse]:
        """The team roster, newest-safe: a deleted user must not break the page."""
        members = []

        for member in self.users or []:
            try:
                _user = get_user(member.user)
            except Exception:
                _user = None
            if not _user:
                # The user row is gone (get_user returns None rather than
                # raising); show the id instead of 500-ing the whole page.
                _user = {"full_name": member.user, "user_image": None}
            else:
                _user = dict(_user)

            role = self.effective_role(member.user, member.get("role"))
            _user["email"] = member.user
            _user["role"] = role
            _user["can_edit_team"] = role == ROLE_ADMIN
            _user["is_owner"] = self.owner == member.user
            members.append(GetTeamMembersResponse.model_validate(_user).model_dump())

        return members

    def effective_role(self, user: str, stored_role: str | None = None) -> str:
        """The owner is always an Admin, whatever the row says."""
        if user == self.owner:
            return ROLE_ADMIN
        return stored_role if stored_role in TEAM_ROLES else ROLE_MEMBER

    def get_member(self, user: str):
        for member in self.users or []:
            if member.user == user:
                return member
        return None

    def is_team_member(self, user: str) -> bool:
        if user == self.owner:
            return True
        return self.get_member(user) is not None

    def get_role(self, user: str) -> str | None:
        if user == self.owner:
            return ROLE_ADMIN
        member = self.get_member(user)
        if not member:
            return None
        return self.effective_role(user, member.get("role"))

    def is_admin(self, user: str) -> bool:
        if user == self.owner:
            return True
        return self.get_role(user) == ROLE_ADMIN

    def after_insert(self) -> None:
        self.add_to_team(self.owner, role=ROLE_ADMIN)
        set_current_team(self.name, self.owner)
        self.save()

    def add_to_team(self, user: str, role: str = ROLE_MEMBER) -> None:
        """Add a user to the team with the given role."""
        if user == "Guest":
            return

        # Check for an actual roster row, not `is_team_member`: that reports
        # *effective* membership, under which the owner always counts, so using
        # it here meant after_insert() could never give the owner their row and
        # every single team creation threw DuplicateEntryError.
        if self.get_member(user) is not None:
            frappe.throw(
                frappe._("User is already a member of the team"),
                frappe.DuplicateEntryError,
            )

        if role not in TEAM_ROLES:
            role = ROLE_MEMBER

        self.append("users", {"user": user, "role": role})
        self._sync_share(user, role)

    def set_member_role(self, user: str, role: str) -> None:
        """Promote or demote a member. The owner cannot be demoted."""
        if role not in TEAM_ROLES:
            frappe.throw(frappe._("Unknown team role: {0}").format(role), frappe.ValidationError)

        if user == self.owner:
            frappe.throw(
                frappe._("The team owner is always an admin."),
                frappe.ValidationError,
            )

        member = self.get_member(user)
        if not member:
            frappe.throw(frappe._("User is not a member of this team"), frappe.DoesNotExistError)

        member.role = role
        self.save(ignore_permissions=True)
        self._sync_share(user, role)

    def _sync_share(self, user: str, role: str) -> None:
        """
        Every member can read the team; only admins can write or re-share it.

        Membership — not the DocShare — is what the API authorises against, but
        keeping the share in step means desk access matches the app.
        """
        is_admin = role == ROLE_ADMIN
        add_docshare(
            self.doctype,
            self.name,
            user,
            read=1,
            write=1 if is_admin else 0,
            share=1 if is_admin else 0,
            flags={"ignore_share_permission": True},
        )

    def remove_from_team(self, user: str) -> None:
        """Remove a member. The owner stays."""
        if user == self.owner:
            frappe.throw(
                frappe._("Cannot remove the owner from the team"),
                frappe.ValidationError,
            )

        self.users = [member for member in self.users if member.user != user]
        self.save(ignore_permissions=True)
        remove_docshare(
            doctype="FP Team",
            name=self.name,
            user=user,
            flags={"ignore_permissions": True},
        )
