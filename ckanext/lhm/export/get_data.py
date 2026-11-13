"""Export CKAN datasets to current, protected, versionless Excel forms."""
from __future__ import annotations

import json
import os
import shutil
import sys
import time
from pathlib import Path
from urllib.parse import parse_qs, quote, urlsplit

import requests

try:
    from .field_mapping import MasterConfig, TABLES, configured_schema
    from .choice_mapping import ChoiceMap
    from .ckan_model import dataset_to_form
    from .form_adapter import write_form
except ImportError:
    from field_mapping import MasterConfig, TABLES, configured_schema
    from choice_mapping import ChoiceMap
    from ckan_model import dataset_to_form
    from form_adapter import write_form

ROOT = Path(__file__).resolve().parent
EXCEL_TEMPLATES = ROOT / "excel_templates"
MASTER = EXCEL_TEMPLATES / "template_master_config.xlsx"
_BACKEND = "external"
TRANSIENT_STATUS = (502, 503, 504)


def config():
    if _BACKEND == "internal":
        return {"base_url": "http://localhost:5000", "api_key_harvester": ""}
    if len(sys.argv) < 2:
        raise ValueError("Path to harvester configuration is missing")
    with open(sys.argv[1], encoding="utf-8") as handle:
        return json.load(handle)


def sheet_password():
    password = (os.environ.get("sheet_protection") if _BACKEND == "internal"
                else config().get("sheet_protection"))
    if not isinstance(password, str) or not password:
        raise ValueError("'sheet_protection' is missing from JSON configuration or environment")
    return password


def ckan_request(api_string):
    if _BACKEND == "internal":
        import ckan.plugins.toolkit as tk
        from ckan.common import json as ckan_json
        try:
            from flask import g
            user = getattr(g, "user", None)
        except RuntimeError:
            user = None
        url = urlsplit(api_string)
        data = {key: vals[-1] for key, vals in parse_qs(url.query).items()}
        for key in ("include_drafts", "include_private", "include_datasets",
                    "include_dataset_count"):
            if key in data:
                data[key] = data[key].lower() == "true"
        result = tk.get_action(url.path.rsplit("/", 1)[-1])({"user": user}, data)
        return ckan_json.loads(ckan_json.dumps(result))
    settings = config()
    url = settings["base_url"].rstrip("/") + api_string
    response = _get_with_retry(url, settings)
    payload = response.json()
    if not payload.get("success"):
        raise ValueError(f"CKAN action failed: {api_string}: {payload}")
    return payload["result"]


def _get_with_retry(url, settings, timeout=90, retry_404=False):
    attempts = max(1, int(settings.get("ckan_retry_attempts", 10)))
    delay = max(0, float(settings.get("ckan_retry_delay_seconds", 2)))
    for attempt in range(1, attempts + 1):
        try:
            response = requests.get(
                url, headers={"Authorization": settings["api_key_harvester"]},
                timeout=timeout)
            response.raise_for_status()
            return response
        except (requests.Timeout, requests.ConnectionError,
                requests.HTTPError) as exc:
            status = exc.response.status_code if isinstance(exc, requests.HTTPError) else None
            retryable = status in TRANSIENT_STATUS or (retry_404 and status == 404)
            if (status is not None and not retryable) or attempt == attempts:
                raise
            print(f"CKAN: GET {status or type(exc).__name__}; "
                  f"retry {attempt + 1}/{attempts} in {delay:g} s", flush=True)
            time.sleep(delay)


def _datastore(resource_id):
    data = ckan_request(f"/api/3/action/datastore_search?resource_id={resource_id}&limit=32000")
    records = list(data.get("records") or [])
    total = data.get("total", len(records))
    while len(records) < total:
        page = ckan_request(f"/api/3/action/datastore_search?resource_id={resource_id}&limit=32000&offset={len(records)}")
        records.extend(page.get("records") or [])
        if not page.get("records"):
            break
    data["records"] = records
    return data


def _ready_datastore(resource):
    """Never export an unavailable resource as an apparently empty table."""
    settings = config()
    attempts = max(1, int(settings.get("datastore_wait_attempts", 30)))
    delay = max(0, float(settings.get("datastore_wait_delay_seconds", 2)))
    for attempt in range(1, attempts + 1):
        if resource.get("datastore_active"):
            try:
                return _datastore(resource["id"])
            except requests.HTTPError as exc:
                if exc.response is None or exc.response.status_code != 404:
                    raise
            except ValueError as exc:
                if "not found" not in str(exc).lower():
                    raise
        if attempt == attempts:
            raise ValueError(
                f"Datastore for resource {resource.get('name')!r} ({resource['id']}) "
                f"is not ready after {attempts} checks")
        if attempt == 1:
            print(f"CKAN: waiting for datastore of resource "
                  f"{resource.get('name')!r} ({resource['id']})", flush=True)
        time.sleep(delay)
        try:
            resource = ckan_request(
                f"/api/3/action/resource_show?id={quote(str(resource['id']), safe='')}")
        except requests.HTTPError as exc:
            if exc.response is None or exc.response.status_code != 404:
                raise
        except ValueError as exc:
            if "not found" not in str(exc).lower():
                raise


