"""Translate stable master field names to and from CKAN package values."""

from __future__ import annotations

import json

TAGS = "tags.{j}.name"
TOPICS = "groups.topic.{k}.title"
MAIN = "groups.main.title"
DEPARTMENT = "groups.department.title"
OWNER = "organization.title"
TYPE = "type"
USAGE_KEY = "nutzungshinweise.{j}.stichwort"
USAGE_TEXT = "nutzungshinweise.{j}.hinweise"
OPTIONS = "nutzungsoptionen_bei_einschraenkungen"
SPECIAL = {TAGS, TOPICS, MAIN, DEPARTMENT, OWNER, TYPE, USAGE_KEY,
           USAGE_TEXT, OPTIONS}


def _nonempty(value):
    return value is not None and value != ""


def _as_list(value):
    if value is None or value == "":
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    if isinstance(value, str) and value.startswith("{") and value.endswith("}"):
        return [item.strip().strip("'\"") for item in value[1:-1].split(",")
                if item.strip()]
    if isinstance(value, str) and value.startswith("["):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return parsed
        except ValueError:
            pass
    return [value]


def _json_value(value):
    if isinstance(value, str) and value.startswith(("{", "[")):
        try:
            return json.loads(value)
        except ValueError:
            return value
    return value


def _package_value(package, name):
    if name in package:
        return package[name]
    extras = package.get("extras") or []
    for extra in extras:
        if extra.get("key") == name:
            return extra.get("value")
    if "." not in name:
        return None
    root, *parts = name.split(".")
    value = _json_value(package.get(root))
    for part in parts:
        value = value.get(part) if isinstance(value, dict) else None
    return value


def _choice_to_ckan(choices, name, value, is_select):
    if not is_select or not _nonempty(value):
        return value
    return choices.to_ckan(name, value)


def _choice_to_display(choices, name, value, is_select):
    if not is_select or not _nonempty(value):
        return value
    try:
        return choices.to_display(name, value)
    except (ValueError, TypeError):
        # Show an unknown CKAN code in Excel, where the validation marks it.
        return value


def form_to_dataset(values, schema, version, master, choices, package_name):
    """Build CKAN metadata without referring to workbook positions."""
    fields = master.fields(schema)
    result = {"name": package_name}
    nested = {}
    for name, spec in fields.items():
        if name not in values:
            if not version and spec.required:
                raise ValueError(f"Required field {name!r} is missing")
            continue
        value = values[name]
        parts = _as_list(value) if spec.format.startswith("multi-") else [value]
        if spec.required and not any(_nonempty(part) for part in parts):
            raise ValueError(f"Required field {name!r} is empty")
        if name in SPECIAL:
            continue
        is_select = "select" in spec.format
        converted = [_choice_to_ckan(choices, name, part, is_select)
                     for part in parts if _nonempty(part)]
        value = converted if spec.format.startswith("multi-") else (
            converted[0] if converted else None)
        if "." in name:
            root, subkey = name.split(".", 1)
            # The composite display snippet calls |length on every subfield.
            # JSON null raises there; an empty Excel cell must become "".
            nested.setdefault(root, {})[subkey] = "" if value is None else value
        else:
            result[name] = value

    if TAGS in values:
        result["tag_string"] = ", ".join(str(tag) for tag in
                                           _as_list(values[TAGS]) if _nonempty(tag))

    group_codes = []
    for name in (MAIN, TOPICS, DEPARTMENT):
        if name not in values:
            continue
        for display in _as_list(values[name]):
            if _nonempty(display):
                code = choices.to_ckan(name, display)
                if code not in group_codes:
                    group_codes.append(code)
    if not group_codes:
        group_codes = ["dataset"]
    result["groups"] = [{"name": code} for code in group_codes]

    if _nonempty(values.get(OWNER)):
        result["owner_org"] = choices.to_ckan(OWNER, values[OWNER])
    dataset_type = choices.to_ckan(TYPE, values[TYPE]) if _nonempty(values.get(TYPE)) else master.schemas[schema]
    if dataset_type != master.schemas[schema]:
        raise ValueError(f"Metadata schema does not match {schema}: {dataset_type}")
    result["type"] = dataset_type

    if USAGE_KEY in values or USAGE_TEXT in values:
        keywords = _as_list(values.get(USAGE_KEY))
        notes = _as_list(values.get(USAGE_TEXT))
        result["nutzungshinweise"] = [
            {"stichwort": keywords[i] if i < len(keywords) else "",
             "hinweise": notes[i] if i < len(notes) else ""}
            for i in range(max(len(keywords), len(notes)))
            if (i < len(keywords) and _nonempty(keywords[i])) or
               (i < len(notes) and _nonempty(notes[i]))
        ]

    if OPTIONS in values:
        options = [choices.to_ckan(OPTIONS, option) for option in
                   _as_list(values[OPTIONS]) if _nonempty(option)]
        result[OPTIONS] = (None if not options else options[0] if len(options) == 1
                           else "{" + ",".join(options) + "}")

    for root, data in nested.items():
        result[root] = json.dumps(data, ensure_ascii=False)
    return result


def dataset_to_form(package, schema, master, choices):
    """Represent CKAN package metadata with stable master field names."""
    fields = master.fields(schema)
    result = {}
    groups = package.get("groups") or []
    group_names = [group.get("name") or group.get("title") for group in groups]
    for name, spec in fields.items():
        if name == TAGS:
            result[name] = [tag.get("name") for tag in package.get("tags", [])
                            if tag.get("name")]
            continue
        if name in (MAIN, TOPICS, DEPARTMENT):
            candidates = [code for code in group_names
                          if code in choices.reverse[name]]
            displays = [choices.to_display(name, code) for code in candidates]
            result[name] = displays if name == TOPICS else (displays[0] if displays else None)
            continue
        if name == OWNER:
            organization = package.get("organization")
            title = organization.get("title") if isinstance(organization, dict) else None
            if _nonempty(title):
                result[name] = title
            else:
                code = (organization.get("name") if isinstance(organization, dict)
                        else None) or package.get("owner_org")
                result[name] = _choice_to_display(choices, name, code, True)
            continue
        if name == TYPE:
            result[name] = _choice_to_display(choices, name,
                                              package.get("type"), True)
            continue
        if name in (USAGE_KEY, USAGE_TEXT):
            entries = _json_value(_package_value(package, "nutzungshinweise")) or []
            key = "stichwort" if name == USAGE_KEY else "hinweise"
            result[name] = [entry.get(key) for entry in entries]
            continue
        if name == OPTIONS:
            options = _as_list(_package_value(package, name))
            result[name] = [_choice_to_display(choices, name, option, True)
                            for option in options]
            continue
        value = _package_value(package, name)
        is_select = "select" in spec.format
        if spec.format.startswith("multi-"):
            result[name] = [_choice_to_display(choices, name, part, is_select)
                            for part in _as_list(value)]
        else:
            result[name] = _choice_to_display(choices, name, value, is_select)
    return result
