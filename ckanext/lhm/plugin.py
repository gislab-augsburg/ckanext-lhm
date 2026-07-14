import json
from collections import OrderedDict
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
        # Get helpers
        existing_helpers = dict(helpers.all_helpers)
        # Add additional helper
        existing_helpers.update({
            'pycsw_enabled': lambda: toolkit.config.get('ckan.pycsw_enabled', 'false').lower() == 'true'
        })
        return existing_helpers


    def _group_has_parent(self, group, root_name, seen=None):
        seen = seen or set()
        if not group or group.id in seen:
            return False
        seen.add(group.id)

        if group.name == root_name:
            return True

        parents = model.Session.query(model.Group).join(
            model.Member, model.Member.group_id == model.Group.id
        ).filter(
            model.Member.table_name == 'group',
            model.Member.table_id == group.id,
            model.Member.state == 'active',
        ).all()

        return any(self._group_has_parent(parent, root_name, seen) for parent in parents)

    def _package_group_names_for_root(self, package_id, root_name):
        package = model.Package.get(package_id)
        if not package:
            return []

        names = []
        for group in package.get_groups(group_type='group'):
            if group.name != root_name and self._group_has_parent(group, root_name):
                names.append(group.name)
        return names


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

        data_dict['department'] = self._package_group_names_for_root(
            data_dict['id'], helpers.LHM_DEPARTMENT_ROOT)
        data_dict['main_category'] = self._package_group_names_for_root(
            data_dict['id'], helpers.LHM_MAIN_CATEGORIES_ROOT)
        data_dict['topic'] = self._package_group_names_for_root(
            data_dict['id'], helpers.LHM_TOPICS_ROOT)

        # get list of dicts from repeating subfield fields to prevent Solr errors
        usage_keywords = []
        usage_remarks = []
        for sub in data_dict.get('nutzungshinweise', []):
            usage_keywords.append(sub['stichwort'])
            usage_remarks.append(sub['hinweise'])

        refsystem_code = []
        refsystem_codespace = []
        refsystem_version = []
        for sub in data_dict.get('refsystem', []):
            if 'refsystem_code' in sub.keys():
                refsystem_code.append(sub['refsystem_code'])
            else:
                refsystem_code.append('')
            if 'refsystem_codespace' in sub.keys():
                refsystem_codespace.append(sub['refsystem_codespace'])
            else:
                refsystem_codespace.append('')
            if 'refsystem_version' in sub.keys():
                refsystem_version.append(sub['refsystem_version'])
            else:
                refsystem_version.append('')

        distrib_format_name = []
        distrib_format_version = []
        for sub in data_dict.get('distrib_format', []):
            if 'distrib_format_name' in sub.keys():
                distrib_format_name.append(sub['distrib_format_name'])
            else:
                distrib_format_name.append('')
            if 'distrib_format_version' in sub.keys():
                distrib_format_version.append(sub['distrib_format_version'])
            else:
                distrib_format_version.append('')

        # replace list of dicts with plain texts to prevent Solr errors
        data_dict['nutzungshinweise'] = '\n'.join(usage_keywords)
        data_dict['nutzungshinweise'] += '\n'.join(usage_remarks)

        data_dict['refsystem'] = '\n'.join(refsystem_code)
        data_dict['refsystem'] += '\n'.join(refsystem_codespace)
        data_dict['refsystem'] += '\n'.join(refsystem_version)

        data_dict['distrib_format'] = '\n'.join(distrib_format_name)
        data_dict['distrib_format'] += '\n'.join(distrib_format_version)

        return data_dict

    def before_map(self, map):
        return map

    def after_map(self, map):
        return map

    def before_dataset_search(self, search_params):
        if self._is_organization_dataset_search(search_params):
            query = search_params.get('q', '')
            include_children = 'include_children: "True"'
            if include_children not in query:
                search_params['q'] = (query + ' ' + include_children).strip()

        return HierarchyDisplay.before_dataset_search(self, search_params)

    before_search = before_dataset_search

    def _is_organization_dataset_search(self, search_params):
        if 'owner_org' not in search_params.get('fq', ''):
            return False

        try:
            fields = toolkit.g.fields
        except (AttributeError, RuntimeError):
            return False

        if not isinstance(fields, list):
            return False

        try:
            if toolkit.check_ckan_version("2.10"):
                controller = toolkit.get_endpoint()[0]
            else:
                controller = toolkit.g.controller
        except (TypeError, AttributeError, RuntimeError):
            return False

        return controller == 'organization'

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


    # IConfigurer
    def update_config(self, config):
        p.toolkit.add_template_directory(config, 'theme_templates')
        p.toolkit.add_public_directory(config, 'public')
        p.toolkit.add_resource('assets_theme', 'lhm_theme')



    def _lhm_facets(self, facets_dict):
        labels = OrderedDict([
            ('organization', 'Datenquellen'),
            ('department', 'Abteilungen'),
            ('main_category', 'Hauptkategorien'),
            ('topic', 'Themen'),
            ('tags', 'Schlagworte'),
            ('res_format', 'Formate'),
            ('open_data', 'Open Data'),
        ])
        skipped = ('groups', 'type', 'owner_org')
        facets = OrderedDict()

        for name, label in labels.items():
            if name in facets_dict:
                facets[name] = label

        for name, title in facets_dict.items():
            if name in facets or name in skipped:
                continue
            facets[name] = title

        return facets

    def dataset_facets(self, facets_dict, package_type):
        return self._lhm_facets(facets_dict)

    def group_facets(self, facets_dict, group_type, package_type):
        return self._lhm_facets(facets_dict)

    def organization_facets(self, facets_dict, organization_type, package_type):
        return self._lhm_facets(facets_dict)

    # IActions
    def get_actions(self):
        return {
            'user_create': action.user_create,
        }
