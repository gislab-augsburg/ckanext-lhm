from flask import Blueprint, send_file
import json
import subprocess
import os
from openpyxl import load_workbook
from openpyxl.styles import Alignment
from ckanext.lhm.get_data import packages_to_files
from pkg_resources import resource_filename
from ckan.logic import get_action
from ckan import model
from ckan.common import g
import ckan.plugins.toolkit as toolkit
from ckanext.lhm.gp_to_iso1939 import convert_metadata_dict
import shutil
import requests

# Create routes
lhm_view = Blueprint('lhm_view', __name__)

# Get package type
def get_package_type(dataset_id):
    context = {
        'model': model,
        'session': model.Session,
        'user': g.user,
        'auth_user_obj': g.userobj,
    }
    # fetch the package and read its type
    pkg_dict = get_action('package_show')(context, {'id': dataset_id})
    p_type = pkg_dict.get('type')
    return p_type

# Define variables, Create working dir
def get_export_vars():
    from ckan.common import config
    storage = config.get('ckan.storage_path')
    wdir = storage + '/export'
    if os.path.exists(wdir) == False:
        os.mkdir(wdir)
    return wdir

# Excel to PDF Conversion
def convert_xlsx_to_pdf(input_path, output_dir, package):
    cmd = [
        "libreoffice",
        "--headless",
        "--convert-to", "ods",
        input_path,
        "--outdir", output_dir
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, env={"HOME": "/var/lib/ckan/export"})
        print("LibreOffice output:", result.stdout)
        print("LibreOffice errors:", result.stderr)
    except subprocess.CalledProcessError as e:
        print("Fehler bei der Konvertierung:", e.stderr)

    output_ods =output_dir + '/' + package + '.ods'

    cmd = [
        "libreoffice",
        "--headless",
        "--convert-to", "pdf",
        output_ods,
        "--outdir", output_dir
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, env={"HOME": "/var/lib/ckan/export"})
        print("LibreOffice output:", result.stdout)
        print("LibreOffice errors:", result.stderr)
        return True
    except subprocess.CalledProcessError as e:
        print("Fehler bei der Konvertierung:", e.stderr)
        return False


# Generate package pdf for download
@lhm_view.route("/lhm_view/pdf/<dataset_name>")
def generate_pdf(dataset_name):

    # Get vars
    vars = get_export_vars()
    wdir = vars
    p_type = get_package_type(dataset_name)
    if p_type == 'geodatenpool':
        excel_template = resource_filename('ckanext.lhm', 'schemas/template_gdp.xlsx')
    elif p_type == 'mobidam':
        excel_template = resource_filename('ckanext.lhm', 'schemas/template_mobidam.xlsx')
    elif p_type == 'plan-db':
        excel_template = resource_filename('ckanext.lhm', 'schemas/template_plandb.xlsx')
    else:
        excel_template = resource_filename('ckanext.lhm', 'schemas/template_gdp.xlsx')

    # Create pdf directory
    if os.path.exists(f'{wdir}/pdf') == False:
        os.mkdir(f'{wdir}/pdf')

    package = dataset_name
    packages_to_files(package, 1, wdir, excel_template)

    # Define path to excel
    file_path = wdir + '/excel/' + package + '.xlsx'

    # Add headers
    wb = load_workbook(file_path)
    ws_0 = wb["Metadaten"]
    ws_1 = wb["Datenverzeichnis"]
    ws_2 = wb["Katalogwerte"]
    ws_3 = wb["Dienste und Dokumente"]
    ws_0.oddHeader.center.text = "Metadaten"
    ws_1.oddHeader.center.text = "Datenverzeichnis"
    ws_2.oddHeader.center.text = "Katalogwerte"
    ws_3.oddHeader.center.text = "Dienste und Dokumente"

    # Remove infotext long version 'LHM-Extern Nutzungsoptionen' for pdf
    if p_type == 'geodatenpool':
        coords = 'A37'
    elif p_type == 'mobidam':
        coords = 'A35'
    elif p_type == 'plan-db':
        coords = 'A40'
    else:
        coords = 'A37'
    cell = ws_0[coords]
    cell.value = ''

    # Add text wrap and save excel file
    for row in ws_0:
        for cell in row:
            cell.alignment = Alignment(wrapText=True,vertical='top')
    for row in ws_1:
        for cell in row:
            cell.alignment = Alignment(wrapText=True,vertical='top')
    for row in ws_2:
        for cell in row:
            cell.alignment = Alignment(wrapText=True,vertical='top')
    for row in ws_3:
        for cell in row:
            cell.alignment = Alignment(wrapText=True,vertical='top')
    wb.save(file_path)

    # Convert to pdf
    input_file = file_path
    output_dir = wdir + '/pdf'
    convert_xlsx_to_pdf(input_file, output_dir, package)
    output_pdf = wdir + '/pdf/' + package + '.pdf'

    # Download pdf
    return send_file(
        output_pdf,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=package + '.pdf'
    )

