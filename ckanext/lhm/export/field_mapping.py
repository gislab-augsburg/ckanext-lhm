"""Field identity for current and 1.3.6/1.3.7 Excel forms."""
from __future__ import annotations
from base64 import b32decode, b32encode
from dataclasses import dataclass
from pathlib import Path
import re
import unicodedata
from openpyxl import load_workbook
from openpyxl.utils.cell import coordinate_from_string
from openpyxl.workbook.defined_name import DefinedName

METADATA = "Metadaten"
TABLES = ("Datenverzeichnis", "Katalogwerte", "Dienste und Dokumente")
FIELD_NAME_PREFIX = "_metadata_field_"

def bind_field_name(book, name, coordinate):
    """Store a stable field identity without a visible Name column."""
    encoded = b32encode(name.encode("utf-8")).decode("ascii").rstrip("=")
    defined = DefinedName(
        name=FIELD_NAME_PREFIX + encoded,
        attr_text=f"'Metadaten'!${coordinate[0]}${coordinate[1:]}",
        hidden=True,
    )
    if hasattr(book.defined_names, "add"):
        book.defined_names.add(defined)
    else:  # openpyxl 3.0.x
        book.defined_names.append(defined)

def embedded_field_rows(book):
    """Return stable names and positions saved as hidden workbook names."""
    names = (book.defined_names.values() if hasattr(book.defined_names, "values")
             else book.defined_names.definedName)
    result = {}
    for defined in names:
        if not defined.name.startswith(FIELD_NAME_PREFIX):
            continue
        encoded = defined.name[len(FIELD_NAME_PREFIX):]
        name = b32decode(encoded + "=" * (-len(encoded) % 8)).decode("utf-8")
        destinations = list(defined.destinations)
        if len(destinations) != 1 or destinations[0][0] != METADATA:
            raise ValueError(f"Invalid field reference for {name!r}")
        column, row = coordinate_from_string(destinations[0][1])
        if column != "B" or name in result:
            raise ValueError(f"Invalid field position for {name!r}")
        result[name] = row
    return result

