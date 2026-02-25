import os
import json
import click

import ckan.lib.navl.dictization_functions as dict_fns
import ckan.plugins.toolkit as toolkit
import ckan.model as model

from ckan.cli import error_shout

from ckanext.lhm.helpers import get_init_data


NotFound = toolkit.ObjectNotFound
NotAuthorized = toolkit.NotAuthorized
ValidationError = toolkit.ValidationError

HERE = os.path.dirname(__file__)
_site_url = toolkit.config.get('ckan.site_url')


@click.group("grouphierarchy", short_help="Grouphierarchy commands")
def grouphierarchy():
    pass


def create_org_or_group(group, is_org=False):
    user = toolkit.get_action('get_site_user')({'ignore_auth': True})
    context = {
            "model": model,
            "session": model.Session,
            "user": user['name'],
            #"return_id_only": True
        }
    data_dict = {
        "id": group['name']
    }
    list_grp_or_org = 'organization_list' if is_org else 'group_list'
    group_exist = toolkit.get_action(list_grp_or_org)(context, data_dict)

    if group['name'] in group_exist:
        delete_grp_or_org = 'organization_purge' if is_org else 'group_purge'
        data_dict = {
            "id": group['name']
        }
        toolkit.get_action(delete_grp_or_org)(context, data_dict)

    
    grp_or_org = 'organization_create' if is_org else 'group_create'
    if group.get('image_url'):
        group['image_url'] = _site_url + group.get('image_url')

    try:
        toolkit.get_action(grp_or_org)(context, group)
    except (NotFound, NotAuthorized) as e:
        error_shout(e)
        raise click.Abort()
    except dict_fns.DataError:
        error_shout('Integrity Error')
        raise click.Abort()
    except ValidationError as e:
        error_shout(e)
        raise click.Abort()


@grouphierarchy.command("init_data")
def init_data():

    data = get_init_data()

    for group in data.get('groups'):
        create_org_or_group(group)
    # for org in data.get('organizations'):
    #     create_org_or_group(org, is_org=True)

    click.secho(
        "Successfully created the initial Orgs/Groups",
        fg="green",
        bold=True
    )

def get_commands():
    return [grouphierarchy]
