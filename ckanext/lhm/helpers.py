import os
import json

from datetime import date
import ckan.logic as logic
from ckan.plugins import toolkit
from ckan.common import config, request
from ckan import model

from validate_email import validate_email

HERE = os.path.dirname(__file__)

all_helpers = {}

LHM_MAIN_CATEGORIES_ROOT = 'main-categories'
LHM_TOPICS_ROOT = 'topics'
LHM_DEPARTMENT_ROOT = 'department'

def helper(fn):
    """
    collect helper functions into ckanext.lhm.all_helpers dict
    """
    all_helpers[fn.__name__] = fn
    return fn

@helper
def lhm_validate_email(email):
    if validate_email(email):
        return email
    else:
        return ""

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

def _group_tree_section(id_):
    try:
        return toolkit.h.group_tree_section(
            id_=id_, type_='group', include_siblings=True)
    except Exception:
        return None


@helper
def lhm_group_tree_section(id_):
    return _group_tree_section(id_)


def _group_value(group, key):
    if isinstance(group, dict):
        return group.get(key)
    if isinstance(group, str) and key in ('id', 'name'):
        return group
    return getattr(group, key, None)


def _group_children(group):
    if isinstance(group, dict):
        return group.get('children', []) or []
    return getattr(group, 'children', []) or []


def _collect_group_ids(node):
    ids = set()
    if not node:
        return ids

    for child in _group_children(node):
        child_id = _group_value(child, 'id')
        child_name = _group_value(child, 'name')
        if child_id:
            ids.add(child_id)
        if child_name:
            ids.add(child_name)
        ids.update(_collect_group_ids(child))
    return ids


@helper
def lhm_department_root_name():
    return LHM_DEPARTMENT_ROOT


@helper
def lhm_department_tree():
    root = _group_tree_section(LHM_DEPARTMENT_ROOT)
    return _group_children(root) if root else []


@helper
def lhm_group_ids_for_root(root_name):
    return _collect_group_ids(_group_tree_section(root_name))


@helper
def lhm_groups_for_root(groups, root_name):
    ids = lhm_group_ids_for_root(root_name)
    selected = []
    for group in groups or []:
        group_id = _group_value(group, 'id')
        group_name = _group_value(group, 'name')
        if group_id in ids or group_name in ids:
            selected.append(group)
    return selected


@helper
def lhm_package_department(pkg_dict):
    groups = (
        pkg_dict.get('groups', [])
        if isinstance(pkg_dict, dict)
        else getattr(pkg_dict, 'groups', [])
    )

    if not groups:
        package_id = (
            pkg_dict.get('id') or pkg_dict.get('name')
            if isinstance(pkg_dict, dict)
            else getattr(pkg_dict, 'id', None) or getattr(pkg_dict, 'name', None)
        )
        if package_id:
            try:
                package = toolkit.get_action('package_show')(
                    {'ignore_auth': True}, {'id': package_id})
                groups = package.get('groups', [])
            except (logic.NotFound, logic.NotAuthorized):
                groups = []

    departments = lhm_groups_for_root(groups, LHM_DEPARTMENT_ROOT)
    return departments[0] if departments else None


@helper
def lhm_package_main_category(pkg_dict):
    main_categories = lhm_groups_for_root(
        pkg_dict.get('groups', []) if isinstance(pkg_dict, dict) else [],
        LHM_MAIN_CATEGORIES_ROOT)
    return main_categories[0] if main_categories else None


@helper
def lhm_package_topics(pkg_dict):
    return lhm_groups_for_root(
        pkg_dict.get('groups', []) if isinstance(pkg_dict, dict) else [],
        LHM_TOPICS_ROOT)


@helper
def lhm_department_url(group):
    name = _group_value(group, 'name') or group
    return toolkit.url_for('group.read', id=name)

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

@helper
def is_activity_user_admin(user_id):
    user = model.User.get(user_id)
    if user and user.sysadmin:
        return True
    return False

@helper
def usage_info():
    '''Return the value of the terms of use config setting.

    To enable showing the usage_info, add this line to the
    [app:main] section of your CKAN config file::
      lhm.usage_info = www.useage.com
    '''
    value = config.get('lhm.usage_info', None)
    return value


@helper
def contact_email():
    '''Return the value of the contact Email config setting.

    To enable showing the contact Email, add this line to the
    [app:main] section of your CKAN config file::
      lhm.contact_email = email_adress@something.com
    '''
    value = config.get('lhm.contact_email', None)
    return value

@helper
def github():
    '''Return the value of the github repo setting.

    To enable showing the github repo, add this line to the
    [app:main] section of your CKAN config file::
      lhm.github = https://github.com/ckan
    '''
    value = config.get('lhm.github', None)
    return value

@helper
def version_info():
    '''Return the value of the CKAN version config setting.

    To enable showing the contact Email, add this line to the
    [app:main] section of your CKAN config file::
      lhm.version_info = CKAN Lastest
    '''
    value = config.get('lhm.version_info', None)
    return value


@helper
def about_us():
    '''Return the value of the CKAN About Us config setting.

    To enable showing the about us info, add this line to the
    [app:main] section of your CKAN config file::
      lhm.about_us = lhm_about.html
    '''
    value = config.get('lhm.about_us', '/about')
    return value

@helper
def username_info():
    '''Return the value of the CKAN username info text config setting.

    To enable showing the username info text, add this line to the
    [app:main] section of your CKAN config file::
      lhm.username_info = username_info
    '''
    value = config.get('lhm.username_info', None)
    return value

@helper
def password_info():
    '''Return the value of the CKAN password info text config setting.

    To enable showing the password info text, add this line to the
    [app:main] section of your CKAN config file::
      lhm.password_info = password_info
    '''
    value = config.get('lhm.password_info', None)
    return value