def normalized_label(value):
    value = unicodedata.normalize("NFKD", str(value or "")).casefold()
    value = "".join(c for c in value if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", value.replace("*", "")).strip()

def headers(sheet):
    return {str(c.value).strip(): c.column for c in sheet[1] if c.value is not None}

@dataclass(frozen=True)
class FieldSpec:
    name: str
    label: str
    format: str
    required: bool
    source_row: int
    dropdown: str | None
    @property
    def width(self):
        if not self.format.startswith("multi-"):
            return 1
        suffix = self.format.rsplit("-", 1)[-1]
        return int(suffix) if suffix.isdigit() else 10

class MasterConfig:
    def __init__(self, filename):
        self.filename = Path(filename)
        self.workbook = load_workbook(filename, data_only=True)
        self.ws = self.workbook[METADATA]
        self.headers = headers(self.ws)
        self.schemas = {str(r[0]): str(r[1]) for r in self.workbook["Schemata"].iter_rows(min_row=2, values_only=True) if r[0] and r[1]}
        self.legacy = {(str(s), normalized_label(l)): str(n or "") for s,l,n in self.workbook["Legacy_136_137"].iter_rows(min_row=2, values_only=True) if s and l}
        self._fields = {}
    def fields(self, schema):
        if schema not in self.schemas:
            raise ValueError(f"Unknown schema: {schema}")
        if schema not in self._fields:
            h = self.headers
            result = {}
            for row in self.ws.iter_rows(min_row=2):
                label = row[h["Feld"]-1].value
                if str(label or "").startswith("Datenverzeichnis -"):
                    break
                if row[h[schema]-1].value != "x":
                    continue
                name = row[h["Name"]-1].value
                if not name or normalized_label(label) == "version":
                    continue
                name = str(name)
                if name in result:
                    raise ValueError(f"Duplicate field name in {schema}: {name}")
                result[name] = FieldSpec(name, str(label), str(row[h["Format"]-1].value or ""), row[h["Pflichtfeld"]-1].value == "x", row[0].row, row[h[schema+"_w"]-1].value if schema+"_w" in h else None)
            self._fields[schema] = result
        return self._fields[schema]
    def table_fields(self, sheet_name):
        prefix = sheet_name + " -"
        col = self.headers["Name"]-1
        return tuple(str(row[col].value) for row in self.ws.iter_rows(min_row=2) if str(row[0].value or "").startswith(prefix) and row[col].value)
    def table_specs(self, sheet_name, schema=None):
        prefix = sheet_name + " -"
        h = self.headers
        return {str(row[h["Name"]-1].value): FieldSpec(
            str(row[h["Name"]-1].value), str(row[h["Feld"]-1].value),
            str(row[h["Format"]-1].value or ""),
            row[h["Pflichtfeld"]-1].value == "x", row[0].row,
            row[h[schema + "_w"]-1].value if schema and schema + "_w" in h else None)
            for row in self.ws.iter_rows(min_row=2)
            if str(row[0].value or "").startswith(prefix) and row[h["Name"]-1].value
            and (schema is None or row[h[schema]-1].value == "x")}
    def schema_for_type(self, ckan_type):
        return next((key for key, value in self.schemas.items() if value == ckan_type), None)

def configured_schema(excel_template, master):
    """Treat the configured template filename as an explicit schema filter."""
    filename = Path(str(excel_template).replace("\\", "/")).stem
    for prefix in ("template_", "form_"):
        if filename.startswith(prefix):
            filename = filename[len(prefix):]
            break
    if filename not in master.schemas:
        raise ValueError(f"Unknown configured schema: {filename!r}")
    return filename

def form_version(sheet, stable_rows=None):
    h = headers(sheet)
    if "Name" in h or stable_rows:
        return ""
    for row in sheet.iter_rows(min_row=2):
        if normalized_label(row[0].value) == "version":
            v = str(row[h["Wert"]-1].value or "").strip().rstrip(".")
            if v in ("1.3.6", "1.3.7"):
                return v
            raise ValueError(f"Unsupported legacy version: {v!r}")
    raise ValueError("Name column and version information are missing")

def value_columns(sheet):
    result = []
    for label, column in headers(sheet).items():
        if label == "Wert":
            result.append((1, column))
        else:
            match = re.fullmatch(r"Wert\s*(\d+)", label)
            if match:
                result.append((int(match.group(1)), column))
    return [column for _, column in sorted(result)]

def table_columns(sheet, master):
    section = sheet.title
    labels = {
        normalized_label(str(row[0].value).split(" - ", 1)[-1]):
        str(row[master.headers["Name"]-1].value)
        for row in master.ws.iter_rows(min_row=2)
        if str(row[0].value or "").startswith(section + " -") and
        row[master.headers["Name"]-1].value
    }
    return {cell.column: master.legacy.get((section, normalized_label(cell.value)))
            or labels.get(normalized_label(cell.value)) for cell in sheet[1]}

def table_value(value):
    """Treat text that looks blank in Excel as an empty table cell."""
    if isinstance(value, str):
        visible = value.strip().strip("\u200b\u200c\u200d\ufeff").strip()
        return value if visible else None
    return value

def read_form(filename, master, schema=None):
    book = load_workbook(filename, data_only=True)
    sheet = book[METADATA]
    h = headers(sheet)
    stable_rows = embedded_field_rows(book)
    names_by_row = {row: name for name, row in stable_rows.items()}
    version = form_version(sheet, stable_rows)
    cols = value_columns(sheet)
    name_col = h.get("Name")
    if schema is None:
        for row in sheet.iter_rows(min_row=2):
            label = normalized_label(row[h["Feld"]-1].value)
            name = names_by_row.get(row[0].row) or (row[name_col-1].value if name_col else master.legacy.get((METADATA, label)))
            if name == "type":
                display = row[cols[0]-1].value
                schema = next((key for key, typ in master.schemas.items() if normalized_label(display) in (normalized_label(key), normalized_label(typ))), None)
                break
    if schema not in master.schemas:
        raise ValueError("Schema cannot be identified; provide schema=")
    fields = master.fields(schema)
    values = {}
    for row in sheet.iter_rows(min_row=2):
        label = normalized_label(row[h["Feld"]-1].value)
        name = names_by_row.get(row[0].row) or (row[name_col-1].value if name_col else master.legacy.get((METADATA, label)))
        if not name or name not in fields:
            continue
        spec = fields[name]
        parts = [row[col-1].value for col in cols[:spec.width]]
        values[name] = parts if spec.format.startswith("multi-") else parts[0]
    tables = {}
    for sheet_name in TABLES:
        tab = book[sheet_name]
        keys = table_columns(tab, master)
        records = []
        for row in tab.iter_rows(min_row=2, values_only=True):
            record = {key: table_value(row[col-1]) for col, key in keys.items() if key}
            # _id is assigned by the CKAN datastore. It may remain when the
            # three editable catalog cells have been cleared in Excel.
            active_values = (value for key, value in record.items()
                             if sheet_name != "Katalogwerte" or key != "kat_id")
            if any(value is not None for value in active_values):
                records.append(record)
        tables[sheet_name] = records
    book.close()
    return schema, version, values, tables

def field_rows(sheet, master, schema):
    stable = embedded_field_rows(sheet.parent)
    if stable:
        return {name: row for name, row in stable.items() if name in master.fields(schema)}
    col = headers(sheet).get("Name")
    if not col:
        raise ValueError("Current template has no Name column")
    fields = master.fields(schema)
    return {row[col-1].value: row[0].row for row in sheet.iter_rows(min_row=2) if row[col-1].value in fields}
