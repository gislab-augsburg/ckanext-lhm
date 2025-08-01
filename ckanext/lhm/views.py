from flask import Blueprint, send_file
import json
import subprocess
import os
from openpyxl import load_workbook
from openpyxl.styles import Alignment
from ckanext.lhm.get_data import packages_to_files
from pkg_resources import resource_filename

# Create routes
lhm_view = Blueprint('lhm_view', __name__)

# Define variables, Create working dir
def get_export_vars():
    from ckan.common import config
    storage = config.get('ckan.storage_path')
    wdir = storage + '/export'
    if os.path.exists(wdir) == False:
        os.mkdir(wdir)
    excel_template = resource_filename('ckanext.lhm', 'schemas/template_v1.2.2.xlsx')
    return wdir, excel_template

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
    wdir = vars[0]
    excel_template = vars[1]

    # Create pdf directory
    if os.path.exists(f'{wdir}/pdf') == False:
        os.mkdir(f'{wdir}/pdf')
    
    package = dataset_name
    packages_to_files(package, 1, wdir, excel_template)

    # Define path to excel
    file_path = wdir + '/excel/' + package + '.xlsx'

    # Add headers
    wb = load_workbook(file_path)
    ws_0 = wb["GDP Metadaten"]
    ws_1 = wb["Datenverzeichnis"]
    ws_2 = wb["Katalogwerte"]
    ws_3 = wb["Dienste und Dokumente"]
    ws_0.oddHeader.center.text = "GDP Metadaten"
    ws_1.oddHeader.center.text = "Datenverzeichnis"
    ws_2.oddHeader.center.text = "Katalogwerte"
    ws_3.oddHeader.center.text = "Dienste und Dokumente"

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
        attachment_filename=package + '.pdf'
    )

# Generate package excel for download
@lhm_view.route("/lhm_view/excel/<dataset_name>")
def generate_xlsx(dataset_name):

    # Get vars
    vars = get_export_vars()
    wdir = vars[0]
    excel_template = vars[1]

    package = dataset_name
    packages_to_files(package, 1, wdir, excel_template)

    # Download Excel
    file_path = wdir + '/excel/' + package + '.xlsx'

    return send_file(
        file_path,
        mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment = True,
        attachment_filename = package + '.xlsx'
    )

# Register blueprint with ckan
def get_blueprints():
    return [lhm_view]
