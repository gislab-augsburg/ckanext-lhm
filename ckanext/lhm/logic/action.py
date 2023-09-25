import ckan.plugins.toolkit as tk
import ckanext.lhm.logic.schema as schema


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
