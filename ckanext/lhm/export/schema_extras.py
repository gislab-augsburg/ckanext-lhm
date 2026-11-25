"""Schema-specific form rules shared by generation, export and import.

Rules are keyed by the CKAN field name.  Only the documented JSON operators
are accepted, so Excel and Python always check the same condition.
"""

from __future__ import annotations

from dataclasses import dataclass
from copy import copy
import json
import warnings

from openpyxl import load_workbook
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

try:
    from .field_mapping import field_rows, schema_status
except ImportError:
    from field_mapping import field_rows, schema_status


GREY = PatternFill(fill_type="solid", fgColor="FFD9D9D9")
GREY_RULE = PatternFill(fill_type="solid", bgColor="FFD9D9D9")
GREY_FONT = Font(color="FF757171")
RED_RULE = PatternFill(fill_type="solid", bgColor="FFFF0000")
RED_FONT = Font(color="FF000000")
HEADERS = ("Schema", "Blatt", "Name", "Info Titel", "Info Text",
           "Festwert", "Bedingte Ableitung", "Validierung",
           "Festwert aktiv", "Bearbeitbar wenn", "Ableitungsabweichung")
CONDITIONAL_REQUIRED = "Pflichtfeld wenn"


def _json(value, context):
    if value in (None, ""):
        return None
    try:
        result = json.loads(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{context}: expected a JSON rule") from exc
    if not isinstance(result, dict):
        raise ValueError(f"{context}: rule must be a JSON object")
    return result


def _ref(rule, master, schema, context):
    source = rule.get("source")
    if not isinstance(source, dict) or set(source) != {"Blatt", "Name"}:
        raise ValueError(f"{context}: source must contain Blatt and Name")
    if source["Blatt"] != "Metadaten" or source["Name"] not in master.fields(schema):
        raise ValueError(f"{context}: unknown metadata source {source!r}")
    if master.fields(schema)[source["Name"]].width != 1:
        raise ValueError(f"{context}: conditional source must have one value cell")
    return source["Name"]


@dataclass(frozen=True)
class Extra:
    schema: str
    sheet: str
    name: str
    title: str | None
    text: str | None
    fixed: bool
    fixed_value: object
    derivation: dict | None
    validation: dict | None
    editable_if: dict | None
    required_if: dict | None
    mismatch: str


class SchemaExtras:
    def __init__(self, master):
        self.master = master
        self.rules = {}
        if "Schema_Extras" not in master.workbook:
            return
        sheet = master.workbook["Schema_Extras"]
        header_names = [str(cell.value).strip() for cell in sheet[1]
                        if cell.value not in (None, "")]
        if len(header_names) != len(set(header_names)):
            raise ValueError("Schema_Extras has duplicate column headings")
        columns = {str(cell.value).strip(): cell.column - 1 for cell in sheet[1]
                   if cell.value not in (None, "")}
        missing = set(HEADERS) - columns.keys()
        if missing:
            raise ValueError(f"Schema_Extras is missing columns: {', '.join(sorted(missing))}")
        for number, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
            if not any(value is not None for value in row):
                continue
            def value(header):
                position = columns.get(header)
                return row[position] if position is not None else None
            schema, tab, name = (value(header) for header in HEADERS[:3])
            title, text = value("Info Titel"), value("Info Text")
            fixed_value, deriv = value("Festwert"), value("Bedingte Ableitung")
            valid, active = value("Validierung"), value("Festwert aktiv")
            enabled, mismatch = value("Bearbeitbar wenn"), value("Ableitungsabweichung")
            required = value(CONDITIONAL_REQUIRED)
            context = f"Schema_Extras row {number} ({schema}/{tab}/{name})"
            if schema not in master.schemas:
                raise ValueError(f"{context}: unknown schema")
            if tab != "Metadaten":
                raise ValueError(f"{context}: only Metadaten rules are currently supported")
            if name not in master.fields(schema):
                raise ValueError(f"{context}: field is not in the schema")
            key = (schema, tab, name)
            if key in self.rules:
                raise ValueError(f"{context}: duplicate rule for field")
            if active not in (None, "", "x"):
                raise ValueError(f"{context}: Festwert aktiv must be x or empty")
            if fixed_value is not None and active != "x":
                raise ValueError(f"{context}: Festwert needs Festwert aktiv=x")
            if mismatch not in (None, "", "error", "warn"):
                raise ValueError(f"{context}: Ableitungsabweichung must be error or warn")
            derivation = _json(deriv, context + " Bedingte Ableitung")
            validation = _json(valid, context + " Validierung")
            editable_if = _json(enabled, context + " Bearbeitbar wenn")
            required_if = _json(required, context + " Pflichtfeld wenn")
            if active == "x" and (derivation or editable_if):
                raise ValueError(f"{context}: a fixed value cannot also be derived or conditional")
            if active == "x" and fixed_value in (None, "") and master.fields(schema)[name].required:
                raise ValueError(f"{context}: a required field cannot have an empty fixed value")
            if derivation:
                if derivation.get("op") not in ("slug", "copy"):
                    raise ValueError(f"{context}: unknown derivation operator")
                _ref(derivation, master, schema, context)
            if validation:
                if validation.get("op") not in ("allowed_chars_and_length", "max_length"):
                    raise ValueError(f"{context}: unknown validation operator")
                if validation["op"] == "allowed_chars_and_length":
                    if not isinstance(validation.get("allowed"), str) or not validation["allowed"]:
                        raise ValueError(f"{context}: allowed must be a nonempty string")
                    replacements = validation.get("replacements", {})
                    if not isinstance(replacements, dict) or any(
                            not isinstance(k, str) or not isinstance(v, str)
                            for k, v in replacements.items()):
                        raise ValueError(f"{context}: invalid replacements")
                    limit = validation.get("max_after_replacements")
                else:
                    limit = validation.get("max_length")
                if not isinstance(limit, int) or limit < 1:
                    raise ValueError(f"{context}: length limit must be positive")
                if active == "x" and not valid_python(validation, fixed_value,
                                                        master.fields(schema)[name].required):
                    raise ValueError(f"{context}: fixed value fails its validation")
            for heading, condition in (("Bearbeitbar wenn", editable_if),
                                       (CONDITIONAL_REQUIRED, required_if)):
                if condition:
                    if set(condition) != {"source", "equals"}:
                        raise ValueError(f"{context}: {heading} needs source and equals")
                    _ref(condition, master, schema, context)
            if required_if and master.fields(schema)[name].required:
                raise ValueError(f"{context}: an unconditional required field cannot use Pflichtfeld wenn")
            self.rules[key] = Extra(schema, tab, name, title, text, active == "x",
                                    fixed_value, derivation, validation, editable_if,
                                    required_if,
                                    mismatch or "error")
        for schema in master.schemas:
            for spec in master.fields(schema).values():
                status = schema_status(master.ws[spec.source_row],
                                       master.headers[schema], schema)
                if status == "b" and not (
                        self.rules.get((schema, "Metadaten", spec.name))
                        and self.rules[(schema, "Metadaten", spec.name)].required_if):
                    raise ValueError(f"{schema}/{spec.name}: b requires a Pflichtfeld wenn rule")

    def for_schema(self, schema):
        return [rule for (key_schema, _, _), rule in self.rules.items()
                if key_schema == schema]


def _quote(value):
    return '"' + str(value).replace('"', '""') + '"'


def _substitute(expression, replacements):
    for old, new in replacements.items():
        expression = f"SUBSTITUTE({expression},{_quote(old)},{_quote(new)})"
    return expression


def _condition_excel(rule, rows):
    source = "B" + str(rows[rule["source"]["Name"]])
    return f'{source}={_quote(rule["equals"])}'


def _condition_python(rule, values, master, schema, choices=None):
    source = rule["source"]["Name"]
    actual = values.get(source)
    expected = rule["equals"]
    if actual == expected:
        return True
    if choices is not None and actual not in (None, ""):
        source_spec = master.fields(schema)[source]
        if "select" in source_spec.format:
            return choices.to_ckan(source, actual) == choices.to_ckan(source, expected)
    return False


def _grey_cell(cell):
    cell.fill = GREY
    font = copy(cell.font)
    font.color = GREY_FONT.color
    cell.font = font


def derived_excel(rule, rows):
    source = "B" + str(rows[rule["source"]["Name"]])
    if rule["op"] == "copy":
        return f'IF({source}="","",{source})'
    if rule["op"] == "slug":
        converted = _substitute(source, {"Ä": "AE", "Ö": "OE", "Ü": "UE",
                                         "ä": "ae", "ö": "oe", "ü": "ue",
                                         "ß": "ss", " ": "_", "-": "_"})
        return f'IF({source}="","",LOWER({converted}))'
    raise ValueError(f"Unknown derivation operator: {rule['op']}")


def derived_python(rule, values):
    source = values.get(rule["source"]["Name"])
    if source in (None, ""):
        return ""
    if rule["op"] == "copy":
        return source
    if rule["op"] == "slug":
        converted = str(source)
        for old, new in {"Ä": "AE", "Ö": "OE", "Ü": "UE",
                         "ä": "ae", "ö": "oe", "ü": "ue",
                         "ß": "ss", " ": "_", "-": "_"}.items():
            converted = converted.replace(old, new)
        return converted.lower()
    raise ValueError(f"Unknown derivation operator: {rule['op']}")


def valid_excel(rule, address, required):
    op = rule["op"]
    if op == "max_length":
        check = f'LEN({address})<={rule["max_length"]}'
    elif op == "allowed_chars_and_length":
        allowed = _quote(rule["allowed"])
        chars = (f'SUMPRODUCT(--ISERROR(FIND(MID({address},'
                 f'ROW(INDIRECT("1:"&LEN({address}))),1),{allowed})))=0')
        transformed = _substitute(address, rule.get("replacements", {}))
        check = f'AND({chars},LEN({transformed})<={rule["max_after_replacements"]})'
    else:
        raise ValueError(f"Unknown validation operator: {op}")
    return f'IF({address}="",{"FALSE" if required else "TRUE"},{check})'


def valid_python(rule, value, required):
    if value in (None, ""):
        return not required
    text = str(value)
    if rule["op"] == "max_length":
        return len(text) <= rule["max_length"]
    if rule["op"] == "allowed_chars_and_length":
        if any(char not in rule["allowed"] for char in text):
            return False
        for old, new in rule.get("replacements", {}).items():
            text = text.replace(old, new)
        return len(text) <= rule["max_after_replacements"]
    raise ValueError(f"Unknown validation operator: {rule['op']}")


def apply_to_form(book, master, schema, row_numbers, isolate_validation_cell,
                  set_locked):
    """Compile master rules into ordinary Excel formulas and formatting."""
    extras = SchemaExtras(master)
    ws = book["Metadaten"]
    choices = None
    for extra in extras.for_schema(schema):
        if extra.name not in row_numbers:
            raise ValueError(f"{schema}/{extra.name}: field missing from generated form")
        spec = master.fields(schema)[extra.name]
        address = "B" + str(row_numbers[extra.name])
        cell = ws[address]
        dv = next((candidate for candidate in ws.data_validations.dataValidation
                   if address in candidate), None)
        if extra.validation:
            if spec.width != 1:
                raise ValueError(f"{schema}/{extra.name}: custom validation needs one value cell")
            if dv is None:
                dv = DataValidation(type="custom")
                dv.add(address)
                ws.add_data_validation(dv)
            else:
                dv = isolate_validation_cell(ws, dv, address)
            dv.type = "custom"
            dv.operator = None
            check_formula = valid_excel(extra.validation, address, spec.required)
            dv.formula1 = "=" + check_formula
            dv.allow_blank = not spec.required
            dv.showErrorMessage = True
            dv.errorTitle = "Ungültiger Eintrag"
            dv.error = "Der Wert entspricht nicht der konfigurierten Prüfung."
            ws.conditional_formatting.add(address, FormulaRule(
                formula=[f'NOT(IFERROR({check_formula},FALSE))'],
                fill=RED_RULE, font=RED_FONT))
        if extra.title is not None or extra.text is not None:
            if dv is None:
                dv = DataValidation(type="custom", formula1="=TRUE")
                dv.add(address)
                ws.add_data_validation(dv)
            else:
                dv = isolate_validation_cell(ws, dv, address)
            if extra.title is not None:
                dv.promptTitle = str(extra.title)
            if extra.text is not None:
                dv.prompt = str(extra.text)
            dv.showInputMessage = True
        if extra.fixed:
            if spec.width != 1:
                raise ValueError(f"{schema}/{extra.name}: fixed multi fields are unsupported")
            if "select" in spec.format and extra.fixed_value not in (None, ""):
                if choices is None:
                    try:
                        from .choice_mapping import ChoiceMap
                    except ImportError:
                        from choice_mapping import ChoiceMap
                    choices = ChoiceMap(master.filename, schema)
                if extra.fixed_value not in choices.active[extra.name]:
                    raise ValueError(f"{schema}/{extra.name}: fixed value is not in current dropdown")
            cell.value = extra.fixed_value
            _grey_cell(cell)
            set_locked(cell, True)
        if extra.derivation:
            if spec.width != 1:
                raise ValueError(f"{schema}/{extra.name}: derived multi fields are unsupported")
            expected = derived_excel(extra.derivation, row_numbers)
            cell.value = "=" + expected
            _grey_cell(cell)
            set_locked(cell, True)
            ws.conditional_formatting.add(address, FormulaRule(
                formula=[f'IFERROR({address}<>{expected},TRUE)'],
                fill=RED_RULE, font=RED_FONT))
        if extra.editable_if:
            source_address = "B" + str(row_numbers[extra.editable_if["source"]["Name"]])
            disabled = f'{source_address}<>{_quote(extra.editable_if["equals"])}'
            for offset in range(spec.width):
                target = ws.cell(cell.row, 2 + offset).coordinate
                ws.conditional_formatting.add(target, FormulaRule(
                    formula=[f'AND({disabled},{target}<>"")'],
                    fill=RED_RULE, font=RED_FONT))
                ws.conditional_formatting.add(target, FormulaRule(
                    formula=[f'AND({disabled},{target}="")'],
                    fill=GREY_RULE, font=GREY_FONT))
        if extra.required_if:
            active = _condition_excel(extra.required_if, row_numbers)
            if spec.width == 1:
                empty = f'{address}=""'
            else:
                end = ws.cell(cell.row, 1 + spec.width).coordinate
                empty = f'COUNTIF(${address[0]}{cell.row}:${end[0]}{cell.row},"<>")=0'
            ws.conditional_formatting.add(address, FormulaRule(
                formula=[f'AND({active},{empty})'], fill=RED_RULE))


def hydrate_formulas(filename, master, schema, values):
    """openpyxl cannot calculate formula caches; derive untouched formula cells."""
    extras = SchemaExtras(master)
    formulas = [extra for extra in extras.for_schema(schema) if extra.derivation]
    if not formulas:
        return
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message=r"^Data Validation extension is not supported and will be removed$",
            category=UserWarning,
            module=r"openpyxl\.worksheet\._reader",
        )
        book = load_workbook(filename, data_only=False, read_only=False)
    try:
        rows = field_rows(book["Metadaten"], master, schema)
        for extra in formulas:
            if extra.name not in rows:
                continue
            raw = book["Metadaten"].cell(rows[extra.name], 2).value
            if isinstance(raw, str) and raw.startswith("="):
                values[extra.name] = derived_python(extra.derivation, values)
    finally:
        book.close()


