#!/usr/bin/env python

from openpyxl import Workbook
from openpyxl import load_workbook
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.reader.excel import warnings
from openpyxl.styles import PatternFill
from openpyxl.formatting.rule import FormulaRule
from openpyxl.utils import get_column_letter
from copy import copy
import re
from io import BytesIO
from zipfile import ZipFile
from bisect import bisect_left, bisect_right
from openpyxl.worksheet.cell_range import CellRange
from pathlib import Path
import argparse
import json
import os

try:
    from .field_mapping import (MasterConfig, TABLES, bind_field_name,
                                embedded_field_rows, table_columns)
    from .choice_mapping import ChoiceMap
except ImportError:
    from field_mapping import (MasterConfig, TABLES, bind_field_name,
                               embedded_field_rows, table_columns)
    from choice_mapping import ChoiceMap


# Define values #################################################
_ROOT = Path(__file__).resolve().parent
EXCEL_TEMPLATES = _ROOT / 'excel_templates'
template_master = EXCEL_TEMPLATES / 'template_master_config.xlsx'
types = []
first_line_md = 2
first_line_dv = 40
first_line_kw = 46
first_line_dd = 50
last_line_dd = 53
#################################################################


def configure_section_rows(excel_template):
    """Find section boundaries after metadata fields are inserted or removed."""
    global first_line_dv, first_line_kw, first_line_dd, last_line_dd, types
    book = load_workbook(excel_template, data_only=True)
    ws = book["Metadaten"]
    types = [str(row[0]) for row in book['Schemata'].iter_rows(min_row=2, values_only=True)
             if row[0]]
    sections = ("Datenverzeichnis -", "Katalogwerte -", "Dienste und Dokumente -")
    starts = {}
    ends = {}
    for row in ws.iter_rows(min_row=2, values_only=False):
        label = str(row[0].value or "")
        for section in sections:
            if label.startswith(section):
                starts.setdefault(section, row[0].row)
                ends[section] = row[0].row
    if len(starts) != len(sections):
        raise ValueError("Section rows are missing from the master file")
    first_line_dv, first_line_kw, first_line_dd = (starts[s] for s in sections)
    last_line_dd = ends[sections[2]]
    book.close()


def validate_master_for_forms(master):
    """Check structure once before generating forms; report unmapped choices."""
    headers = master.headers
    schema_rows = [row for row in master.workbook['Schemata'].iter_rows(
        min_row=2, values_only=True) if row[0]]
    keys = [str(row[0]) for row in schema_rows]
    types_seen = [str(row[1]) for row in schema_rows if row[1]]
    if len(keys) != len(set(keys)) or len(types_seen) != len(set(types_seen)):
        raise ValueError("Schemata has duplicate schema identifiers or CKAN types")
    if len(types_seen) != len(keys):
        raise ValueError("Schemata contains a schema without a CKAN type")

    warnings = {}
    for schema in keys:
        if schema not in headers or schema + '_w' not in headers:
            raise ValueError(f"Metadaten is missing {schema!r} or {schema + '_w'!r}")
        specs = list(master.fields(schema).values())
        for sheet_name in TABLES:
            table_specs = master.table_specs(sheet_name, schema)
            columns = set(table_columns(master.workbook[sheet_name], master).values())
            for name, spec in table_specs.items():
                if name not in columns:
                    raise ValueError(f"{sheet_name}: no header for field {name!r}")
            specs.extend(table_specs.values())
        for spec in specs:
            if spec.source_row < first_line_dv:
                value_columns_for_format(spec.format)
            if 'select' not in spec.format:
                continue
            if not spec.dropdown:
                raise ValueError(f"Metadaten row {spec.source_row}: "
                                 f"dropdown range for {schema}/{spec.name} is missing")
            try:
                area = CellRange(str(spec.dropdown))
            except ValueError as exc:
                raise ValueError(f"Metadaten row {spec.source_row}: "
                                 f"invalid dropdown range {spec.dropdown!r}") from exc
            if area.min_col != area.max_col or area.min_row < 2:
                raise ValueError(f"Metadaten row {spec.source_row}: "
                                 f"invalid dropdown range {spec.dropdown!r}")
            choices = master.workbook['Wertelisten']
            if not any(choices.cell(row, area.min_col).value not in (None, '')
                       for row in range(area.min_row, area.max_row + 1)):
                raise ValueError(f"Metadaten row {spec.source_row}: "
                                 f"dropdown range {spec.dropdown!r} is empty")
        choices = ChoiceMap(master.filename, schema)
        type_choices = choices.active.get('type', {})
        if len(type_choices) != 1 or next(iter(type_choices.values())) != master.schemas[schema]:
            raise ValueError(f"Metadaten: type dropdown for {schema} must contain "
                             "exactly its CKAN type")
        for name, displays in choices.unmapped.items():
            for display in displays:
                warnings.setdefault((name, display), set()).add(schema)
    for (name, display), schemas in sorted(warnings.items()):
        print(f"CONFIG WARNING: no CKAN_Werte mapping for {name}: {display!r} "
              f"(schemas: {', '.join(sorted(schemas))})", flush=True)


