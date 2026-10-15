import ckan.plugins.toolkit as tk
import ckan.logic as logic

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
