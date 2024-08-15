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
      lhm.password_info = password_info
    '''
    value = config.get('lhm.password_info', None)
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