# Add dropdown validation
def add_validation_dropdown(ws, coords, formula, allow_blank=False):
    val_fields = []
    # Use existing validation
    for dv in ws.data_validations.dataValidation:   
        val_fields.append(dv.sqref)       
        if dv.sqref == coords:
            dv.type = 'list'
            dv.formula1 = formula
            dv.allow_blank = allow_blank
            dv.error ='Bitte wählen Sie einen Wert aus der Drop-Down Liste'
            dv.errorTitle = 'Ungültiger Eintrag'
            dv.showErrorMessage = True
            dv_final = dv
    # Add new validation if no existing
    if coords not in val_fields:       
        cell = ws[coords]
        dv = DataValidation(type="list", formula1=formula,
                            allow_blank=allow_blank)
        dv.error ='Bitte wählen Sie einen Wert aus der Drop-Down Liste'
        dv.errorTitle = 'Ungültiger Eintrag'
        dv.showErrorMessage = True
        dv.add(cell)
        dv_final = dv
        
    return dv_final


# Give a required cell its own validation before changing a shared rule.
def isolate_validation_cell(ws, validation, coords):
    cell = ws[coords]
    areas = list(validation.sqref.ranges)
    if len(areas) == 1:
        area = areas[0]
        if (area.min_row == area.max_row == cell.row
                and area.min_col == area.max_col == cell.column):
            return validation

    remaining = []
    for area in areas:
        if not (area.min_row <= cell.row <= area.max_row
                and area.min_col <= cell.column <= area.max_col):
            remaining.append(str(area))
            continue
        pieces = (
            (area.min_col, area.max_col, area.min_row, cell.row - 1),
            (area.min_col, area.max_col, cell.row + 1, area.max_row),
            (area.min_col, cell.column - 1, cell.row, cell.row),
            (cell.column + 1, area.max_col, cell.row, cell.row),
        )
        for min_col, max_col, min_row, max_row in pieces:
            if min_col <= max_col and min_row <= max_row:
                remaining.append(str(CellRange(
                    min_col=min_col, max_col=max_col,
                    min_row=min_row, max_row=max_row,
                )))

    isolated = copy(validation)
    isolated.sqref = coords
    if remaining:
        validation.sqref = ' '.join(remaining)
    else:
        ws.data_validations.dataValidation = [
            dv for dv in ws.data_validations.dataValidation if dv is not validation
        ]
    ws.add_data_validation(isolated)
    return isolated


# Add field-not-empty validation
def add_validation_mandatory(ws, coords):
    # Excel permits one validation rule per cell. A required dropdown must
    # retain its list rule; only text fields need the text-length rule.
    for dv in list(ws.data_validations.dataValidation):
        if coords in dv:
            dv = isolate_validation_cell(ws, dv, coords)
            dv.allow_blank = False
            if dv.type != 'list':
                dv.type = 'textLength'
                dv.operator = 'greaterThan'
                dv.formula1 = '0'
                dv.error = 'Dieses Feld darf nicht leer sein, ein Wert ist erforderlich'
                dv.errorTitle = 'Ungültiger Eintrag'
            dv.showErrorMessage = True
            return dv

    dv = DataValidation(type='textLength', operator='greaterThan',
                        formula1='0', allow_blank=False)
    dv.error = 'Dieses Feld darf nicht leer sein, ein Wert ist erforderlich'
    dv.errorTitle = 'Ungültiger Eintrag'
    dv.showErrorMessage = True
    dv.add(ws[coords])
    ws.add_data_validation(dv)
    return dv


