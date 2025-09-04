import json
import ckan.model as model
from ckan.lib import search
import ckan.plugins as p
import ckan.plugins.toolkit as toolkit
from ckan.plugins.interfaces import IConfigurer, IDatasetForm
from ckan.lib.plugins import DefaultTranslation
import ckanext.lhm.cli as cli
import ckanext.lhm.views as views

from ckanext.hierarchy.plugin import HierarchyDisplay

# import ckanext.lhm.cli as cli
import ckanext.lhm.helpers as helpers
# import ckanext.lhm.views as views
from ckanext.lhm.logic import action, schema
#     (action, auth, validators
# )

#from ckanext.datastore.backend.postgres import _cache_types
from sqlalchemy import create_engine

# This function extends the data types in postgresql.
# This is required for Data Dictionary and is an extension to the function _cache_types in Datastor.backend.postgres.py
def _data_dict_type():
    eng = toolkit.config['ckan.datastore.write_url']
    _pg_types = {}
    _type_names = set()
    engine = create_engine(eng)
    connection = engine.connect()
    if not _pg_types:
        results = connection.execute(
            'SELECT oid, typname FROM pg_type;'
        )
        for result in results:
            _pg_types[result[0]] = result[1]
            _type_names.add(result[1])

    if 'number_' not in _type_names:
        with engine.begin() as write_connection:
            write_connection.execute(
                'CREATE TYPE "number_" AS (number text)')
            # Add 'number' to _pg_types dictionary with a custom OID
            _pg_types[9000] = 'number_'  # You can use any unique OID here
            _type_names.add('number_')
    if 'sdo_geometry' not in _type_names:
        with engine.begin() as write_connection:
            write_connection.execute(
                'CREATE TYPE "sdo_geometry" AS (sdo_geometry text)')
            # Add 'sdo_geometry' to _pg_types dictionary with a custom OID
            _pg_types[6001] = 'sdo_geometry'  # You can use any unique OID here
            _type_names.add('sdo_geometry')
    if 'nvarchar2' not in _type_names:
        with engine.begin() as write_connection:
            write_connection.execute(
                'CREATE TYPE "nvarchar2" AS (nvarchar2 text)')
            # Add 'nvarchar2' to _pg_types dictionary with a custom OID
            _pg_types[6002] = 'nvarchar2'  # You can use any unique OID here
            _type_names.add('nvarchar2')
    # if 'float' not in _type_names:
    #     with engine.begin() as write_connection:
    #         write_connection.execute(
    #             'CREATE TYPE "float" AS (float text)')
    #         # Add 'float' to _pg_types dictionary with a custom OID
    #         _pg_types[6003] = 'float'  # You can use any unique OID here
    #         _type_names.add('float')
    if 'blob' not in _type_names:
        with engine.begin() as write_connection:
            write_connection.execute(
                'CREATE TYPE "blob" AS (blob text)')
            # Add 'blob' to _pg_types dictionary with a custom OID
            _pg_types[6004] = 'blob'  # You can use any unique OID here
            _type_names.add('blob')
_data_dict_type()


