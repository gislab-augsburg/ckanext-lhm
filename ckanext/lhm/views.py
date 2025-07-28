from flask import Blueprint, send_file
import json
import subprocess
import os
from openpyxl import load_workbook
from openpyxl.styles import Alignment
from ckanext.lhm.get_data import packages_to_files

lhm_view = Blueprint('lhm_view', __name__)

## Excel to PDF Conversion
def convert_xlsx_to_pdf(input_path, output_dir, package):
    cmd = [
        "libreoffice",
        "--headless",
        "--convert-to", "ods",
        input_path,
        "--outdir", output_dir
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
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
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print("LibreOffice output:", result.stdout)
        print("LibreOffice errors:", result.stderr)
        return True
    except subprocess.CalledProcessError as e:
        print("Fehler bei der Konvertierung:", e.stderr)
        return False
    

@lhm_view.route("/lhm_view/pdf/<dataset_name>")
def generate_pdf(dataset_name):

    ## Generate Package Excel
    # Get config values
    #arg_config = sys.argv[1]
    arg_config = '/srv/app/md_download/config-download.json'
    with open(arg_config, 'r') as config_file:
        config = json.load(config_file)
    wdir= config['wdir']
    template = config['template']

    # Create directories
    if os.path.exists(wdir) == False:
        os.mkdir(wdir)
    if os.path.exists(f'{wdir}/pdf') == False:
        os.mkdir(f'{wdir}/pdf')
    
    package = dataset_name
    packages_to_files(package, 1, wdir, template)

    # Define path
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

    ## Convert to PDF
    input_file = file_path
    output_dir = wdir + '/pdf'
    convert_xlsx_to_pdf(input_file, output_dir, package)
    output_pdf = wdir + '/pdf/' + package + '.pdf'

    ## Download PDF
    return send_file(
        output_pdf,
        mimetype='application/pdf',
        as_attachment=True,
        attachment_filename=package + '.pdf'
    )


@lhm_view.route("/lhm_view/excel/<dataset_name>")
def generate_xlsx(dataset_name):

    ## Generate Package Excel
    # Get config values
    #arg_config = sys.argv[1]
    arg_config = '/srv/app/md_download/config-download.json'
    with open(arg_config, 'r') as config_file:
        config = json.load(config_file)
    wdir= config['wdir']
    template = config['template']

    # Create directories
    if os.path.exists(wdir) == False:
        os.mkdir(wdir)
    if os.path.exists(f'{wdir}/pdf') == False:
        os.mkdir(f'{wdir}/pdf')

    package = dataset_name
    packages_to_files(package, 1, wdir, template)

    ## Download Excel
    file_path = wdir + '/excel/' + package + '.xlsx'

    return send_file(
        file_path,
        mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment = True,
        attachment_filename = package + '.xlsx'
    )

def get_blueprints():
    return [lhm_view]