def split_coords(coordinate):
    # Sucht nach einer Gruppe von Buchstaben gefolgt von einer Gruppe von Zahlen
    match = re.match(r"([A-Za-z]+)([0-9]+)", coordinate)
    if match:
        letters = match.group(1)
        numbers = match.group(2)  # Bleibt als String bestehen
        return letters, numbers
    return None, None


def adjust_merged_cells_after_delete(ws, del_rows):
    """
    Safely shifts merged cell ranges internally to match row deletions
    without triggering openpyxl KeyError issues.
    """
    # Create a list of the ranges to modify
    merged_ranges = list(ws.merged_cells.ranges)
    
    for mcr in merged_ranges:
        # Count how many of the deleted rows were strictly ABOVE this merged range
        rows_above_deleted = sum(1 for r in del_rows if r < mcr.min_row)
        
        if rows_above_deleted > 0:
            # Shift the internal boundaries of the existing merged cell object upward
            mcr.min_row = max(1, mcr.min_row - rows_above_deleted)
            mcr.max_row = max(1, mcr.max_row - rows_above_deleted)


def save_excel_compatible(workbook, filename):
    """Save an XLSX file and fix duplicate UTC timezone suffixes."""
    buffer = BytesIO()
    workbook.save(buffer)
    buffer.seek(0)

    with ZipFile(buffer, "r") as source:
        with ZipFile(filename, "w") as target:
            target.comment = source.comment

            for entry in source.infolist():
                data = source.read(entry.filename)

                if entry.filename == "docProps/core.xml":
                    for field in (b"created", b"modified"):
                        closing_tag = b"</dcterms:" + field + b">"
                        data = data.replace(
                            b"+00:00Z" + closing_tag,
                            b"Z" + closing_tag,
                        )

                target.writestr(entry, data)


def adjust_validations_after_delete(ws, deleted_rows):
    """Remap validation targets using ORIGINAL, 1-based deleted row numbers.


    Call once after all row deletions. Source-list formulas are unchanged;
    this suits the template's lists on the separate Wertelisten sheet.
    """
    deleted = sorted(set(deleted_rows))
    kept = []
    seen = set()
    for dv in ws.data_validations.dataValidation:
        # Existing helper code can register the same object more than once.
        if id(dv) in seen:
            continue
        seen.add(id(dv))
        ranges = []
        for area in dv.sqref.ranges:
            first = area.min_row - bisect_left(deleted, area.min_row)
            last = area.max_row - bisect_right(deleted, area.max_row)
            if first <= last:
                ranges.append(str(CellRange(
                    min_col=area.min_col, max_col=area.max_col,
                    min_row=first, max_row=last,
                )))
        if ranges:
            dv.sqref = " ".join(ranges)
            kept.append(dv)
    ws.data_validations.dataValidation = kept


def value_columns_for_format(format_value):
    """Return editable column numbers for a metadata field (B is column 2)."""
    format_value = str(format_value or '').strip().lower()
    multi = re.fullmatch(r'multi-(?:text|select)(?:-(\d+))?', format_value)
    if multi:
        count = int(multi.group(1)) if multi.group(1) else 10
        if not 1 <= count <= 10:
            raise ValueError(f'Unsupported number of value columns: {format_value}')
        return range(2, 2 + count)
    if format_value in ('text', 'select', 'email'):
        return range(2, 3)
    raise ValueError(f'Unknown metadata format: {format_value}')


# Differential fills for conditional formatting are interpreted by Excel via
# bgColor.  fgColor alone becomes a pattern colour and leaves the cell blue.
INVALID_FILL = PatternFill(fill_type='solid', bgColor='FFFF0000')


def invalid_value_formula(validation, address, blank_is_invalid=True):
    """Excel formula for the validation types generated by this script."""
    if validation.type == 'list' and validation.formula1:
        source_range = validation.formula1.lstrip('=')
        if '!' in source_range:
            source_range = source_range.replace('"', '""')
            bad_choice = (f'SUMPRODUCT(--(INDIRECT("{source_range}")='
                          f'{address}))=0')
            if blank_is_invalid:
                return f'OR({address}="",{bad_choice})'
            return f'AND({address}<>"",{bad_choice})'
    if (validation.type == 'textLength'
            and validation.operator == 'greaterThan'
            and str(validation.formula1) == '0'):
        return f'LEN({address}&"")=0' if blank_is_invalid else None
    return None


