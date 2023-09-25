from datetime import date

from ckan.plugins import toolkit


all_helpers = {}

def helper(fn):
    """
    collect helper functions into ckanext.scheming.all_helpers dict
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

