import ckan.plugins.toolkit as tk
import ckan.logic as logic
import ckan.model as model

""" ****Automatice generated Example*****
@tk.side_effect_free
def lhm_get_sum(context, data_dict):
    tk.check_access(
        "lhm_get_sum", context, data_dict)
    data, errors = tk.navl_validate(
        data_dict, schema.lhm_get_sum(), context)

    if errors:
        raise tk.ValidationError(errors)

    return {
        "left": data["left"],
        "right": data["right"],
        "sum": data["left"] + data["right"]
    }

def get_actions():
    return {
        'lhm_get_sum': lhm_get_sum,
    }
"""

@tk.chained_action
def organization_member_create(original_action, context, data_dict):
    """Give organization editors/admins membership of the LHM root groups."""
    membership = original_action(context, data_dict)
    if membership["capacity"] == "member":
        _remove_root_memberships_if_no_organization_role(context, membership["table_id"])
        return membership
    if membership["capacity"] not in ("editor", "admin"):
        return membership

    # The organization action has already authorized the role change. Only the
    # automatic root-group memberships bypass group administration permissions.
    group_context = {"user": context["user"], "ignore_auth": True}
    user_id = membership["table_id"]
    for group in ("department", "main-categories", "topics"):
        try:
            members = tk.get_action("member_list")(
                dict(group_context), {"id": group, "object_type": "user"}
            )
        except logic.NotFound:
            continue

        # Preserve all existing active roles, including editor and admin.
        if any(member[0] == user_id for member in members):
            continue

        try:
            tk.get_action("group_member_create")(
                dict(group_context),
                {"id": group, "username": user_id, "role": "member"},
            )
        except logic.NotFound:
            # The group may have been removed since member_list was called.
            continue

    return membership


@tk.chained_action
def organization_member_delete(original_action, context, data_dict):
    """Reconcile root memberships after an organization membership is removed."""
    result = original_action(context, data_dict)
    username = data_dict.get("username")
    if username is None:
        username = data_dict.get("user_id")
    user = model.User.get(username)
    if user is not None:
        _remove_root_memberships_if_no_organization_role(context, user.id)
    return result


def _has_editor_or_admin_organization(user_id):
    # Query actual active memberships: organization_list_for_user treats
    # sysadmins as admins of every organization even without a membership.
    return model.Session.query(model.Member).join(
        model.Group, model.Member.group_id == model.Group.id
    ).filter(
        model.Member.table_name == "user",
        model.Member.table_id == user_id,
        model.Member.state == "active",
        model.Member.capacity.in_(("editor", "admin")),
        model.Group.is_organization.is_(True),
        model.Group.state == "active",
    ).first() is not None


def _remove_root_memberships_if_no_organization_role(context, user_id):
    if _has_editor_or_admin_organization(user_id):
        return

    # Use member_delete directly: CKAN's group_member_delete does not pass
    # ignore_auth through to its nested member_delete action.
    group_context = {"user": context["user"], "ignore_auth": True}
    for name in ("department", "main-categories", "topics"):
        try:
            group = tk.get_action("group_show")(
                dict(group_context),
                {"id": name, "include_users": False, "include_dataset_count": False},
            )
            tk.get_action("member_delete")(
                dict(group_context),
                {"id": group["id"], "object": user_id, "object_type": "user"},
            )
        except logic.NotFound:
            # Missing roots (including a group removed during cleanup) are fine.
            continue