def validation_at(ws, address):
    return next((dv for dv in ws.data_validations.dataValidation
                 if dv.type in ('list', 'textLength') and address in dv), None)


def set_locked(cell, locked):
    protection = copy(cell.protection)
    protection.locked = locked
    cell.protection = protection


def read_sheet_password(config_file=None):
    """Use the harvester JSON locally or the pod's environment variable."""
    if config_file is not None:
        with open(config_file, encoding='utf-8') as handle:
            password = json.load(handle).get('sheet_protection')
    else:
        password = os.environ.get('sheet_protection')
    if not isinstance(password, str) or not password:
        raise ValueError("'sheet_protection' is missing from JSON configuration or environment")
    return password


def enable_sheet_protection(ws, password):
    ws.protection.sheet = True
    ws.protection.formatCells = True
    ws.protection.set_password(password)


def finalize_form_workbook(book, password):
    """Keep only the Excel dropdown source and store stable names invisibly."""
    metadata = book['Metadaten']
    name_column = next((cell.column for cell in metadata[1]
                        if cell.value == 'Name'), None)
    if name_column is not None:
        for row in metadata.iter_rows(min_row=2):
            name = row[name_column - 1].value
            if name:
                bind_field_name(book, str(name), metadata.cell(row[0].row, 2).coordinate)
        metadata.delete_cols(name_column)
    elif not embedded_field_rows(book):
        raise ValueError('Form has neither a Name column nor field references')
    for sheet_name in ('CKAN_Werte', 'Legacy_136_137', 'Schemata'):
        if sheet_name in book:
            del book[sheet_name]
    if 'Wertelisten' not in book:
        raise ValueError('Wertelisten sheet is missing; dropdowns require this sheet')
    lists = book['Wertelisten']
    enable_sheet_protection(lists, password)
    lists.sheet_state = 'hidden'
    for sheet_name in ('Metadaten', 'Datenverzeichnis', 'Katalogwerte',
                       'Dienste und Dokumente'):
        enable_sheet_protection(book[sheet_name], password)


def protect_and_mark_invalid_values(ws, editable_fields, deleted_rows,
                                    required_fields, password):
    """Protect Metadaten and overlay invalid cells with a temporary red fill."""
    deleted = sorted(set(deleted_rows))

    # Lock after row deletion so old unlocked positions cannot survive.
    for row in ws.iter_rows():
        for cell in row:
            set_locked(cell, True)

    for source_row, columns in editable_fields.items():
        target_row = source_row - bisect_left(deleted, source_row)
        is_multi = len(columns) > 1
        if is_multi and source_row in required_fields:
            first = ws.cell(target_row, columns.start).coordinate
            last = ws.cell(target_row, columns.stop - 1).coordinate
            ws.conditional_formatting.add(
                f'{first}:{last}',
                FormulaRule(formula=[f'COUNTIF(${get_column_letter(columns.start)}'
                                     f'{target_row}:${get_column_letter(columns.stop - 1)}'
                                     f'{target_row},"<>")=0'],
                            fill=INVALID_FILL),
            )
        for column in columns:
            cell = ws.cell(target_row, column)
            set_locked(cell, False)
            blank_allowed = is_multi or source_row not in required_fields
            for candidate in ws.data_validations.dataValidation:
                if cell.coordinate in candidate:
                    candidate.allow_blank = blank_allowed
            validation = validation_at(ws, cell.coordinate)
            if validation is None:
                continue
            formula = invalid_value_formula(validation, cell.coordinate,
                                            blank_is_invalid=(source_row in required_fields
                                                              and not is_multi))
            if formula:
                # A conditional fill never changes the cell's original fill.
                ws.conditional_formatting.add(
                    cell.coordinate,
                    FormulaRule(formula=[formula], fill=INVALID_FILL),
                )

    enable_sheet_protection(ws, password)


