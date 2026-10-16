"""Regression tests for automatic LHM root-group membership."""

import unittest
from unittest.mock import Mock, call, patch

from ckanext.lhm.logic import action


ROOTS = ("department", "main-categories", "topics")


class OrganizationMembershipTest(unittest.TestCase):
    def setUp(self):
        self.context = {"user": "organization-admin"}
        self.data = {"id": "organization", "username": "new-editor", "role": "editor"}
        self.membership = {"table_id": "user-id", "capacity": "editor"}
        self.original = Mock(return_value=self.membership)
        self.member_list = Mock(return_value=[])
        self.group_member_create = Mock()
        self.member_delete = Mock()
        self.group_show = Mock(side_effect=lambda context, data: {"id": data["id"]})
        self.has_role_patch = patch.object(
            action, "_has_editor_or_admin_organization", return_value=False
        )
        self.has_role = self.has_role_patch.start()
        self.addCleanup(self.has_role_patch.stop)
        self.actions = {
            "member_list": self.member_list,
            "group_member_create": self.group_member_create,
            "member_delete": self.member_delete,
            "group_show": self.group_show,
        }
        self.get_action_patch = patch.object(
            action.tk, "get_action", side_effect=self.actions.__getitem__
        )
        self.get_action = self.get_action_patch.start()
        self.addCleanup(self.get_action_patch.stop)

    def invoke(self):
        return action.organization_member_create(
            self.original, self.context, self.data
        )

    def test_editor_and_admin_gain_only_root_memberships(self):
        for role in ("editor", "admin"):
            with self.subTest(role=role):
                self.data["role"] = role
                self.membership["capacity"] = role
                self.group_member_create.reset_mock()
                self.assertIs(self.invoke(), self.membership)
                self.original.assert_called_with(self.context, self.data)
                self.assertEqual(self.group_member_create.call_args_list, [
                    call(
                        {"user": "organization-admin", "ignore_auth": True},
                        {"id": root, "username": "user-id", "role": "member"},
                    ) for root in ROOTS
                ])

    def test_member_role_does_not_add_groups(self):
        self.membership["capacity"] = "member"
        self.data["role"] = "member"
        self.assertIs(self.invoke(), self.membership)
        self.group_member_create.assert_not_called()

    def test_existing_roles_are_preserved(self):
        self.member_list.side_effect = [
            [("user-id", "user", "Member")],
            [("user-id", "user", "Admin")],
            [("user-id", "user", "Editor")],
        ]
        self.invoke()
        self.group_member_create.assert_not_called()

    def test_other_users_do_not_prevent_membership(self):
        self.member_list.return_value = [("other-user", "user", "Admin")]
        self.invoke()
        self.assertEqual(self.group_member_create.call_count, 3)

    def test_each_missing_root_is_skipped_independently(self):
        for missing_index in range(3):
            with self.subTest(missing=ROOTS[missing_index]):
                results = [[], [], []]
                results[missing_index] = action.logic.NotFound()
                self.member_list.side_effect = results
                self.group_member_create.reset_mock()
                self.invoke()
                self.assertEqual(
                    [args[0][1]["id"] for args in self.group_member_create.call_args_list],
                    [root for index, root in enumerate(ROOTS) if index != missing_index],
                )

    def test_all_missing_roots_are_harmless(self):
        self.member_list.side_effect = action.logic.NotFound()
        self.assertIs(self.invoke(), self.membership)
        self.group_member_create.assert_not_called()

    def test_group_removed_during_assignment_is_skipped(self):
        self.group_member_create.side_effect = [action.logic.NotFound(), None, None]
        self.assertIs(self.invoke(), self.membership)
        self.assertEqual(self.group_member_create.call_count, 3)

    def test_failed_organization_change_does_not_add_groups(self):
        self.original.side_effect = action.logic.NotAuthorized()
        with self.assertRaises(action.logic.NotAuthorized):
            self.invoke()
        self.get_action.assert_not_called()

    def test_caller_context_is_not_elevated_or_changed(self):
        self.context["schema"] = {"organization-only": []}
        before = dict(self.context)
        self.invoke()
        self.assertEqual(self.context, before)
        for args in self.member_list.call_args_list:
            self.assertEqual(args[0][0], {
                "user": "organization-admin", "ignore_auth": True,
            })
            self.assertEqual(args[0][1]["object_type"], "user")

    def test_repeated_assignment_does_not_rewrite_memberships(self):
        members = {root: [] for root in ROOTS}
        self.member_list.side_effect = lambda context, data: members[data["id"]]

        def add_member(context, data):
            members[data["id"]].append((data["username"], "user", "Member"))

        self.group_member_create.side_effect = add_member
        self.invoke()
        self.invoke()
        self.assertEqual(self.group_member_create.call_count, 3)


    def demote(self):
        self.membership["capacity"] = "member"
        self.data["role"] = "member"
        return self.invoke()

    def delete_membership(self, data=None):
        self.original.return_value = None
        with patch.object(action.model.User, "get", return_value=Mock(id="user-id")) as get_user:
            result = action.organization_member_delete(
                self.original, self.context, self.data if data is None else data
            )
        return result, get_user

    def assert_roots_removed(self):
        self.assertEqual(self.member_delete.call_args_list, [
            call(
                {"user": "organization-admin", "ignore_auth": True},
                {"id": root, "object": "user-id", "object_type": "user"},
            ) for root in ROOTS
        ])

    def test_demotion_removes_all_root_memberships_without_other_high_role(self):
        self.assertIs(self.demote(), self.membership)
        self.has_role.assert_called_once_with("user-id")
        self.assert_roots_removed()

    def test_demotion_preserves_roots_with_editor_or_admin_role_elsewhere(self):
        self.has_role.return_value = True
        self.demote()
        self.group_show.assert_not_called()
        self.member_delete.assert_not_called()

    def test_membership_removal_removes_roots_without_other_high_role(self):
        result, get_user = self.delete_membership()
        self.assertIsNone(result)
        get_user.assert_called_once_with("new-editor")
        self.assert_roots_removed()

    def test_membership_removal_preserves_roots_with_high_role_elsewhere(self):
        self.has_role.return_value = True
        self.delete_membership()
        self.member_delete.assert_not_called()

    def test_removal_supports_user_id_parameter(self):
        result, get_user = self.delete_membership({"id": "organization", "user_id": "user-id"})
        get_user.assert_called_once_with("user-id")
        self.assert_roots_removed()

    def test_failed_removal_never_runs_cleanup(self):
        self.original.side_effect = action.logic.NotAuthorized()
        with patch.object(action.model.User, "get") as get_user:
            with self.assertRaises(action.logic.NotAuthorized):
                action.organization_member_delete(self.original, self.context, self.data)
        get_user.assert_not_called()
        self.has_role.assert_not_called()
        self.get_action.assert_not_called()

    def test_demotion_checks_roles_after_successful_change(self):
        changed = []
        def change(context, data):
            changed.append(True)
            return self.membership
        def check(user_id):
            self.assertEqual(changed, [True])
            return False
        self.original.side_effect = change
        self.has_role.side_effect = check
        self.demote()
        self.assert_roots_removed()

    def test_missing_roots_do_not_interrupt_demotion_cleanup(self):
        self.group_show.side_effect = [action.logic.NotFound(), {"id": "main-categories"}, {"id": "topics"}]
        self.demote()
        self.assertEqual([args[0][1]["id"] for args in self.member_delete.call_args_list], ["main-categories", "topics"])

    def test_all_missing_roots_are_harmless_during_removal(self):
        self.group_show.side_effect = action.logic.NotFound()
        self.delete_membership()
        self.member_delete.assert_not_called()

    def test_root_removed_during_cleanup_does_not_interrupt_other_roots(self):
        self.member_delete.side_effect = [action.logic.NotFound(), None, None]
        self.demote()
        self.assert_roots_removed()

    def test_cleanup_preserves_caller_context(self):
        before = dict(self.context)
        self.delete_membership()
        self.assertEqual(self.context, before)

    def test_failed_demotion_never_runs_cleanup(self):
        self.original.side_effect = action.logic.NotAuthorized()
        with self.assertRaises(action.logic.NotAuthorized):
            self.demote()
        self.has_role.assert_not_called()
        self.get_action.assert_not_called()


class OrganizationRoleQueryTest(unittest.TestCase):
    def test_actual_membership_query_handles_presence_and_absence(self):
        for membership in (None, object()):
            with self.subTest(has_membership=membership is not None):
                with patch.object(action.model.Session, "query") as query:
                    query.return_value.join.return_value.filter.return_value.first.return_value = membership
                    self.assertEqual(
                        action._has_editor_or_admin_organization("user-id"),
                        membership is not None,
                    )
                    query.assert_called_once_with(action.model.Member)
                    self.assertEqual(len(query.return_value.join.return_value.filter.call_args[0]), 6)
