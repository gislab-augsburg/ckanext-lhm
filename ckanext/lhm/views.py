from flask import Blueprint, abort, send_file
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import subprocess
import os
from openpyxl import load_workbook
from openpyxl.styles import Alignment
from ckanext.lhm.export.get_data_export import packages_to_files
from ckanext.lhm.export.get_data import MASTER, EXCEL_TEMPLATES
from ckanext.lhm.export.field_mapping import MasterConfig
from ckanext.lhm.export.templates_from_master import save_excel_compatible
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

def get_pycsw_host_url():
    host = os.environ.get('CKANEXT__LHM__PYCSW_URL')
        
    if not host or not host.strip():
        host = 'http://pycsw:8000'
        
    return host.strip()

def get_pycsw_url(path=""):
    host = get_pycsw_host_url()
    return f"{host}{path}"

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

# Export a dataset with the form belonging to its CKAN schema.
def _export_dataset_xlsx(dataset_name, workdir):
    dataset_type = get_package_type(dataset_name)
    master = MasterConfig(MASTER)
    try:
        schema = master.schema_for_type(dataset_type)
    finally:
        master.workbook.close()
    if schema is None:
        abort(404, description=f"No Excel export for dataset type {dataset_type!r}")

    form = EXCEL_TEMPLATES / f"form_{schema}.xlsx"
    if not form.is_file():
        raise FileNotFoundError(f"Excel form is missing: {form}")
    exported = packages_to_files(dataset_name, 1, workdir, str(form))
    if dataset_name not in exported:
        raise RuntimeError(f"Dataset {dataset_name!r} was not exported")
    workbook = Path(workdir) / "excel" / f"{dataset_name}.xlsx"
    if not workbook.is_file():
        raise FileNotFoundError(f"Exported workbook is missing: {workbook}")
    return workbook


def _prepare_pdf_workbook(source, destination):
    workbook = load_workbook(source)
    try:
        headings = {
            "Metadaten": "Metadaten",
            "Datenverzeichnis": "Datenverzeichnis",
            "Katalogwerte": "Katalogwerte",
            "Dienste und Dokumente": "Dienste und Dokumente",
        }
        for sheet_name, heading in headings.items():
            sheet = workbook[sheet_name]
            sheet.oddHeader.center.text = heading
            for row in sheet:
                for cell in row:
                    cell.alignment = Alignment(wrapText=True, vertical="top")

        # Keep the previous PDF layout, but locate the long note by text so
        # adding a metadata field cannot move the wrong heading into its place.
        metadata = workbook["Metadaten"]
        for row in metadata.iter_rows(min_col=1, max_col=1):
            cell = row[0]
            if (isinstance(cell.value, str) and
                    cell.value.startswith('Hinweistext Langversion zu "LHM-extern')):
                cell.value = ""
                break
        destination.parent.mkdir(parents=True, exist_ok=True)
        save_excel_compatible(workbook, destination)
    finally:
        workbook.close()


def convert_xlsx_to_pdf(input_path, output_dir, package):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    profile = output_dir / "libreoffice_profile"
    profile.mkdir(exist_ok=True)
    env = os.environ.copy()
    env["HOME"] = str(output_dir)
    source = Path(input_path)
    for target_format in ("ods", "pdf"):
        expected = output_dir / f"{package}.{target_format}"
        command = [
            "libreoffice", f"-env:UserInstallation={profile.as_uri()}",
            "--headless", "--convert-to", target_format,
            str(source), "--outdir", str(output_dir),
        ]
        result = subprocess.run(command, capture_output=True, text=True,
                                env=env, timeout=180)
        if result.returncode != 0 or not expected.is_file():
            detail = result.stderr.strip() or result.stdout.strip()
            raise RuntimeError(
                f"LibreOffice conversion to {target_format} failed: {detail}")
        source = expected
    return source