# Generate package excel for download
@lhm_view.route("/lhm_view/excel/<dataset_name>")
def generate_xlsx(dataset_name):

    # Get vars
    vars = get_export_vars()
    wdir = vars
    p_type = get_package_type(dataset_name)
    if p_type == 'geodatenpool':
        excel_template = resource_filename('ckanext.lhm', 'schemas/template_gdp.xlsx')
    elif p_type == 'mobidam':
        excel_template = resource_filename('ckanext.lhm', 'schemas/template_mobidam.xlsx')
    elif p_type == 'plan-db':
        excel_template = resource_filename('ckanext.lhm', 'schemas/template_plandb.xlsx')
    else:
        excel_template = resource_filename('ckanext.lhm', 'schemas/template_gdp.xlsx')

    package = dataset_name
    packages_to_files(package, 1, wdir, excel_template)

    # Download Excel
    file_path = wdir + '/excel/' + package + '.xlsx'

    return send_file(
        file_path,
        mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment = True,
        download_name = package + '.xlsx'
    )

# Register blueprint with ckan
def get_blueprints():
    return [lhm_view]


# Test push_csw route
@lhm_view.route("/lhm_view/push_csw")
def test_csw_push():
    #toolkit.h.flash_success("Simulating push to csw here, success :)")

    ###################
    # Get template
    iso_template = resource_filename('ckanext.lhm', 'schemas/iso_template.xml')
    # Get packages of type geoportal
    package_search = toolkit.get_action('package_search')
    data_dict = {'q': 'type:geoportal', 'rows': 1000  }
    context = {'ignore_auth': True}
    search_results = package_search(context, data_dict)
    datasets = search_results.get('results', [])

    # Delete old and create new output_dir
    output_dir = '/var/lib/ckan/csw_edit'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    else:
        shutil.rmtree(output_dir)
        os.makedirs(output_dir)


    # Delete all datasets on pycsw server before importing (update is not available for xml)
    
    # Pagination: Get number matched
    feat_ids = []
    url_m = 'http://pycsw:8000/collections/metadata:main/items?f=json'
    response_m = requests.post(url_m)
    dict_m = json.loads(response_m.text)
    number_matched = dict_m['numberMatched']
    for offset in range(0, number_matched, 20):

        all_url = f'http://pycsw:8000/collections/metadata:main/items?f=json&limit=20&offset={offset}'
        response_all = requests.post(all_url)
        dict_all = json.loads(response_all.text)
        for feat in dict_all['features']:
            feat_id = feat['id']
            feat_ids.append(feat_id)
    
    for feat_id in feat_ids:
        print('-----')
        print(f"Deleting {feat_id}")
        try:   
            del_url = f'http://pycsw:8000/collections/metadata:main/items/{feat_id}'
            del_response = requests.delete(del_url)
            print(f"Status Code delete: {del_response.status_code}")
            print("Response Body delete:")
            print(del_response.text)
            if del_response.status_code != 200:
                for i in range(10):
                    del_url = f'http://pycsw:8000/collections/metadata:main/items/{feat_id}'
                    del_response = requests.delete(del_url)
                    print(f"Status Code delete: {del_response.status_code}")
                    print("Response Body delete:")
                    print(del_response.text)
                    if del_response.status_code == 200:
                        break
        except:
            print(f"An error occurred:")
            print(f"Status Code delete: {del_response.status_code}")
            print("Response Body delete:")
            print(del_response.text)
    
    # Process and import each dataset to Pycsw Server
    i = 0
    for dataset in datasets:
        if 1 < 11:
            identifier = dataset.get("file_identifier")
            name = dataset.get("name")
            print('-----')
            print(f"Processing {name}, {identifier}")
            tree = convert_metadata_dict(meta_dict = dataset, template_xml = iso_template)
            outpath = output_dir + '/' + identifier + '.xml'
            tree.write(outpath, xml_declaration=True, encoding="utf-8", pretty_print=True)

            # Save dataset dict as JSON
            #dataset_name = dataset.get('name')
            #file_path = os.path.join(output_dir, f"{dataset_name}.json")
            #with open(file_path, 'w', encoding='utf-8') as f:
                #json.dump(dataset, f, indent=4, ensure_ascii=False)

            # Push the Iso XML to Pycsw
            pycsw_url = 'http://pycsw:8000/collections/metadata:main/items'
            file_path = outpath
            with open(file_path, 'rb') as f:
                xml_data = f.read()
            headers = {'Content-Type': 'application/xml'}
            try:
                response = requests.post(pycsw_url, data=xml_data, headers=headers, verify=True)
                print(f"Status Code: {response.status_code}")
                print("Response Body:")
                print(response.text)

            except:
                print(f"An error occurred:")
                print(f"Status Code: {response.status_code}")
                print("Response Body:")
                print(response.text)
        
            i = i + 1

    # Flash success message
    toolkit.h.flash_success(f"Processed {str(i)} datasets successfully and pushed them to PyCSW Server :)" )
    #toolkit.h.flash_success(f"All datasets deleted" )

    #return len(datasets)

    ###################
    referrer = toolkit.request.referrer
    if referrer:
        return toolkit.redirect_to(referrer)
    return toolkit.redirect_to('/')


