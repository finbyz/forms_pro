from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch

from forms_pro.overrides.roles import handle_forms_pro_role_change
from forms_pro.roles import FORMS_PRO_ROLE


class TestUserRoleHook(TestCase):
    def make_user(self, previous_roles, current_roles):
        user = Mock(name="user_document")
        user.name = "role-hook@example.com"
        user.get_doc_before_save.return_value = SimpleNamespace(
            get=lambda field: [SimpleNamespace(role=role) for role in previous_roles]
        )
        user.get.return_value = [SimpleNamespace(role=role) for role in current_roles]
        user.has_value_changed.return_value = previous_roles != current_roles
        user.on_update.side_effect = AssertionError("The hook must not rerun User.on_update")
        return user

    def test_profile_edit_does_not_reload_user_or_rerun_controller(self):
        user = self.make_user([], [])
        with patch("forms_pro.overrides.roles.frappe.get_doc") as reload_user:
            handle_forms_pro_role_change(user, "on_update")
        reload_user.assert_not_called()
        user.on_update.assert_not_called()

    def test_existing_role_does_not_create_team_on_profile_edit(self):
        user = self.make_user([FORMS_PRO_ROLE], [FORMS_PRO_ROLE])
        # Child-row objects can differ even when the assigned role is unchanged.
        user.has_value_changed.return_value = True
        with patch("forms_pro.overrides.roles.create_default_team_for_user") as create_team:
            handle_forms_pro_role_change(user, "on_update")
        create_team.assert_not_called()
        user.on_update.assert_not_called()

    def test_new_role_still_creates_default_team(self):
        user = self.make_user([], [FORMS_PRO_ROLE])
        with (
            patch("forms_pro.overrides.roles.get_user_teams", return_value=[]),
            patch("forms_pro.overrides.roles.frappe.db", new=Mock()) as database,
            patch("forms_pro.overrides.roles.create_default_team_for_user") as create_team,
        ):
            database.exists.return_value = False
            handle_forms_pro_role_change(user, "on_update")
        create_team.assert_called_once_with(user)
        user.on_update.assert_not_called()
