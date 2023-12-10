import ckan.plugins.toolkit as tk
import ckan.logic as logic
import ckanext.lhm.logic.schema as schema

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

def user_create(context, data_dict):
    group_list = tk.get_action("group_list")({}, {})
    site_user = tk.get_action("get_site_user")({"ignore_auth": True}, {})
    user = logic.action.create.user_create(context, data_dict)

    role = tk.config.get("ckan.lhm.group_role", "member")
    context["user"] = site_user.get("name")

    for group in group_list:
        try:
            tk.get_action("group_show")(
                context,
                {
                    "id": group,
                },
            )
        except logic.NotFound:
            return user

        tk.get_action("group_member_create")(
            context,
            {
                "id": group,
                "username": user["name"],
                "role": role,
            },
        )

    return user


