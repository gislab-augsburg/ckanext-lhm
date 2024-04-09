import ckan.plugins as plugins
from ckan.plugins import toolkit
import json


def copy_data_to_solr(data_dict):
    """
    Copies data from the CKAN DataStore to Solr before indexing.
    """
    # Get the data from the data_dict
    resources = data_dict['resources']
    
    if not resources:
        return

    for resource in resources:
        attribut = []
        wert = []
        bedeutung = []
        try:
            result = toolkit.get_action('datastore_search')(None, {'resource_id': resource['id']})

            records_lazy = result.get('records')
            records_str = str(records_lazy)
            # Find the index of '[' and ']'
            start_index = records_str.index('[')
            end_index = records_str.rindex(']')
            if start_index != -1 and end_index != -1:
                records_ = records_str[start_index:end_index+1]
            else:
                records_ = records_str
            print(records_)
            records = json.loads(records_)
            if records:
                for record in records:
                    attribut.append(record['ATTRIBUT'])
                    wert.append(record['WERT'])
                    bedeutung.append(record['BEDEUTUNG'])

        except (toolkit.ObjectNotFound, toolkit.NotAuthorized):
        # Continue even if no datastore record is found for the
        # current resource
            pass

    return attribut, wert, bedeutung