# push_csw geonetwork route
@lhm_view.route("/lhm_view/push_csw_gn")
def gn_csw_push():
    #toolkit.h.flash_success("Simulating push to csw here, success :)")

#    ###################
#    # Get template
#    iso_template = resource_filename('ckanext.lhm', 'schemas/iso_template.xml')
#    # Get packages of type geoportal
    package_search = toolkit.get_action('package_search')
    data_dict = {'q': 'type:geoportal', 'rows': 1000  }
    context = {'ignore_auth': True}
    search_results = package_search(context, data_dict)
    datasets = search_results.get('results', [])
#
#    # Delete old and create new output_dir
    output_dir = '/var/lib/ckan/csw/xml'
#    if not os.path.exists(output_dir):
#        os.makedirs(output_dir)
#    else:
#        shutil.rmtree(output_dir)
#        os.makedirs(output_dir)


    # Delete all datasets on pycsw server before importing (update is not available for xml)
    
    # Pagination: Get number matched
    feat_ids = []
    url_m = 'http://pycsw:8000/collections/metadata:main/items?f=json'
    response_m = requests.post(url_m)
    dict_m = json.loads(response_m.text)
    number_matched = dict_m['numberMatched']
    for offset in range(0, number_matched, 20):

        all_url = f'http://pycsw:8000/collections/metadata:main/items?f=json&limit=20&offset={offset}'
        response_all = requests.post(all_url)
        dict_all = json.loads(response_all.text)
        for feat in dict_all['features']:
            feat_id = feat['id']
            feat_ids.append(feat_id)
    
    for feat_id in feat_ids:
        print('-----')
        print(f"Deleting {feat_id}")
        try:   
            del_url = f'http://pycsw:8000/collections/metadata:main/items/{feat_id}'
            del_response = requests.delete(del_url)
            print(f"Status Code delete: {del_response.status_code}")
            print("Response Body delete:")
            print(del_response.text)
            if del_response.status_code != 200:
                for i in range(10):
                    del_url = f'http://pycsw:8000/collections/metadata:main/items/{feat_id}'
                    del_response = requests.delete(del_url)
                    print(f"Status Code delete: {del_response.status_code}")
                    print("Response Body delete:")
                    print(del_response.text)
                    if del_response.status_code == 200:
                        break
        except:
            print(f"An error occurred:")
            print(f"Status Code delete: {del_response.status_code}")
            print("Response Body delete:")
            print(del_response.text)
    
    # Process and import each dataset to Pycsw Server
    i = 0
    for dataset in datasets:
        if 1 < 11:
            identifier = dataset.get("file_identifier")
            name = dataset.get("name")
            print('-----')
            print(f"Handling {name}, {identifier}")
#            tree = convert_metadata_dict(meta_dict = dataset, template_xml = iso_template)
            outpath = output_dir + '/' + identifier + '-iso_tree.xml'
#            tree.write(outpath, xml_declaration=True, encoding="utf-8", pretty_print=True)

            # Save dataset dict as JSON
            #dataset_name = dataset.get('name')
            #file_path = os.path.join(output_dir, f"{dataset_name}.json")
            #with open(file_path, 'w', encoding='utf-8') as f:
                #json.dump(dataset, f, indent=4, ensure_ascii=False)

            # Push the Iso XML to Pycsw
            pycsw_url = 'http://pycsw:8000/collections/metadata:main/items'
            file_path = outpath
            with open(file_path, 'rb') as f:
                xml_data = f.read()
            headers = {'Content-Type': 'application/xml'}
            try:
                response = requests.post(pycsw_url, data=xml_data, headers=headers, verify=True)
                print(f"Status Code: {response.status_code}")
                print("Response Body:")
                print(response.text)

            except:
                print(f"An error occurred:")
                print(f"Status Code: {response.status_code}")
                print("Response Body:")
                print(response.text)
        
            i = i + 1

    # Flash success message
    toolkit.h.flash_success(f"Pushed {str(i)} XML files successfully to PyCSW Server :)" )
    #toolkit.h.flash_success(f"All datasets deleted" )

    #return len(datasets)

    ###################
    referrer = toolkit.request.referrer
    if referrer:
        return toolkit.redirect_to(referrer)
    return toolkit.redirect_to('/')
