"""Write stable-name values into the current protected Excel form."""

from pathlib import Path

from openpyxl import load_workbook

try:
    from .field_mapping import TABLES, field_rows, table_columns
    from .templates_from_master import finalize_form_workbook, save_excel_compatible
    from .schema_extras import SchemaExtras
except ImportError:
    from field_mapping import TABLES, field_rows, table_columns
    from templates_from_master import finalize_form_workbook, save_excel_compatible
    from schema_extras import SchemaExtras


def write_form(form_file, output_file, master, schema, values, tables,
               sheet_password):
    workbook = load_workbook(form_file)
    metadata = workbook["Metadaten"]
    rows = field_rows(metadata, master, schema)
    extra_rules = SchemaExtras(master).for_schema(schema)
    fixed = {extra.name for extra in extra_rules if extra.fixed}
    derived = {extra.name for extra in extra_rules if extra.derivation}
    value_col = next((cell.column for cell in metadata[1]
                      if str(cell.value or "").strip() == "Wert"), None)
    if value_col is None:
        raise ValueError("Value column is missing from the form")

    for name, spec in master.fields(schema).items():
        if name not in rows:
            raise ValueError(f"Field {name!r} is missing from form {form_file}")
        if name in fixed:
            # The form always shows the configured fixed value, even if an
            # older CKAN package still contains a different value.
            continue
        # Some openpyxl versions reset allowBlank while loading a workbook.
        # Restore it from the authoritative Pflichtfeld setting before export.
        blank_allowed = not spec.required or spec.format.startswith("multi-")
        for offset in range(spec.width):
            address = metadata.cell(rows[name], value_col + offset).coordinate
            for validation in metadata.data_validations.dataValidation:
                if address in validation:
                    validation.allow_blank = blank_allowed
        value = values.get(name)
        if value is None:
            if name in derived:
                # A filled export shows the actual CKAN value (also when
                # absent); the precompiled comparison rule marks divergence.
                metadata.cell(rows[name], value_col).value = None
            continue
        parts = value if isinstance(value, (list, tuple)) else [value]
        if len(parts) > spec.width and any(part not in (None, "")
                                           for part in parts[spec.width:]):
            raise ValueError(f"{name}: more values than form columns")
        if not spec.format.startswith("multi-") and len(parts) > 1:
            raise ValueError(f"{name}: multiple values in a single-value field")
        for offset, part in enumerate(parts[:spec.width]):
            metadata.cell(rows[name], value_col + offset).value = part

    for sheet_name in TABLES:
        sheet = workbook[sheet_name]
        keys = table_columns(sheet, master)
        records = tables.get(sheet_name) or []
        for row_number, record in enumerate(records, start=2):
            if row_number > sheet.max_row:
                sheet_label = {"Datenverzeichnis": "Data directory",
                               "Katalogwerte": "Catalog values",
                               "Dienste und Dokumente": "Services and documents"}[sheet_name]
                raise ValueError(f"Too many rows in {sheet_label}")
            for column, key in keys.items():
                if key in record:
                    sheet.cell(row_number, column).value = record[key]

    output_file = Path(output_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    finalize_form_workbook(workbook, sheet_password)
    save_excel_compatible(workbook, output_file)
