import os
import json

from datetime import date
import ckan.logic as logic
from ckan.plugins import toolkit

HERE = os.path.dirname(__file__)

all_helpers = {}

def helper(fn):
    """
    collect helper functions into ckanext.lhm.all_helpers dict
    """
    all_helpers[fn.__name__] = fn
    return fn

@helper
def user_info():

    user = {}
    try:
        full_name = toolkit.g.userobj.fullname
        email = toolkit.g.userobj.email
        
        user['full_name'] = full_name if full_name is not None else ''
        user['email'] = email if email is not None else ''
        user['all_info'] = f"{full_name}, {email}" if full_name is not None or email is not None else ''
    except AttributeError:
        user['full_name'] = user['email'] = user['all_info'] = None

    return user

@helper
def get_info_group(id):
    '''Returns the group information'''

    context: Context = {'ignore_auth': True,
                        'for_view': True}
    data_dict = {'id': id}

    try:
        out = logic.get_action('group_show')(context, data_dict)
    except logic.NotFound:
        return None
    return out

def get_init_data():
    # ckanext.grouphierarchy.init_data = example.json
    # make sure the .json file is inside grouphierarchy directory,
    # otherwise it won't work
    # if the .json file is not set in the .ini it would fall to the default one
    filepath = toolkit.config.get("ckanext.lhm.init_data", "schemas/init_group.json")
    if toolkit.h.is_url(filepath):
        url = filepath
        response = requests.get(url)

        if response.status_code == 200:
            if is_github_url(url):
                content = response.json()['payload']['blob']['rawBlob']
                data = json.loads(content)
            else:
                data = response.json()

    else:
        with open(os.path.join(HERE, filepath), encoding="utf-8") as f:
            data = json.load(f)

    return data

