import ckan.plugins as plugins
from ckan.plugins import toolkit
import json


def copy_data_to_solr(data_dict):
    """
    Copies data from the CKAN DataStore to Solr before indexing.
    """
    # Get the data from the data_dict
    resources = data_dict.get('resources', []) #data_dict['resources']

    
    attribut = []
    wert = []
    bedeutung = []
    if not resources:
        return attribut, wert, bedeutung

    else:
        for resource in resources:
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

                records = json.loads(records_)
                if records:
                    for record in records:
                        attribut.append(record.get('ATTRIBUT', None))
                        wert.append(record.get('WERT', None))
                        bedeutung.append(record.get('BEDEUTUNG', None))

            except (toolkit.ObjectNotFound, toolkit.NotAuthorized):
            # Continue even if no datastore record is found for the
            # current resource
                pass
        return attribut, wert, bedeutung



def lhm_get_sum():
    not_empty = toolkit.get_validator("not_empty")
    convert_int = toolkit.get_validator("convert_int")

    return {
        "left": [not_empty, convert_int],
        "right": [not_empty, convert_int]
    }