def _resource_tables(package, choices, resource_folder):
    tables = {name: [] for name in TABLES}
    # A previous export may contain uploads that no longer exist in CKAN.
    if resource_folder.is_dir():
        shutil.rmtree(resource_folder)
    for resource in package.get("resources") or []:
        name = resource.get("name")
        if resource.get("format", "").lower() == "oracle-db" and resource.get("position") == 0:
            for field in _ready_datastore(resource).get("fields", []):
                if field.get("id") == "_id":
                    continue
                info = field.get("info") or {}
                code = info.get("db_type") or field.get("type")
                try:
                    display = choices.to_display("dic_type", code)
                except ValueError:
                    display = code
                tables["Datenverzeichnis"].append({
                    "dic_id": field.get("id"), "dic_type": display,
                    "dic_condition": info.get("condition"),
                    "dic_notes": info.get("notes"),
                    "dic_label": info.get("label"),
                    "dic_override": info.get("opendata"),
                })
        elif name == "Katalogwerte":
            for record in _ready_datastore(resource).get("records", []):
                tables["Katalogwerte"].append({
                    "kat_id": record.get("_id"),
                    "kat_attribut": record.get("Attribut"),
                    "kat_wert": record.get("Wert"),
                    "kat_bedeutung": record.get("Bedeutung"),
                })
        else:
            fmt = resource.get("format")
            try:
                fmt = choices.to_display("dd_format", fmt)
            except ValueError:
                pass
            tables["Dienste und Dokumente"].append({
                "dd_name": name, "dd_beschr": resource.get("description"),
                "dd_format": fmt, "dd_url": resource.get("url"),
            })
            if resource.get("url_type") == "upload" and resource.get("url"):
                resource_folder.mkdir(parents=True, exist_ok=True)
                filename = resource["url"].rsplit("/", 1)[-1]
                settings = config()
                response = _get_with_retry(resource["url"], settings, retry_404=True)
                (resource_folder / filename).write_bytes(response.content)
    return tables


def packages_to_files(packages, limit, wdir, excel_template=None, backend="external",
                      progress=True):
    global _BACKEND
    _BACKEND = backend
    password = sheet_password()
    master = MasterConfig(MASTER)
    schema_filter = (configured_schema(excel_template, master)
                     if excel_template else None)
    output = Path(wdir)
    (output / "json").mkdir(parents=True, exist_ok=True)
    (output / "excel").mkdir(parents=True, exist_ok=True)
    requested = [packages] if isinstance(packages, str) else list(packages)
    exported = []
    organization_cache = {}
    dots_pending = False
    for package_name in requested[:limit]:
        package = ckan_request(f"/api/3/action/package_show?id={package_name}")
        schema = master.schema_for_type(package.get("type"))
        if schema is None or (schema_filter and schema_filter != schema):
            if progress:
                print(".", end="", flush=True)
                dots_pending = True
            continue
        name = package["name"]
        if progress and dots_pending:
            print()
            dots_pending = False
        if progress:
            print(name, flush=True)
        organization = package.get("organization")
        owner_id = package.get("owner_org")
        if owner_id and not (isinstance(organization, dict) and organization.get("title")):
            if owner_id not in organization_cache:
                details = ckan_request(
                    f"/api/3/action/organization_show?id={quote(str(owner_id), safe='')}"
                    "&include_datasets=false&include_dataset_count=false")
                if not isinstance(details, dict) or not details.get("title"):
                    raise ValueError(f"Organization title for {owner_id!r} is missing")
                organization_cache[owner_id] = {"title": details["title"],
                                                "name": details.get("name")}
            package["organization"] = organization_cache[owner_id]
        choices = ChoiceMap(MASTER, schema)
        values = dataset_to_form(package, schema, master, choices)
        tables = _resource_tables(package, choices, output / "excel" / name)
        with (output / "json" / f"{name}.json").open("w", encoding="utf-8") as handle:
            json.dump(package, handle, ensure_ascii=False, indent=2)
        write_form(EXCEL_TEMPLATES / f"form_{schema}.xlsx",
                   output / "excel" / f"{name}.xlsx", master, schema, values,
                   tables, password)
        exported.append(name)
    if progress and dots_pending:
        print()
    return exported