@lhm_view.route("/lhm_view/pdf/<dataset_name>")
def generate_pdf(dataset_name):
    with TemporaryDirectory(prefix="lhm-export-", dir=get_export_vars()) as workdir:
        workbook = _export_dataset_xlsx(dataset_name, workdir)
        pdf_source = Path(workdir) / "pdf_input" / f"{dataset_name}.xlsx"
        _prepare_pdf_workbook(workbook, pdf_source)
        pdf = convert_xlsx_to_pdf(pdf_source, Path(workdir) / "pdf", dataset_name)
        content = pdf.read_bytes()
    return send_file(BytesIO(content), mimetype="application/pdf",
                     as_attachment=True, download_name=dataset_name + ".pdf")


@lhm_view.route("/lhm_view/excel/<dataset_name>")
def generate_xlsx(dataset_name):
    with TemporaryDirectory(prefix="lhm-export-", dir=get_export_vars()) as workdir:
        workbook = _export_dataset_xlsx(dataset_name, workdir)
        content = workbook.read_bytes()
    return send_file(
        BytesIO(content),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True, download_name=dataset_name + ".xlsx",
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
    url_m = get_pycsw_url("/collections/metadata:main/items?f=json")
    response_m = requests.post(url_m)
    dict_m = json.loads(response_m.text)
    number_matched = dict_m['numberMatched']
    for offset in range(0, number_matched, 20):

        all_url = get_pycsw_url(f"/collections/metadata:main/items?f=json&limit=20&offset={offset}")
        response_all = requests.post(all_url)
        dict_all = json.loads(response_all.text)
        for feat in dict_all['features']:
            feat_id = feat['id']
            feat_ids.append(feat_id)
    
    for feat_id in feat_ids:
        print('-----')
        print(f"Deleting {feat_id}")
        try:   
            del_url = get_pycsw_url(f"/collections/metadata:main/items/{feat_id}")
            del_response = requests.delete(del_url)
            print(f"Status Code delete: {del_response.status_code}")
            print("Response Body delete:")
            print(del_response.text)
            if del_response.status_code != 200:
                for i in range(10):
                    del_url = get_pycsw_url(f"/collections/metadata:main/items/{feat_id}")
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
            pycsw_url = get_pycsw_url("/collections/metadata:main/items")
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
    url_m = get_pycsw_url("/collections/metadata:main/items?f=json")
    response_m = requests.post(url_m)
    dict_m = json.loads(response_m.text)
    number_matched = dict_m['numberMatched']
    for offset in range(0, number_matched, 20):

        all_url = get_pycsw_url(f"/collections/metadata:main/items?f=json&limit=20&offset={offset}")
        response_all = requests.post(all_url)
        dict_all = json.loads(response_all.text)
        for feat in dict_all['features']:
            feat_id = feat['id']
            feat_ids.append(feat_id)
    
    for feat_id in feat_ids:
        print('-----')
        print(f"Deleting {feat_id}")
        try:   
            del_url = get_pycsw_url(f"/collections/metadata:main/items/{feat_id}")
            del_response = requests.delete(del_url)
            print(f"Status Code delete: {del_response.status_code}")
            print("Response Body delete:")
            print(del_response.text)
            if del_response.status_code != 200:
                for i in range(10):
                    del_url = get_pycsw_url(f"/collections/metadata:main/items/{feat_id}")
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
#           tree = convert_metadata_dict(meta_dict = dataset, template_xml = iso_template)
            outpath = output_dir + '/' + identifier + '-iso_tree.xml'
#           tree.write(outpath, xml_declaration=True, encoding="utf-8", pretty_print=True)

            # Save dataset dict as JSON
            #dataset_name = dataset.get('name')
            #file_path = os.path.join(output_dir, f"{dataset_name}.json")
            #with open(file_path, 'w', encoding='utf-8') as f:
                #json.dump(dataset, f, indent=4, ensure_ascii=False)

            # Push the Iso XML to Pycsw
            pycsw_url = get_pycsw_url("/collections/metadata:main/items")
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
