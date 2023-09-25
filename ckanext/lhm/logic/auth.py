import ckan.plugins.toolkit as tk


@tk.auth_allow_anonymous_access
def lhm_get_sum(context, data_dict):
    return {"success": True}


def get_auth_functions():
    return {
        "lhm_get_sum": lhm_get_sum,
    }