def validate_input(master, schema, values, choices=None):
    """Reject pasted invalid data before any CKAN write."""
    for extra in SchemaExtras(master).for_schema(schema):
        value = values.get(extra.name)
        if extra.fixed and value != extra.fixed_value and not (
                value in (None, "") and extra.fixed_value in (None, "")):
            raise ValueError(f"{extra.name}: expected fixed value {extra.fixed_value!r}, got {value!r}")
        if extra.validation:
            required = master.fields(schema)[extra.name].required
            if not valid_python(extra.validation, value, required):
                raise ValueError(f"{extra.name}: value {value!r} violates Schema_Extras validation")
        if extra.editable_if:
            source = extra.editable_if["source"]["Name"]
            expected = extra.editable_if["equals"]
            if not _condition_python(extra.editable_if, values, master, schema, choices):
                parts = value if isinstance(value, (list, tuple)) else [value]
                if any(part not in (None, "") for part in parts):
                    raise ValueError(f"{extra.name}: value is only allowed when "
                                     f"{source}={expected!r}")
        if extra.required_if and _condition_python(
                extra.required_if, values, master, schema, choices):
            parts = value if isinstance(value, (list, tuple)) else [value]
            if not any(part not in (None, "") for part in parts):
                source = extra.required_if["source"]["Name"]
                raise ValueError(
                    f"{extra.name}: required when "
                    f"{source}={extra.required_if['equals']!r}"
                )
        if extra.derivation:
            expected = derived_python(extra.derivation, values)
            if value != expected:
                detail = f"{extra.name}: value {value!r} differs from derived value {expected!r}"
                if extra.mismatch == "warn":
                    warnings.warn(detail, UserWarning)
                else:
                    raise ValueError(detail)
