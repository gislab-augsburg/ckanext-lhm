"""Compatibility entry point for the CKAN pod's download button.

The implementation is shared with the external harvester in get_data.py.
"""

try:
    from . import get_data as shared
except ImportError:
    import get_data as shared


def packages_to_files(packages, limit, wdir, excel_template):
    return shared.packages_to_files(packages, limit, wdir, excel_template,
                                    backend="internal")


def ckan_action(action_name, data_dict):
    import ckan.plugins.toolkit as tk
    from ckan.common import json as ckan_json
    try:
        from flask import g
        user = getattr(g, "user", None)
    except RuntimeError:
        user = None
    result = tk.get_action(action_name)({"user": user}, data_dict)
    return ckan_json.loads(ckan_json.dumps(result))