class LHMCatalogPlugin(p.SingletonPlugin, DefaultTranslation):
    p.implements(p.IConfigurer, inherit=True)
    # p.implements(p.IDatasetForm, inherit=True)
    # p.implements(p.IAuthFunctions)
    # p.implements(p.IActions)
    p.implements(p.IClick)
    p.implements(p.ITranslation, inherit=True)
    p.implements(p.ITemplateHelpers, inherit=True)
    p.implements(p.IPackageController, inherit=True)
    p.implements(p.IBlueprint, inherit=True)
    # p.implements(p.IValidators)
          
    def i18n_domain(self):
        return 'ckanext-lhm'

    # IConfigurer

    def update_config(self, config):
        toolkit.add_template_directory(config, 'templates')
        toolkit.add_public_directory(config, 'public')
        toolkit.add_resource("assets", "ckanext-lhm")


        config['scheming.presets'] = """
        ckanext.scheming:presets.json
        ckanext.composite:presets.json
        ckanext.lhm:schemas/presets_lhm.yaml
        """ + (
                "ckanext.validation:presets.json" if "validation" in config['ckan.plugins'] else
                "ckanext.lhm:schemas/validation_placeholder_presets.yaml"
        )

        # config['scheming.dataset_schemas'] = """
        # ckanext.lhm:schemas/lhm_dataset.yaml
        # """

    # ITemplateHelpers
    def get_helpers(self):
        return dict(helpers.all_helpers)
        # retunr dict((h, getattr(helpers, h)) for h in [
        #     'user_info',#: helpers.user_info
        # ])

    def before_index(self, data_dict):

        data_dict_scheming = data_dict['validated_data_dict']
        validated_data_dict = json.loads(data_dict_scheming)

        if validated_data_dict:
            # To index the datastore values into the solr
            # Focus is only on the Table Katalogwerte from GDP metadata
            attribut, wert, bedeutung = schema.copy_data_to_solr(validated_data_dict)
        else:
            attribut, wert, bedeutung = [], [], []

        data_dict['text'] = attribut #'\n'.join(attribut)
        data_dict['text'] += wert #'\n'.join(wert)
        data_dict['text'] += bedeutung #'\n'.join(bedeutung)

        usage_keywords = []
        usage_remarks = []
        for sub in data_dict.get('nutzungshinweise', []):
            usage_keywords.append(sub['stichwort'])
            usage_remarks.append(sub['hinweise'])

        # replace list of dicts with plain texts to prevent Solr errors
        data_dict['nutzungshinweise'] = '\n'.join(usage_keywords)
        data_dict['nutzungshinweise'] += '\n'.join(usage_remarks)

        return data_dict

    def before_map(self, map):
        return map

    def after_map(self, map):
        return map

    def before_search(self, search_params):
        # Call the original method to retain its functionality
        search_params = HierarchyDisplay.before_dataset_search('', search_params)

        # Add your additional logic here
        if 'owner_org' in search_params.get('fq', ''):
            query = search_params.get('q', '')
            query += ' include_children: "True"'
            search_params['q'] = query.strip()

        return search_params

    def is_fallback(self):
        return False

    # IActions

    def get_actions(self):
        return action.get_actions()

    # IBlueprint

    def get_blueprint(self):
        return views.get_blueprints()

    # IClick

    def get_commands(self):
        return cli.get_commands() 

    # IAuthFunctions

    # def get_auth_functions(self):
    #     return auth.get_auth_functions()

    # IValidators

    # def get_validators(self):
    #     return validators.get_validators()

    

    # def form_to_db_schema(self):
    #     schema = SchemingDatasets.form_to_db_schema()
    #     # Merge your new schema with the existing schema
    #     schema.update({
    #         'my_schema': {'some_field': ['ckanext.scheming:field_text']}
    #     })
    #     return schema


class LHMThemePlugin(p.SingletonPlugin, DefaultTranslation):
    '''Theme plugin for LHM UDP Catalog.'''

    # Declare the iterfaces this class implements
    #p.implements(p.IBlueprint)
    p.implements(p.IConfigurer)
    p.implements(p.IFacets, inherit=True)
    p.implements(p.IActions)
    #p.implements(p.ITemplateHelpers)

    if toolkit.check_ckan_version("2.9"):
        # IConfigurer
        def update_config(self, config):
            p.toolkit.add_template_directory(config, 'theme_templates_2.9.9')
            p.toolkit.add_public_directory(config, 'public')
            p.toolkit.add_resource('assets_theme_2.9.9', 'lhm_theme')

    elif toolkit.check_ckan_version("2.10"):
        # IConfigurer
        def update_config(self, config):
            p.toolkit.add_template_directory(config, 'theme_templates')
            p.toolkit.add_public_directory(config, 'public')
            p.toolkit.add_resource('assets_theme', 'lhm_theme')

    elif toolkit.check_ckan_version("2.11"):
        print('MB_debug: theme_templates, assets for ckan 2.11')
        # IConfigurer
        def update_config(self, config):
            p.toolkit.add_template_directory(config, 'theme_templates_2.9.9')
            p.toolkit.add_public_directory(config, 'public')
            p.toolkit.add_resource('assets_theme_2.9.9', 'lhm_theme')


    # IActions
    def get_actions(self):
        return {
            'user_create': action.user_create,
        }


from ckan.plugins import SingletonPlugin
from flask import template_rendered, current_app
import os

class LHMTemplateWrapper(SingletonPlugin):
    """Automatically wrap all CKAN core and ckanext-* templates in HTML comments."""

    def __init__(self):
        template_rendered.connect(self.wrap_template, current_app)

    def wrap_template(self, sender, template, context, **extra):
        # Only wrap if debug_templates is enabled in ckan.ini
        debug_enabled = getattr(sender.config, 'ckan.debug_templates', False)
        if not debug_enabled:
            return

        template_name = getattr(template, 'name', None)
        if not template_name:
            return

        # Wrap core templates (package/home) or any template from ckanext-* directories
        if template_name.startswith('package/') \
           or template_name.startswith('home/') \
           or self.is_ckanext_template(template_name):
            original_render = template.render

            def wrapped_render(*args, **kwargs):
                return (
                    f"<!-- START template: {template_name} -->\n"
                    + original_render(*args, **kwargs)
                    + f"\n<!-- END template: {template_name} -->"
                )

            template.render = wrapped_render

    def is_ckanext_template(self, template_name):
        """
        Detect if template belongs to any ckanext-* directory.
        Looks at absolute template path.
        """
        try:
            template_path = getattr(template, 'filename', None)
            if template_path and '/ckanext-' in template_path:
                return True
        except Exception:
            return False
        return False