def protect_and_mark_table(ws, master, schema, last_row, password):
    """Protect table headers and mark invalid values only in started rows."""
    columns = [cell.column for cell in ws[1] if cell.value is not None]
    names = table_columns(ws, master)
    specs = master.table_specs(ws.title, schema)
    if not columns:
        raise ValueError(f'No value columns found in {ws.title}')
    # The master contains borders in the header only.  Give the data cells
    # their own borders so the input grid remains visible in all three sheets.
    for column in columns:
        header = ws.cell(1, column)
        header_border = copy(header.border)
        font_size = header.font.sz
        for row in range(2, last_row + 1):
            cell = ws.cell(row, column)
            # The master may set 10 pt on a whole column while its empty
            # cells still use the workbook's 11 pt default font. Once a
            # border/protection is assigned, those cells need a direct font.
            if font_size is not None and (cell._style is None or cell._style.fontId == 0):
                font = copy(cell.font)
                font.sz = font_size
                cell.font = font
            cell.border = header_border
        # A normal Excel paste can replace the cell's direct border.  The
        # unconditional border rule restores its visible grid afterward.
        letter = get_column_letter(column)
        ws.conditional_formatting.add(
            f'{letter}2:{letter}{last_row}',
            FormulaRule(formula=['TRUE'], border=header_border),
        )
    for row in ws.iter_rows(min_row=1, max_row=max(ws.max_row, last_row),
                            max_col=ws.max_column):
        for cell in row:
            set_locked(cell, not (2 <= cell.row <= last_row
                                  and cell.column in columns))

    for column in columns:
        letter = get_column_letter(column)
        address = f'{letter}2'
        validation = validation_at(ws, address)
        if validation is None:
            continue
        name = names.get(column)
        required = bool(name in specs and specs[name].required)
        invalid = invalid_value_formula(validation, address,
                                        blank_is_invalid=required)
        if invalid is None:
            continue
        # The row counts only if ANOTHER cell contains a value. Empty rows
        # retain their base fill. A filled, valid cell also retains that fill.
        other_cells = ','.join(
            f'${get_column_letter(other_column)}2<>""'
            for other_column in columns if other_column != column
        )
        other_cell_filled = f'OR({other_cells})' if other_cells else 'FALSE'
        ws.conditional_formatting.add(
            f'{letter}2:{letter}{last_row}',
            FormulaRule(formula=[f'AND({other_cell_filled},{invalid})'],
                        fill=INVALID_FILL),
        )

    enable_sheet_protection(ws, password)


def add_table_validations(ws, master, schema, last_row):
    """Build table dropdowns and mandatory checks from field names and flags."""
    columns = {name: column for column, name in table_columns(ws, master).items()
               if name}
    for name, spec in master.table_specs(ws.title, schema).items():
        if name not in columns:
            raise ValueError(f"{ws.title}: no column for field {name!r}")
        letter = get_column_letter(columns[name])
        if 'select' in spec.format:
            if not spec.dropdown:
                raise ValueError(f"{ws.title}: no dropdown range for {name!r}")
            area = CellRange(str(spec.dropdown))
            source = get_column_letter(area.min_col)
            formula = (f'=Wertelisten!${source}${area.min_row}:'
                       f'${source}${area.max_row}')
            for row in range(2, last_row + 1):
                validation = add_validation_dropdown(
                    ws, f'{letter}{row}', formula, allow_blank=not spec.required)
                ws.add_data_validation(validation)
        if spec.required and validation_at(ws, f'{letter}2') is None:
            dv = DataValidation(type='textLength', operator='greaterThan',
                                formula1='0', allow_blank=False)
            dv.error = 'Dieses Feld darf nicht leer sein, ein Wert ist erforderlich'
            dv.errorTitle = 'Ungültiger Eintrag'
            dv.showErrorMessage = True
            dv.add(f'{letter}2:{letter}{last_row}')
            ws.add_data_validation(dv)

  
# Create templates and empty forms from master config excel

