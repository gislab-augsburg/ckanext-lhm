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


LHM_ORG_KIND_EXTRA = 'lhm_org_kind'
LHM_ORG_KIND = 'lhm_org'
LHM_OWNER_ORG_KIND = 'owner_org'
_lhm_organization_cache = {}


def _lhm_org_display_name(organization):
    if not organization:
        return None
    return (
        organization.get('display_name')
        or organization.get('title')
        or organization.get('name')
        or organization.get('id')
    )


def _lhm_org_extra(organization, key):
    if not organization:
        return None

    if organization.get(key):
        return organization.get(key)

    extras = organization.get('extras')
    if isinstance(extras, dict):
        return extras.get(key)

    if isinstance(extras, list):
        for extra in extras:
            if extra.get('key') == key:
                return extra.get('value')

    return None


def _lhm_org_kind(organization, resolve_missing=False):
    org_kind = _lhm_org_extra(organization, LHM_ORG_KIND_EXTRA)
    if org_kind or not organization:
        return org_kind

    # Bulk list helpers must not call organization_show for every untyped
    # organization. With many legacy organizations this turns page rendering
    # into an expensive N+1 action loop and can hit gateway timeouts.
    if not resolve_missing:
        return None

    organization_id = organization.get('id') or organization.get('name')
    if not organization_id:
        return None

    full_organization = _lhm_organization_show(organization_id)
    if not full_organization:
        return None

    return _lhm_org_extra(full_organization, LHM_ORG_KIND_EXTRA)


def _lhm_organization_list():
    try:
        return toolkit.get_action('organization_list')(
            {'ignore_auth': True},
            {'all_fields': True, 'include_extras': True}
        )
    except Exception:
        return []


def _lhm_filter_orgs(organizations, kind):
    return [
        organization for organization in organizations or []
        if _lhm_org_kind(organization, resolve_missing=False) == kind
    ]


def _lhm_sort_orgs(organizations):
    return sorted(
        organizations,
        key=lambda organization: (_lhm_org_display_name(organization) or '').lower()
    )


def _lhm_matches_query(organization, query):
    if not query:
        return True

    query = query.lower()
    values = [
        organization.get('name'),
        organization.get('title'),
        organization.get('display_name'),
        organization.get('description'),
    ]
    return any(query in value.lower() for value in values if value)


def _lhm_config_list(key):
    value = config.get(key, '')
    if isinstance(value, (list, tuple)):
        return [str(item).strip() for item in value if item]

    if not value:
        return []

    value = str(value).strip()
    if value.startswith('['):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return [str(item).strip() for item in parsed if item]
        except ValueError:
            pass

    value = value.replace(',', ' ')
    return [item for item in value.split() if item]


def _lhm_organization_show(organization_id):
    if not organization_id:
        return None

    cache_key = str(organization_id)
    if cache_key in _lhm_organization_cache:
        return _lhm_organization_cache[cache_key]

    try:
        organization = toolkit.get_action('organization_show')(
            {'ignore_auth': True},
            {
                'id': organization_id,
                'include_datasets': False,
                'include_extras': True,
                'include_users': False,
                'include_groups': False,
                'include_tags': False,
                'include_followers': False,
            }
        )
    except Exception:
        organization = None

    _lhm_organization_cache[cache_key] = organization
    if organization:
        for key in (organization.get('id'), organization.get('name')):
            if key:
                _lhm_organization_cache[str(key)] = organization
    return organization


@helper
def lhm_featured_owner_orgs():
    organizations = []
    for organization_id in _lhm_config_list('ckan.featured_orgs'):
        organization = _lhm_organization_show(organization_id)
        if organization and lhm_is_data_source(organization):
            organizations.append(organization)
    return organizations


@helper
def lhm_org_options(organizations=None):
    """Return selectable LHM organizations for the lhm_org metadata field."""
    organizations = organizations or _lhm_organization_list()
    organizations = _lhm_filter_orgs(organizations, LHM_ORG_KIND)

    options = []
    for organization in _lhm_sort_orgs(organizations):
        value = organization.get('id') or organization.get('name')
        label = _lhm_org_display_name(organization)
        if value and label:
            options.append({'value': value, 'label': label})

    return options


@helper
def lhm_data_source_options(organizations=None):
    organizations = organizations or _lhm_organization_list()
    return _lhm_sort_orgs(_lhm_filter_orgs(organizations, LHM_OWNER_ORG_KIND))


@helper
def lhm_filter_lhm_orgs(organizations):
    return _lhm_sort_orgs(_lhm_filter_orgs(organizations, LHM_ORG_KIND))


@helper
def lhm_lhm_orgs(q=None, organizations=None):
    organizations = organizations or _lhm_organization_list()
    organizations = _lhm_filter_orgs(organizations, LHM_ORG_KIND)
    organizations = [
        organization for organization in organizations
        if _lhm_matches_query(organization, q)
    ]
    return _lhm_sort_orgs(organizations)


@helper
def lhm_org_kind(organization):
    return _lhm_org_kind(organization)


@helper
def lhm_members_route(group_type='organization'):
    for route_name in (group_type + '.manage_members', group_type + '.members'):
        try:
            toolkit.url_for(route_name, id='__lhm_route_probe__')
            return route_name
        except Exception:
            continue
    return group_type + '.members'


@helper
def lhm_is_lhm_org(organization):
    return _lhm_org_kind(organization, resolve_missing=True) == LHM_ORG_KIND


@helper
def lhm_is_data_source(organization):
    return _lhm_org_kind(organization, resolve_missing=True) == LHM_OWNER_ORG_KIND


@helper
def lhm_org_label(value):
    organization = lhm_org(value)
    if organization:
        return _lhm_org_display_name(organization)
    return value if value else None


@helper
def lhm_org(value_or_pkg):
    if not value_or_pkg:
        return None

    value = value_or_pkg
    if isinstance(value_or_pkg, dict):
        value = value_or_pkg.get('lhm_org')

    if not value:
        return None

    try:
        return _lhm_organization_show(value)
    except Exception:
        return None


@helper
def lhm_owner_org_label(pkg_dict):
    organization = pkg_dict.get('organization') if pkg_dict else None
    label = _lhm_org_display_name(organization)
    if label:
        return label

    owner_org = pkg_dict.get('owner_org') if pkg_dict else None
    if owner_org:
        return lhm_org_label(owner_org)

    return None

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
