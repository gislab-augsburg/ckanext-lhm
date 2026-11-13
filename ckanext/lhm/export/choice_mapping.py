"""Translate current master dropdowns and input aliases from issued forms."""

from collections import defaultdict

from openpyxl import load_workbook
from openpyxl.utils.cell import range_boundaries


class ChoiceMap:
    def __init__(self, master_file, schema=None, legacy=False):
        book = load_workbook(master_file, data_only=True)
        try:
            metadata = book["Metadaten"]
            lists = book["Wertelisten"]
            translations = book["CKAN_Werte"]
            expected = ["Name", "Anzeige", "CKAN_Wert", "Importalias"]
            if [translations.cell(1, column).value for column in range(1, 5)] != expected:
                raise ValueError("CKAN_Werte requires the columns Name, Anzeige, CKAN_Wert, Importalias")
            headers = {str(cell.value): cell.column - 1 for cell in metadata[1]
                       if cell.value is not None}
            schemas = ([schema] if schema is not None else
                       [str(row[0]) for row in book["Schemata"].iter_rows(
                           min_row=2, values_only=True) if row[0]])

            allowed = defaultdict(set)
            for selected_schema in schemas:
                if selected_schema not in headers or selected_schema + "_w" not in headers:
                    raise ValueError(f"Dropdown columns for {selected_schema} are missing")
                for row in metadata.iter_rows(min_row=2):
                    if row[headers[selected_schema]].value != "x":
                        continue
                    name = row[headers["Name"]].value
                    address = row[headers[selected_schema + "_w"]].value
                    if not name or not address:
                        continue
                    first_col, first_row, last_col, last_row = range_boundaries(str(address))
                    if first_col != last_col or first_row < 2:
                        raise ValueError(f"Invalid dropdown range for {name}: {address}")
                    for index in range(first_row, last_row + 1):
                        display = lists.cell(index, first_col).value
                        if display not in (None, ""):
                            allowed[str(name)].add(display)

            self.active = defaultdict(dict)
            self.forward = defaultdict(dict)
            self.reverse = defaultdict(dict)
            self.legacy = legacy
            mapped = {}
            aliases = []
            for name, display, code, import_alias in translations.iter_rows(
                    min_row=2, max_col=4, values_only=True):
                if name is None or display is None:
                    continue
                name = str(name)
                key = (name, display)
                if key in mapped:
                    raise ValueError(f"Duplicate CKAN mapping for {name}: {display!r}")
                if code in (None, ""):
                    raise ValueError(f"CKAN value for {name}: {display!r} is missing")
                if import_alias not in (None, "", "x"):
                    raise ValueError(f"Importalias for {name}: {display!r} must be x or empty")
                mapped[key] = code
                if display in allowed[name]:
                    if import_alias == "x":
                        raise ValueError(f"Current dropdown value is marked as Importalias: {name}: {display!r}")
                    previous = self.reverse[name].get(code)
                    if previous is not None and previous != display:
                        raise ValueError(f"CKAN value {code!r} has multiple current display values for {name}")
                    self.active[name][display] = code
                    self.forward[name][display] = code
                    self.reverse[name][code] = display
                elif import_alias == "x":
                    self.forward[name][display] = code
                    aliases.append((name, display, code))

            for name, display, code in aliases:
                if code not in self.reverse[name]:
                    raise ValueError(f"Importalias {name}: {display!r} has no current CKAN value {code!r}")

            self.unmapped = {name: values - self.active[name].keys()
                             for name, values in allowed.items()
                             if values - self.active[name].keys()}
        finally:
            book.close()

    def to_ckan(self, name, display):
        if display in (None, ""):
            return display
        if display in self.active[name]:
            return self.active[name][display]
        if display in self.forward[name]:
            return self.forward[name][display]
        raise ValueError(f"Unknown dropdown value for {name}: {display!r}")

    def to_display(self, name, value):
        if value in (None, ""):
            return value
        if value not in self.reverse[name]:
            raise ValueError(f"CKAN value {value!r} for {name} is missing from CKAN_Werte")
        return self.reverse[name][value]