def create_empty_forms(excel_template=template_master, sheet_password=None):

    if sheet_password is None:
        sheet_password = read_sheet_password()

    configure_section_rows(excel_template)
    master = MasterConfig(excel_template)
    validate_master_for_forms(master)
    EXCEL_TEMPLATES.mkdir(parents=True, exist_ok=True)

    print('Creating empty forms for:')

    for type_ in types:
        print(type_)

        # Open excel template, define sheets
        warnings.simplefilter(action='ignore')
        wb = load_workbook(filename=excel_template)
        ws = wb["Metadaten"]
        ws_1 = wb["Datenverzeichnis"]
        ws_2 = wb["Katalogwerte"]
        ws_3 = wb["Dienste und Dokumente"]
        # Spalten für Schema Typ 
        for cells in ws.iter_rows(min_row=1, max_row=1, values_only=False):
            for cell in cells:
                if cell.value == f'{type_}':
                    col_field_exists = split_coords(cell.coordinate)[0]
                    #print(col_field_exists)
                    break
        
        for cells in ws.iter_rows(min_row=1, max_row=1, values_only=False):
            for cell in cells:
                if cell.value == f'{type_}_w':
                    col_dropdown = split_coords(cell.coordinate)[0]
                    #print(col_dropdown)
                    break

        for cells in ws.iter_rows(min_row=1, max_row=1, values_only=False):
            for cell in cells:
                if cell.value == 'Format':
                    col_format = split_coords(cell.coordinate)[0]
                    col_format_nr = cell.column
                    #print(col_dropdown)
                    break

        for cell in ws[1]:
            if cell.value == 'Pflichtfeld':
                col_mandatory = split_coords(cell.coordinate)[0]
            elif cell.value == 'Name':
                col_name = split_coords(cell.coordinate)[0]

        for cells in ws.iter_rows(min_row=1, max_row=1, values_only=False):
            for cell in cells:
                col_end_nr = cell.column

        # Add dropdowns to select fields
        # Main metadata select
        for row in range(first_line_md, first_line_dv):
            value_cell_coords = f'B{str(row)}'
            dropdown_cell_coords = f'{col_dropdown}{str(row)}'
            dropdown_coords = ws[dropdown_cell_coords].value
            format_value = str(ws[f'{col_format}{row}'].value or '').strip()
            is_multi = format_value.startswith('multi-')
            
            if 'select' in format_value and dropdown_coords is not None:
                one = split_coords(dropdown_coords.split(':')[0])[0]
                two = split_coords(dropdown_coords.split(':')[0])[1]
                three = split_coords(dropdown_coords.split(':')[1])[0]
                four = split_coords(dropdown_coords.split(':')[1])[1]
                #print(one, two, three, four)
                validation_string = f'=Wertelisten!${one}${two}:${three}${four}'
                validation = add_validation_dropdown(
                    ws, value_cell_coords, validation_string,
                    allow_blank=(is_multi or ws[f'{col_mandatory}{row}'].value != 'x'))
                ws.add_data_validation(validation)

                # The same list applies to every value column of multi-select
                # fields, including numbered formats such as multi-select-5.
                if format_value.startswith('multi-select'):
                    for column in list(value_columns_for_format(format_value))[1:]:
                        value_cell_coords = ws.cell(row, column).coordinate
                        validation = add_validation_dropdown(
                            ws, value_cell_coords, validation_string,
                            allow_blank=True)
                        ws.add_data_validation(validation)

        # Apply mandatory rules to the Wert column of fields kept in this
        # schema. The master form also retains rows 40-53.
        last_metadata_row = last_line_dd if type_ == 'master' else first_line_dv - 1
        for row in range(first_line_md, last_metadata_row + 1):
            if ws[f'{col_mandatory}{row}'].value != 'x':
                continue
            if row < first_line_dv and ws[f'{col_field_exists}{row}'].value != 'x':
                continue
            if not str(ws[f'{col_format}{row}'].value or '').startswith('multi-'):
                add_validation_mandatory(ws, f'B{row}')

        # Delete rows not part of schema
        del_rows = []
        del_cols = []
        for row in range(first_line_md, first_line_dv):
            exists = f'{col_field_exists}{str(row)}'
            if ws[exists].value != 'x' or str(ws.cell(row, 1).value or '').strip() == 'Version':
                del_rows.append(row)

        editable_fields = {
            row: value_columns_for_format(ws[f'{col_format}{row}'].value)
            for row in range(first_line_md, first_line_dv)
            if row not in del_rows
        }
        required_fields = {
            row for row in editable_fields
            if ws[f'{col_mandatory}{row}'].value == 'x'
        }
     
        # Delete config rows and cols, not for master
        if type_ != 'master':
            for row in range(first_line_dv, last_line_dd + 1):
                del_rows.append(row)
            for col in range (col_format_nr, col_end_nr + 1):
                del_cols.append(col)

        #print('FINAL rows to delete:')
        #print(del_rows)
        #print('FINAL cols to delete:')
        #print(del_cols)

        for row_idx in sorted(del_rows, reverse=True):
            ws.delete_rows(row_idx)
        adjust_validations_after_delete(ws, del_rows)
        adjust_merged_cells_after_delete(ws, del_rows)

        for col_idx in sorted(del_cols, reverse=True):
            ws.delete_cols(col_idx)

        # Protect Sheet and Save Excel
        protect_and_mark_invalid_values(ws, editable_fields, del_rows,
                                        required_fields, sheet_password)
        add_table_validations(ws_1, master, type_, 201)
        add_table_validations(ws_2, master, type_, 1501)
        add_table_validations(ws_3, master, type_, 201)
        protect_and_mark_table(ws_1, master, type_, 201, sheet_password)
        protect_and_mark_table(ws_2, master, type_, 1501, sheet_password)
        protect_and_mark_table(ws_3, master, type_, 201, sheet_password)
        finalize_form_workbook(wb, sheet_password)
        save_excel_compatible(wb, EXCEL_TEMPLATES / f'form_{type_}.xlsx')
    master.workbook.close()


