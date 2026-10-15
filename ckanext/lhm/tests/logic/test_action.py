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
        self.actions = {
            "member_list": self.member_list,
            "group_member_create": self.group_member_create,
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
        self.get_action.assert_not_called()

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