# Create templates from master config excel

def create_templates(excel_template=template_master):

    configure_section_rows(excel_template)
    EXCEL_TEMPLATES.mkdir(parents=True, exist_ok=True)

    print('Creating templates for:')

    for type_ in types:
        print(type_)

        # Open excel template, define sheets
        warnings.simplefilter(action='ignore')
        wb = load_workbook(filename=excel_template)
        ws = wb["Metadaten"]

        # Spalten für Schema Typ 
        for cells in ws.iter_rows(min_row=1, max_row=1, values_only=False):
            for cell in cells:
                if cell.value == f'{type_}':
                    col_field_exists = split_coords(cell.coordinate)[0]
                    #print(col_field_exists)
                    break

        for cells in ws.iter_rows(min_row=1, max_row=1, values_only=False):
            for cell in cells:
                if cell.value == 'Format':
                    col_format = split_coords(cell.coordinate)[0]
                    col_format_nr = cell.column
                    #print(col_dropdown)
                    break

        for cells in ws.iter_rows(min_row=1, max_row=1, values_only=False):
            for cell in cells:
                col_end_nr = cell.column

        # Delete rows not part of schema
        del_rows = []
        del_cols = []
        for row in range(first_line_md, first_line_dv):
            exists = f'{col_field_exists}{str(row)}'
            if ws[exists].value != 'x' or str(ws.cell(row, 1).value or '').strip() == 'Version':
                del_rows.append(row)
     
        # Delete config rows and cols
        for row in range(first_line_dv, last_line_dd + 1):
            del_rows.append(row)
        for col in range (col_format_nr, col_end_nr + 1):
            del_cols.append(col)

        #print('FINAL rows to delete:')
        #print(del_rows)
        #print('FINAL cols to delete:')
        #print(del_cols)

        for row_idx in sorted(del_rows, reverse=True):
            ws.delete_rows(row_idx)
        # openpyxl.delete_rows moves cells, but does not update the sqref
        # ranges of existing data validations (including input messages).
        adjust_validations_after_delete(ws, del_rows)
        adjust_merged_cells_after_delete(ws, del_rows)

        for col_idx in sorted(del_cols, reverse=True):
            ws.delete_cols(col_idx)
        
        # Save Excel
        save_excel_compatible(wb, EXCEL_TEMPLATES / f'template_{type_}.xlsx')


def main(argv=None):
    parser = argparse.ArgumentParser(description='Create protected Excel forms from the master config')
    parser.add_argument('config_file', nargs='?', help='Harvester JSON with sheet_protection')
    parser.add_argument('--password', '--sheet-protection', dest='password',
                        help='Sheet protection password (alternative to config_file)')
    args = parser.parse_args(argv)
    if args.config_file and args.password is not None:
        parser.error('Specify either config_file or --password, not both')
    password = (args.password if args.password is not None
                else read_sheet_password(args.config_file))
    if not password:
        parser.error('The sheet protection password must not be empty')
    create_empty_forms(sheet_password=password)


if __name__ == "__main__":
    main()
