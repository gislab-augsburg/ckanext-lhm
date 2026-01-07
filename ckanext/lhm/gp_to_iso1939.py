#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import csv
import argparse
import re
from copy import deepcopy
from pathlib import Path
from lxml import etree
from typing import Optional, Union
# Namespace-Map für XPath
NSMAP = {
    "gmd": "http://www.isotc211.org/2005/gmd",
    "gco": "http://www.isotc211.org/2005/gco",
    "srv": "http://www.isotc211.org/2005/srv",
    "gml": "http://www.opengis.net/gml",
    "xlink": "http://www.w3.org/1999/xlink",
}
# Spezial-Mapping von Mapping-Feld -> JSON-Feld
SPECIAL_FIELD_MAP = {
    "ident_title": "title",   # Titel kommt aus CKAN-Title
    "ident_keywords": "tags", # Keywords kommen aus tags[]
    "ident_abstract": "notes"
}
# Felder, die im Konsistenzcheck ignoriert werden, weil sie
# über Speziallogik befüllt werden (nicht über das Mapping):
SKIP_COVERAGE_FIELDS = {
    # werden über apply_refsystem_from_json() gesetzt
    "refsystem_code",
    "refsystem_codespace",
    "refsystem_version",
    # werden über apply_bbox_from_json() gesetzt
    "extras.bbox-west-long",
    "extras.bbox-east-long",
    "extras.bbox-south-lat",
    "extras.bbox-north-lat",
    # werden über apply_distrib_format_from_json() gesetzt
    "distrib_format_name",
    "distrib_format_version",
    # wird gleich über apply_ident_date_from_json() gesetzt
    "ident_date_",
}
# -------------------------------
# Embedded mapping (from mapping.csv)
# -------------------------------
MAPPING_PAIRS = [
    ('ident_individual', 'gmd:MD_Metadata/gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:pointOfContact/gmd:CI_ResponsibleParty/gmd:individualName/gco:CharacterString'),
    ('ident_title', 'gmd:MD_Metadata/gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:citation/gmd:CI_Citation/gmd:title/gco:CharacterString'),
    ('ident_abstract', 'gmd:MD_Metadata/gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:abstract/gco:CharacterString'),
    ('ident_keywords', 'gmd:MD_Metadata/gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:descriptiveKeywords/gmd:MD_Keywords/gmd:keyword/gco:CharacterString'),
    ('ident_topic', 'gmd:MD_Metadata/gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:topicCategory/gmd:MD_TopicCategoryCode'),
    ('ident_datetype', 'gmd:MD_Metadata/gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:citation/gmd:CI_Citation/gmd:date/gmd:CI_Date/gmd:dateType/gmd:CI_DateTypeCode'),
    ('ident_date_', 'gmd:MD_Metadata/gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:citation/gmd:CI_Citation/gmd:date/gmd:CI_Date/gmd:date/gco:Date'),
    ('ident_maintenancefrequency', 'gmd:MD_Metadata/gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:resourceMaintenance/gmd:MD_MaintenanceInformation/gmd:maintenanceAndUpdateFrequency/gmd:MD_MaintenanceFrequencyCode'),
    ('ident_organisation', 'gmd:MD_Metadata/gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:pointOfContact/gmd:CI_ResponsibleParty/gmd:organisationName/gco:CharacterString'),
    ('ident_deliverypoint', 'gmd:MD_Metadata/gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:pointOfContact/gmd:CI_ResponsibleParty/gmd:contactInfo/gmd:CI_Contact/gmd:address/gmd:CI_Address/gmd:deliveryPoint/gco:CharacterString'),
    ('ident_city', 'gmd:MD_Metadata/gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:pointOfContact/gmd:CI_ResponsibleParty/gmd:contactInfo/gmd:CI_Contact/gmd:address/gmd:CI_Address/gmd:city/gco:CharacterString'),
    ('ident_administrativearea', 'gmd:MD_Metadata/gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:pointOfContact/gmd:CI_ResponsibleParty/gmd:contactInfo/gmd:CI_Contact/gmd:address/gmd:CI_Address/gmd:administrativeArea/gco:CharacterString'),
    ('ident_postalcode', 'gmd:MD_Metadata/gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:pointOfContact/gmd:CI_ResponsibleParty/gmd:contactInfo/gmd:CI_Contact/gmd:address/gmd:CI_Address/gmd:postalCode/gco:CharacterString'),
    ('ident_country', 'gmd:MD_Metadata/gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:pointOfContact/gmd:CI_ResponsibleParty/gmd:contactInfo/gmd:CI_Contact/gmd:address/gmd:CI_Address/gmd:country/gco:CharacterString'),
    ('ident_voice', 'gmd:MD_Metadata/gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:pointOfContact/gmd:CI_ResponsibleParty/gmd:contactInfo/gmd:CI_Contact/gmd:phone/gmd:CI_Telephone/gmd:voice/gco:CharacterString'),
    ('ident_facsimile', 'gmd:MD_Metadata/gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:pointOfContact/gmd:CI_ResponsibleParty/gmd:contactInfo/gmd:CI_Contact/gmd:phone/gmd:CI_Telephone/gmd:facsimile/gco:CharacterString'),
    ('ident_email', 'gmd:MD_Metadata/gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:pointOfContact/gmd:CI_ResponsibleParty/gmd:contactInfo/gmd:CI_Contact/gmd:address/gmd:CI_Address/gmd:electronicMailAddress/gco:CharacterString'),
    ('ident_online', 'gmd:MD_Metadata/gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:pointOfContact/gmd:CI_ResponsibleParty/gmd:contactInfo/gmd:CI_Contact/gmd:onlineResource/gmd:CI_OnlineResource/gmd:linkage/gmd:URL'),
    ('ident_role', 'gmd:MD_Metadata/gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:pointOfContact/gmd:CI_ResponsibleParty/gmd:role/gmd:CI_RoleCode'),
    ('ident_classification', 'gmd:MD_Metadata/gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:resourceConstraints/gmd:MD_SecurityConstraints/gmd:classification/gmd:MD_ClassificationCode'),
    ('ident_accessconstraints', 'gmd:MD_Metadata/gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:resourceConstraints/gmd:MD_LegalConstraints/gmd:accessConstraints/gmd:MD_RestrictionCode'),
    ('ident_uselimitation', 'gmd:MD_Metadata/gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:resourceConstraints/gmd:MD_LegalConstraints/gmd:useLimitation/gco:CharacterString'),
    ('ident_otherconstraints', 'gmd:MD_Metadata/gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:resourceConstraints/gmd:MD_LegalConstraints/gmd:otherConstraints/gco:CharacterString'),
    ('ident_useconstraints', 'gmd:MD_Metadata/gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:resourceConstraints/gmd:MD_LegalConstraints/gmd:useConstraints/gmd:MD_RestrictionCode'),
    ('distrib_organisation', 'gmd:MD_Metadata/gmd:distributionInfo/gmd:MD_Distribution/gmd:distributor/gmd:MD_Distributor/gmd:distributorContact/gmd:CI_ResponsibleParty/gmd:organisationName/gco:CharacterString'),
    ('distrib_individual', 'gmd:MD_Metadata/gmd:distributionInfo/gmd:MD_Distribution/gmd:distributor/gmd:MD_Distributor/gmd:distributorContact/gmd:CI_ResponsibleParty/gmd:individualName/gco:CharacterString'),
    ('distrib_position', 'gmd:MD_Metadata/gmd:distributionInfo/gmd:MD_Distribution/gmd:distributor/gmd:MD_Distributor/gmd:distributorContact/gmd:CI_ResponsibleParty/gmd:positionName/gco:CharacterString'),
    ('distrib_voice', 'gmd:MD_Metadata/gmd:distributionInfo/gmd:MD_Distribution/gmd:distributor/gmd:MD_Distributor/gmd:distributorContact/gmd:CI_ResponsibleParty/gmd:contactInfo/gmd:CI_Contact/gmd:phone/gmd:CI_Telephone/gmd:voice/gco:CharacterString'),
    ('distrib_facsimile', 'gmd:MD_Metadata/gmd:distributionInfo/gmd:MD_Distribution/gmd:distributor/gmd:MD_Distributor/gmd:distributorContact/gmd:CI_ResponsibleParty/gmd:contactInfo/gmd:CI_Contact/gmd:phone/gmd:CI_Telephone/gmd:facsimile/gco:CharacterString'),
    ('distrib_email', 'gmd:MD_Metadata/gmd:distributionInfo/gmd:MD_Distribution/gmd:distributor/gmd:MD_Distributor/gmd:distributorContact/gmd:CI_ResponsibleParty/gmd:contactInfo/gmd:CI_Contact/gmd:address/gmd:CI_Address/gmd:electronicMailAddress/gco:CharacterString'),
    ('distrib_online', 'gmd:MD_Metadata/gmd:distributionInfo/gmd:MD_Distribution/gmd:distributor/gmd:MD_Distributor/gmd:distributorContact/gmd:CI_ResponsibleParty/gmd:contactInfo/gmd:CI_Contact/gmd:onlineResource/gmd:CI_OnlineResource/gmd:linkage/gmd:URL'),
    ('distrib_role', 'gmd:MD_Metadata/gmd:distributionInfo/gmd:MD_Distribution/gmd:distributor/gmd:MD_Distributor/gmd:distributorContact/gmd:CI_ResponsibleParty/gmd:role/gmd:CI_RoleCode'),
    ('dataquality_scopedescription_dataset', 'gmd:MD_Metadata/gmd:dataQualityInfo/gmd:DQ_DataQuality/gmd:scope/gmd:DQ_Scope/gmd:levelDescription/gmd:MD_ScopeDescription/gmd:dataset/gco:CharacterString'),
    ('dataquality_scopedescription_other', 'gmd:MD_Metadata/gmd:dataQualityInfo/gmd:DQ_DataQuality/gmd:scope/gmd:DQ_Scope/gmd:levelDescription/gmd:MD_ScopeDescription/gmd:other/gco:CharacterString'),
    ('ident_alternatetitle', 'gmd:MD_Metadata/gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:citation/gmd:CI_Citation/gmd:alternateTitle/gco:CharacterString'),
    ('quantitativeresult', 'gmd:MD_Metadata/gmd:dataQualityInfo/gmd:DQ_DataQuality/gmd:report/gmd:DQ_QuantitativeAttributeAccuracy/gmd:result/gmd:DQ_QuantitativeResult/gmd:value/gco:Record/gco:Integer'),
    ('refsystem_code', 'gmd:MD_Metadata/gmd:referenceSystemInfo/gmd:MD_ReferenceSystem/gmd:referenceSystemIdentifier/gmd:RS_Identifier/gmd:code/gco:CharacterString'),
    ('refsystem_codespace', 'gmd:MD_Metadata/gmd:referenceSystemInfo/gmd:MD_ReferenceSystem/gmd:referenceSystemIdentifier/gmd:RS_Identifier/gmd:codeSpace/gco:CharacterString'),
    ('refsystem_version', 'gmd:MD_Metadata/gmd:referenceSystemInfo/gmd:MD_ReferenceSystem/gmd:referenceSystemIdentifier/gmd:RS_Identifier/gmd:version/gco:CharacterString'),
    ('contact_organisation', 'gmd:MD_Metadata/gmd:contact/gmd:CI_ResponsibleParty/gmd:organisationName/gco:CharacterString'),
    ('contact_individual', 'gmd:MD_Metadata/gmd:contact/gmd:CI_ResponsibleParty/gmd:individualName/gco:CharacterString'),
    ('contact_deliverypoint', 'gmd:MD_Metadata/gmd:contact/gmd:CI_ResponsibleParty/gmd:contactInfo/gmd:CI_Contact/gmd:address/gmd:CI_Address/gmd:deliveryPoint/gco:CharacterString'),
    ('contact_city', 'gmd:MD_Metadata/gmd:contact/gmd:CI_ResponsibleParty/gmd:contactInfo/gmd:CI_Contact/gmd:address/gmd:CI_Address/gmd:city/gco:CharacterString'),
    ('contact_administrativearea', 'gmd:MD_Metadata/gmd:contact/gmd:CI_ResponsibleParty/gmd:contactInfo/gmd:CI_Contact/gmd:address/gmd:CI_Address/gmd:administrativeArea/gco:CharacterString'),
    ('contact_postalcode', 'gmd:MD_Metadata/gmd:contact/gmd:CI_ResponsibleParty/gmd:contactInfo/gmd:CI_Contact/gmd:address/gmd:CI_Address/gmd:postalCode/gco:CharacterString'),
    ('contact_country', 'gmd:MD_Metadata/gmd:contact/gmd:CI_ResponsibleParty/gmd:contactInfo/gmd:CI_Contact/gmd:address/gmd:CI_Address/gmd:country/gco:CharacterString'),
    ('contact_voice', 'gmd:MD_Metadata/gmd:contact/gmd:CI_ResponsibleParty/gmd:contactInfo/gmd:CI_Contact/gmd:phone/gmd:CI_Telephone/gmd:voice/gco:CharacterString'),
    ('contact_facsimile', 'gmd:MD_Metadata/gmd:contact/gmd:CI_ResponsibleParty/gmd:contactInfo/gmd:CI_Contact/gmd:phone/gmd:CI_Telephone/gmd:facsimile/gco:CharacterString'),
    ('contact_email', 'gmd:MD_Metadata/gmd:contact/gmd:CI_ResponsibleParty/gmd:contactInfo/gmd:CI_Contact/gmd:address/gmd:CI_Address/gmd:electronicMailAddress/gco:CharacterString'),
    ('contact_online', 'gmd:MD_Metadata/gmd:contact/gmd:CI_ResponsibleParty/gmd:contactInfo/gmd:CI_Contact/gmd:onlineResource/gmd:CI_OnlineResource/gmd:linkage/gmd:URL'),
    ('contact_role', 'gmd:MD_Metadata/gmd:contact/gmd:CI_ResponsibleParty/gmd:role/gmd:CI_RoleCode'),
    ('dataquality_scopecode', 'gmd:MD_Metadata/gmd:dataQualityInfo/gmd:DQ_DataQuality/gmd:scope/gmd:DQ_Scope/gmd:level/gmd:MD_ScopeCode'),
    ('distrib_format_name', 'gmd:MD_Metadata/gmd:distributionInfo/gmd:MD_Distribution/gmd:distributionFormat/gmd:MD_Format/gmd:name/gco:CharacterString'),
    ('distrib_format_version', 'gmd:MD_Metadata/gmd:distributionInfo/gmd:MD_Distribution/gmd:distributionFormat/gmd:MD_Format/gmd:version/gco:CharacterString'),
    ('ident_identifier', 'gmd:MD_Metadata/gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:citation/gmd:CI_Citation/gmd:identifier/gmd:MD_Identifier/gmd:code/gco:CharacterString'),
    ('iso_standard', 'gmd:MD_Metadata/gmd:metadataStandardName/gco:CharacterString'),
    ('iso_version', 'gmd:MD_Metadata/gmd:metadataStandardVersion/gco:CharacterString'),
    ('service_type', 'gmd:MD_Metadata/gmd:identificationInfo/srv:SV_ServiceIdentification/srv:serviceType/gco:LocalName'),
    ('file_identifier', 'gmd:MD_Metadata/gmd:fileIdentifier/gco:CharacterString'),
    ('hierarchylevel_scopecode', 'gmd:MD_Metadata/gmd:hierarchyLevel/gmd:MD_ScopeCode')
]
def load_embedded_mapping():
    """Return a fresh list of mapping dicts from the embedded mapping pairs."""
    return [{"ckan_field": f, "xml_path_pattern": p} for f, p in MAPPING_PAIRS]
# -------------------------------
# Laden von Daten / Mapping
# -------------------------------
def load_metadata(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)
def load_mapping_csv(path: Union[Path, None]):
    """
    Lädt mapping.csv (ckan field;xml path).
    Wenn path None ist, wird das eingebettete Mapping (MAPPING_PAIRS) verwendet.
    """
    if path is None:
        return load_embedded_mapping()
    mappings = []
    with path.open("r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            ckan_field = (row.get("ckan field") or "").strip()
            xml_path = (row.get("xml path") or "").strip()
            if not ckan_field or not xml_path:
                continue
            mappings.append({"ckan_field": ckan_field, "xml_path_pattern": xml_path})
    return mappings
def looks_like_datetime(value: str) -> bool:
    """
    Prüft, ob der Wert wie ein ISO-8601 DateTime aussieht, z.B.:
      2023-09-29T09:00:00
      2023-09-29T09:00
      2023-09-29T09:00:00Z
      2023-09-29T09:00:00+02:00
    Ein reines Datum wie 2024-04-18 soll NICHT als DateTime gelten.
    """
    if not isinstance(value, str):
        return False
    value = value.strip()
    datetime_pattern = re.compile(
        r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?(Z|[+-]\d{2}:\d{2})?$"
    )
    return bool(datetime_pattern.match(value))
def adjust_mappings_for_iso_type_and_date(meta: dict, mappings, iso_type: str):
    """
    Passt die xml_path_pattern je nach iso_type UND ident_date_ an.
    - iso_type:
      - SV_ServiceIdentification: nichts an der Basisstruktur ändern
      - MD_DataIdentification: Pfade mit
          MD_Metadata/gmd:identificationInfo/srv:SV_ServiceIdentification
        werden zu
          MD_Metadata/gmd:identificationInfo/gmd:MD_DataIdentification
    - ident_date_:
      Wenn ident_date_ wie ein DateTime aussieht, überschreiben wir das Mapping
      für dieses Feld komplett mit dem gewünschten DateTime-Pfad.
    """
    # 1) Basis-Anpassung für MD_DataIdentification
    if iso_type == "MD_DataIdentification":
        old1 = "gmd:MD_Metadata/gmd:identificationInfo/srv:SV_ServiceIdentification"
        new1 = "gmd:MD_Metadata/gmd:identificationInfo/gmd:MD_DataIdentification"
        old2 = "MD_Metadata/gmd:identificationInfo/srv:SV_ServiceIdentification"
        new2 = "MD_Metadata/gmd:identificationInfo/gmd:MD_DataIdentification"
        for m in mappings:
            p = m["xml_path_pattern"]
            p = p.replace(old1, new1)
            p = p.replace(old2, new2)
            m["xml_path_pattern"] = p
    # 2) Sonderfall ident_date_ -> DateTime-Pfad, falls DateTime
    date_val = meta.get("ident_date_")
    use_datetime = looks_like_datetime(date_val)
    if not use_datetime:
        return  # nichts weiter tun, normales gco:Date-Mapping bleibt aktiv
    if iso_type == "MD_DataIdentification":
        datetime_path = (
            "gmd:MD_Metadata/gmd:identificationInfo/"
            "gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/"
            "gmd:date/gmd:CI_Date/gmd:date/gco:DateTime"
        )
    else:
        # Default / Service
        datetime_path = (
            "gmd:MD_Metadata/gmd:identificationInfo/"
            "srv:SV_ServiceIdentification/gmd:citation/gmd:CI_Citation/"
            "gmd:date/gmd:CI_Date/gmd:date/gco:DateTime"
        )
    for m in mappings:
        if m["ckan_field"] == "ident_date_":
            m["xml_path_pattern"] = datetime_path
def load_template_xml(path: Path) -> etree._ElementTree:
    parser = etree.XMLParser(remove_blank_text=True)
    return etree.parse(str(path), parser)
# -------------------------------
# Hilfsfunktionen JSON-Zugriff
# -------------------------------
def get_extra_value(meta: dict, key: str):
    """
    Holt einen Wert aus meta['extras'] mit gegebenem key.
    """
    for extra in meta.get("extras", []):
        if extra.get("key") == key:
            return extra.get("value")
    return None
def get_json_value(meta: dict, field: str):
    """
    Holt den Wert aus metadata.json für das angegebene Mapping-Feld.
    Unterstützt u.a.:
      - einfache Felder: ident_*, contact_*, ...
      - SPECIAL_FIELD_MAP (z.B. ident_title -> title)
      - Keywords aus tags[]
      - Extras mit Präfix "extras.": z.B. extras.bbox-east-long
    """
    # Extras.* -> aus extras-Liste holen
    if field.startswith("extras."):
        extra_key = field.split(".", 1)[1]
        return get_extra_value(meta, extra_key)
    # Spezial-Mapping
    if field in SPECIAL_FIELD_MAP:
        real_field = SPECIAL_FIELD_MAP[field]
    else:
        real_field = field
    # Keywords aus tags[]
    if field == "ident_keywords":
        tags = meta.get("tags") or []
        return [t.get("name") for t in tags if isinstance(t, dict) and t.get("name")]
    # Standard: direktes JSON-Feld
    return meta.get(real_field)
def qn(name: str) -> str:
    """
    'gmd:fileIdentifier' -> '{uri}fileIdentifier'
    Hilfsfunktion zum Erzeugen vollqualifizierter LXML-Tags.
    """
    prefix, local = name.split(":", 1)
    uri = NSMAP[prefix]
    return f"{{{uri}}}{local}"
# -------------------------------
# XPath / XML-Hilfen
# -------------------------------
def normalize_xpath(pattern: str) -> str:
    """
    Wandelt die Pfade aus mapping.csv in XPath für lxml um.
    Beispiele:
      gmd:MD_Metadata/gmd:identificationInfo/... -> .//gmd:identificationInfo/...
      "..." im Pfad wird grob als Platzhalter für // behandelt.
    """
    path = pattern.strip()
    if path.startswith("gmd:MD_Metadata/"):
        path = path[len("gmd:MD_Metadata/"):]
    # "..." als Platzhalter: ersetzen durch //
    while "..." in path:
        idx = path.index("...")
        before = path[:idx]
        after = path[idx + 3:]
        last_slash_before = before.rfind("/")
        if last_slash_before != -1:
            before = before[:last_slash_before]
        first_slash_after = after.find("/")
        if first_slash_after != -1:
            after = after[first_slash_after + 1:]
        path = before + "//" + after
    if not path.startswith(".//"):
        path = ".//" + path
    return path
def set_node_value(node: etree._Element, value):
    """
    Wert in ein XML-Element setzen.
    Bei CodeList-Elementen wird codeListValue verwendet.
    """
    if node.tag.endswith("Code"):
        node.attrib["codeListValue"] = str(value)
    else:
        node.text = str(value)
# -------------------------------
# Resources -> gmd:onLine
# -------------------------------
def apply_resources_from_json(meta: dict, root: etree._Element):
    """
    Baut die <gmd:onLine>-Einträge aus meta['resources'] neu auf.
    Verwendet:
      - resources[i]["url"]     -> gmd:linkage/gmd:URL
      - resources[i]["name"]    -> gmd:name/gco:CharacterString
      - resources[i]["format"]  -> gmd:applicationProfile/gco:CharacterString
    """
    resources = meta.get("resources") or []
    if not resources:
        return
    md_dto_list = root.xpath(
        ".//gmd:distributionInfo//gmd:MD_DigitalTransferOptions",
        namespaces=NSMAP,
    )
    if not md_dto_list:
        return
    md_dto = md_dto_list[0]
    existing_onlines = md_dto.xpath("./gmd:onLine", namespaces=NSMAP)
    if not existing_onlines:
        return
    base_online = existing_onlines[0]
    for ol in existing_onlines:
        parent = ol.getparent()
        if parent is not None:
            parent.remove(ol)
    for res in resources:
        url = res.get("url")
        name = res.get("name")
        fmt = res.get("format")
        if not url:
            continue
        new_ol = deepcopy(base_online)
        url_nodes = new_ol.xpath(".//gmd:linkage/gmd:URL", namespaces=NSMAP)
        for u in url_nodes:
            u.text = url
        if name:
            name_nodes = new_ol.xpath(".//gmd:name/gco:CharacterString", namespaces=NSMAP)
            for n in name_nodes:
                n.text = name
        if fmt:
            app_nodes = new_ol.xpath(
                ".//gmd:applicationProfile/gco:CharacterString",
                namespaces=NSMAP,
            )
            for a in app_nodes:
                a.text = fmt
        md_dto.append(new_ol)
# -------------------------------
# Referenzsysteme -> gmd:referenceSystemInfo
# -------------------------------
def apply_refsystem_from_json(meta: dict, root: etree._Element):
    """
    Baut die <gmd:referenceSystemInfo>-Einträge aus meta['refsystem'] neu auf.
    Erwartete Struktur in metadata.json:
      "refsystem": [
        {
          "refsystem_code": "...",
          "refsystem_codespace": "...",
          "refsystem_version": "..."
        },
        ...
      ]
    """
    ref_list = meta.get("refsystem") or []
    if not ref_list:
        return
    infos = root.xpath(".//gmd:referenceSystemInfo", namespaces=NSMAP)
    if not infos:
        return
    base_info = deepcopy(infos[0])
    parent = infos[0].getparent()
    for n in infos:
        parent.remove(n)
    for ref in ref_list:
        new_info = deepcopy(base_info)
        code = ref.get("refsystem_code")
        codespace = ref.get("refsystem_codespace")
        version = ref.get("refsystem_version")
        if code is not None:
            for node in new_info.xpath(
                ".//gmd:RS_Identifier/gmd:code/gco:CharacterString",
                namespaces=NSMAP,
            ):
                node.text = str(code)
        if codespace is not None:
            for node in new_info.xpath(
                ".//gmd:RS_Identifier/gmd:codeSpace/gco:CharacterString",
                namespaces=NSMAP,
            ):
                node.text = str(codespace)
        if version is not None:
            for node in new_info.xpath(
                ".//gmd:RS_Identifier/gmd:version/gco:CharacterString",
                namespaces=NSMAP,
            ):
                node.text = str(version)
        parent.append(new_info)
# -------------------------------
# Verteilungsformate -> gmd:distributionFormat / gmd:MD_Format
# -------------------------------
def apply_distrib_format_from_json(meta: dict, root: etree._Element):
    """
    Baut die <gmd:distributionFormat>-Einträge aus meta['distrib_format'] neu auf.
    Erwartete Struktur in metadata.json:
      "distrib_format": [
        {
          "distrib_format_name": "...",
          "distrib_format_version": "..."
        },
        ...
      ]
    Im Template wird der erste vorhandene
      gmd:distributionInfo/gmd:MD_Distribution/gmd:distributionFormat
    als Vorlage verwendet. Alle vorhandenen distributionFormat-Einträge werden
    entfernt und pro Eintrag in 'distrib_format' neu erzeugt.
    Es werden u.a. gesetzt:
      - gmd:name/gco:CharacterString        <- distrib_format_name
      - gmd:version/gco:CharacterString     <- distrib_format_version
    """
    fmt_list = meta.get("distrib_format") or []
    if not fmt_list:
        return
    # MD_Distribution suchen
    dist_nodes = root.xpath(
        ".//gmd:distributionInfo/gmd:MD_Distribution",
        namespaces=NSMAP,
    )
    if not dist_nodes:
        return
    md_dist = dist_nodes[0]
    # vorhandene distributionFormat-Knoten
    df_nodes = md_dist.xpath("./gmd:distributionFormat", namespaces=NSMAP)
    if not df_nodes:
        return
    base_df = deepcopy(df_nodes[0])
    parent = md_dist
    # alle existierenden distributionFormat entfernen
    for n in df_nodes:
        parent.remove(n)
    # neue distributionFormat-Einträge auf Basis des Templates aufbauen
    for fmt in fmt_list:
        new_df = deepcopy(base_df)
        name = fmt.get("distrib_format_name")
        version = fmt.get("distrib_format_version")
        if name is not None:
            for node in new_df.xpath(".//gmd:name/gco:CharacterString", namespaces=NSMAP):
                node.text = str(name)
        if version is not None:
            for node in new_df.xpath(".//gmd:version/gco:CharacterString", namespaces=NSMAP):
                node.text = str(version)
        parent.append(new_df)
# -------------------------------
# Datum -> gmd:CI_Citation / ... / gmd:CI_Date
# -------------------------------
def apply_ident_date_from_json(meta: dict, root: etree._Element, iso_type: str):
    """
    Setzt das Feld ident_date_ in der Citation:
      - für Services unter srv:SV_ServiceIdentification
      - für Datensätze unter gmd:MD_DataIdentification
    Entscheidet außerdem:
      - wenn Wert wie DateTime aussieht -> gco:DateTime
      - sonst -> gco:Date
    """
    value = meta.get("ident_date_")
    if not value:
        return
    # Service vs. Dataset
    if iso_type == "MD_DataIdentification":
        ident_nodes = root.xpath(
            ".//gmd:identificationInfo/gmd:MD_DataIdentification",
            namespaces=NSMAP,
        )
    else:
        ident_nodes = root.xpath(
            ".//gmd:identificationInfo/srv:SV_ServiceIdentification",
            namespaces=NSMAP,
        )
    if not ident_nodes:
        return
    ident = ident_nodes[0]
    # Citation suchen oder anlegen
    cit_nodes = ident.xpath("./gmd:citation/gmd:CI_Citation", namespaces=NSMAP)
    if cit_nodes:
        cit = cit_nodes[0]
    else:
        cit = etree.SubElement(ident, qn("gmd:citation"))
        cit = etree.SubElement(cit, qn("gmd:CI_Citation"))
    # CI_Date-Struktur suchen oder anlegen
    date_nodes = cit.xpath("./gmd:date/gmd:CI_Date", namespaces=NSMAP)
    if date_nodes:
        ci_date = date_nodes[0]
    else:
        d = etree.SubElement(cit, qn("gmd:date"))
        ci_date = etree.SubElement(d, qn("gmd:CI_Date"))
    # vorhandene Date/DateTime-Children löschen
    for child in list(ci_date):
        local = etree.QName(child).localname
        if local in ("date", "Date", "DateTime"):
            ci_date.remove(child)
    # Entscheiden, ob DateTime
    if looks_like_datetime(value):
        date_container = etree.SubElement(ci_date, qn("gmd:date"))
        date_node = etree.SubElement(date_container, qn("gco:DateTime"))
    else:
        date_container = etree.SubElement(ci_date, qn("gmd:date"))
        date_node = etree.SubElement(date_container, qn("gco:Date"))
    date_node.text = str(value)
# -------------------------------
# BBOX -> gmd:EX_GeographicBoundingBox
# -------------------------------
def apply_bbox_from_json(meta: dict, root: etree._Element, iso_type: str):
    """
    Holt die BBOX-Extras aus metadata.json:
    bbox-west-long, bbox-east-long, bbox-south-lat, bbox-north-lat
    und trägt sie in ein vorhandenes gmd:EX_GeographicBoundingBox ein.
    Die Funktion wählt den BoundingBox-Knoten abhängig von iso_type:
      - MD_DataIdentification -> unter gmd:MD_DataIdentification
      - sonst -> unter srv:SV_ServiceIdentification
    """
    west = get_extra_value(meta, "bbox-west-long")
    east = get_extra_value(meta, "bbox-east-long")
    south = get_extra_value(meta, "bbox-south-lat")
    north = get_extra_value(meta, "bbox-north-lat")
    if not any([west, east, south, north]):
        return

    # 1) passenden identification-Knoten wählen
    if iso_type == "MD_DataIdentification":
        ident_nodes = root.xpath(
            ".//gmd:identificationInfo/gmd:MD_DataIdentification",
            namespaces=NSMAP,
        )
    else:
        ident_nodes = root.xpath(
            ".//gmd:identificationInfo/srv:SV_ServiceIdentification",
            namespaces=NSMAP,
        )

    # Fallback: altes Verhalten, falls Struktur unerwartet ist
    if not ident_nodes:
        bbox_nodes = root.xpath(
            ".//gmd:identificationInfo//gmd:EX_GeographicBoundingBox",
            namespaces=NSMAP,
        )
    else:
        ident = ident_nodes[0]
        bbox_nodes = ident.xpath(".//gmd:EX_GeographicBoundingBox", namespaces=NSMAP)

    if not bbox_nodes:
        return

    bbox = bbox_nodes[0]

    # extentTypeCode muss 1 sein
    extent_type_nodes = bbox.xpath("./gmd:extentTypeCode/gco:Boolean", namespaces=NSMAP)
    if extent_type_nodes:
        extent_type_nodes[0].text = "1"

    # Koordinaten setzen
    if west is not None:
        for n in bbox.xpath("./gmd:westBoundLongitude/gco:Decimal", namespaces=NSMAP):
            n.text = str(west)
    if east is not None:
        for n in bbox.xpath("./gmd:eastBoundLongitude/gco:Decimal", namespaces=NSMAP):
            n.text = str(east)
    if south is not None:
        for n in bbox.xpath("./gmd:southBoundLatitude/gco:Decimal", namespaces=NSMAP):
            n.text = str(south)
    if north is not None:
        for n in bbox.xpath("./gmd:northBoundLatitude/gco:Decimal", namespaces=NSMAP):
            n.text = str(north)


########################################################################
#def prune_empty_elements(elem: etree._Element):
#    """
#    Entfernt leere Elemente:
#      - keine Child Elemente
#      - keine Attribute
#      - kein (nicht-leerer) Text
#    Läuft rekursiv von unten nach oben.
#    """
#    # erst Children bereinigen
#    for child in list(elem):
#        prune_empty_elements(child)
#    # wenn nach der Bereinigung:
#    has_children = len(elem) > 0
#    has_attrs = bool(elem.attrib)
#    text = (elem.text or "").strip()
#    if (not has_children) and (not has_attrs) and text == "":
#        parent = elem.getparent()
#        if parent is not None:
#            parent.remove(elem)
#
####################################################################
## Leere Elemente löschen
def prune_empty_elements(elem: etree._Element):
    """
    Entfernt leere Elemente rekursiv.
    Elemente, die nur "Template-Attribute" wie codeList tragen,
    aber keinen Wert (Text oder codeListValue) enthalten, gelten als leer
    und werden ebenfalls entfernt.
    """
    # 1) erst Children bereinigen
    for child in list(elem):
        prune_empty_elements(child)
    # 2) Hilfsfunktionen
    def has_nonempty_text(e: etree._Element) -> bool:
        return bool((e.text or "").strip())
    def has_meaningful_attributes(e: etree._Element) -> bool:
        """
        True, wenn das Element Attribute hat, die als echter Inhalt gelten.
        codeList allein zählt NICHT als Inhalt.
        """
        if not e.attrib:
            return False
        # Attribute, die KEINEN Inhalt darstellen (typische ISO/Template-Attrs)
        non_content_attr_localnames = {
            "codeList",
            "codeSpace",
            "schemaLocation",  # xsi:schemaLocation
            "type",            # xsi:type
            "nilReason",
        }
        for k, v in e.attrib.items():
            # k kann Namespaced sein: "{uri}local"
            local = k.split("}", 1)[-1] if "}" in k else k
            if local in non_content_attr_localnames:
                continue
            if (v or "").strip():
                return True
        return False
    def is_empty_codelist_element(e: etree._Element) -> bool:
        """
        Ein ISO CodeList-Element ist leer, wenn:
          - es ein codeList Attribut hat
          - und KEIN codeListValue hat
          - und keinen Text hat
          - und keine Kinder hat
        """
        if "codeList" in e.attrib and "codeListValue" not in e.attrib:
            if not has_nonempty_text(e) and len(e) == 0:
                return True
        return False
    # 3) prüfen, ob elem leer ist
    has_children = len(elem) > 0
    text_ok = has_nonempty_text(elem)
    # wenn Children existieren, bleiben wir erstmal drin (Children wurden schon bereinigt)
    if has_children:
        return
    # CodeList ohne codeListValue gilt als leer -> löschen
    if is_empty_codelist_element(elem):
        parent = elem.getparent()
        if parent is not None:
            parent.remove(elem)
        return
    # Keine Children, kein Text, keine inhaltlichen Attribute -> löschen
    if (not text_ok) and (not has_meaningful_attributes(elem)):
        parent = elem.getparent()
        if parent is not None:
            parent.remove(elem)
        return
# -------------------------------
# Haupt-Mapping-Logik
# -------------------------------
def apply_mapping(meta: dict,
                  template_tree: etree._ElementTree,
                  mappings):
    root = deepcopy(template_tree.getroot())
    for entry in mappings:
        field = entry["ckan_field"]
        pattern = entry["xml_path_pattern"]
        value = get_json_value(meta, field)
        if value is None:
            continue
        xpath = normalize_xpath(pattern)
        nodes = root.xpath(xpath, namespaces=NSMAP)
        if not nodes:
            continue

        if isinstance(value, list):
            # Felder, bei denen ISO19139 verlangt, dass der *Container* wiederholt wird
            CONTAINER_REPEAT_FIELDS = {
                "ident_keywords",
                "ident_accessconstraints",
                "ident_useconstraints",
                "ident_uselimitation",
                "ident_otherconstraints",
                "dataquality_scopedescription_dataset",
                "dataquality_scopedescription_other",
            }

            if field in CONTAINER_REPEAT_FIELDS:
                base_leaf = nodes[0]                 # z.B. gco:CharacterString oder gmd:MD_RestrictionCode
                repeat_elem = base_leaf.getparent()  # z.B. gmd:keyword / gmd:useLimitation / gmd:accessConstraints / gmd:dataset ...
                if repeat_elem is None:
                    continue
                repeat_parent = repeat_elem.getparent()  # z.B. gmd:MD_Keywords / gmd:MD_LegalConstraints / gmd:MD_ScopeDescription
                if repeat_parent is None:
                    continue

                # Alle vorhandenen Container dieses Typs entfernen (damit nicht alte + neue gemischt werden)
                for child in list(repeat_parent):
                    if child.tag == repeat_elem.tag:
                        repeat_parent.remove(child)

                # Pro Wert genau EINEN Container erzeugen
                for v in value:
                    new_container = deepcopy(repeat_elem)

                    # Leaf im neuen Container finden (gleiche Tag-Struktur wie im Template)
                    leaf_in_new = None
                    for e in new_container.iter():
                        if e.tag == base_leaf.tag:
                            leaf_in_new = e
                            break

                    if leaf_in_new is not None:
                        set_node_value(leaf_in_new, v)
                    else:
                        # Fallback: falls Template unerwartet ist
                        set_node_value(new_container, v)

                    repeat_parent.append(new_container)

                continue  # wichtig: Default-Listenlogik überspringen

            # Default-Listen-Handling (wie bisher)
            base_node = nodes[0]
            parent = base_node.getparent()
            for n in nodes:
                real_parent = n.getparent()
                if real_parent is not None:
                    real_parent.remove(n)
            for v in value:
                new_node = deepcopy(base_node)
                set_node_value(new_node, v)
                parent.append(new_node)

        else:
            for n in nodes:
                set_node_value(n, value)
    # danach: Resources, Referenzsysteme, Verteilungsformate und BBOX einbauen
    apply_resources_from_json(meta, root)
    apply_refsystem_from_json(meta, root)
    apply_distrib_format_from_json(meta, root)
    iso_type = meta.get("iso_type", "SV_ServiceIdentification")
    apply_bbox_from_json(meta, root, iso_type)
    # ident_date_ explizit setzen (unabhängig vom Mapping-Pfad)
    apply_ident_date_from_json(meta, root, iso_type)
    # zum Schluss: leere Elemente entfernen (z.B. leere serviceType)
    prune_empty_elements(root)
    return etree.ElementTree(root)
# -------------------------------
# Konsistenz-Check Mapping <-> XML
# -------------------------------
def check_mapping_coverage(meta: dict, mappings, root: etree._Element):
    """
    Prüft für alle Mapping-Felder:
      - wenn im Input ein Wert vorhanden ist (nicht None / nicht leere Liste / nicht leerer String),
      - ob der (angepasste) XPath im Ergebnis-XML mindestens einen Knoten trifft.
    Felder in SKIP_COVERAGE_FIELDS werden ignoriert, da sie über Speziallogik gesetzt werden.
    """
    missing = []
    for entry in mappings:
        field = entry["ckan_field"]
        if field in SKIP_COVERAGE_FIELDS:
            continue
        value = get_json_value(meta, field)
        if value is None or value == "" or value == []:
            continue
        xpath = normalize_xpath(entry["xml_path_pattern"])
        nodes = root.xpath(xpath, namespaces=NSMAP)
        if not nodes:
            missing.append((field, entry["xml_path_pattern"], value))
    if missing:
        print("Hinweis: folgende Mapping-Felder haben Werte im Input, aber im XML keine passenden Knoten gefunden:")
        for f, p, v in missing:
            print(f"  - {f} -> {p} (Wert: {repr(v)})")
    else:
        print("Konsistenzcheck: alle Mapping-Felder mit Werten haben passende XML-Knoten gefunden.")
# -------------------------------
# Use from other python script
# -------------------------------
def convert_metadata_dict(
    meta_dict: dict,
    template_xml: Union[str, Path],
    mapping_csv: Optional[Union[str, Path]] = None,
    *,
    do_coverage_check: bool = True,
) -> etree._ElementTree:
    """
    Wandelt ein Metadata-Dictionary (wie metadata.json)
    in einen ISO19139 XML-ElementTree um.
    Parameter:
      meta_dict        dict mit gleicher Struktur wie metadata.json
      mapping_csv      Pfad zur mapping.csv
      template_xml     Pfad zur ISO-Template-XML
      do_coverage_check  optional: Konsistenzcheck Mapping <-> XML
    Rückgabe:
      lxml.etree.ElementTree
    """
    mapping_path = Path(mapping_csv) if mapping_csv is not None else None
    template_path = Path(template_xml)
    if mapping_path is None:
            mappings = load_embedded_mapping()   # <-- Name ggf. anpassen!
    else:
        mappings = load_mapping_csv(mapping_path)
    iso_type = meta_dict.get("iso_type", "SV_ServiceIdentification")
    # Mapping an iso_type + ident_date_ anpassen
    adjust_mappings_for_iso_type_and_date(meta_dict, mappings, iso_type)
    template_tree = load_template_xml(template_path)
    result_tree = apply_mapping(meta_dict, template_tree, mappings)
    if do_coverage_check:
        check_mapping_coverage(meta_dict, mappings, result_tree.getroot())
    return result_tree
# -------------------------------
# CLI
# -------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Transformiere metadata.json mit mapping.csv in ISO19139-XML."
    )
    parser.add_argument(
        "--metadata",
        required=True,
        help="Pfad zu metadata.json",
    )
    parser.add_argument(
        "--mapping",
        required=False,
        help="Optional: Pfad zu mapping.csv (ckan field;xml path). Wenn weggelassen, wird das eingebettete Mapping benutzt.",
    )
    parser.add_argument(
        "--template",
        required=True,
        help="Pfad zur ISO19139-Template-XML (z.B. isodata.xml oder iso_template_clean.xml)",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Pfad zur Ausgabedatei (z.B. isodata_out.xml)",
    )
    args = parser.parse_args()
    metadata_path = Path(args.metadata)
    mapping_path = Path(args.mapping) if args.mapping else None
    template_path = Path(args.template)
    output_path = Path(args.output)
    meta = load_metadata(metadata_path)
    result_tree = convert_metadata_dict(
        meta_dict=meta,
        mapping_csv=mapping_path,
        template_xml=template_path,
        do_coverage_check=True,
    )
    result_tree.write(
        str(output_path),
        xml_declaration=True,
        encoding="utf-8",
        pretty_print=True,
    )
    print(f"ISO19139-XML geschrieben nach: {output_path}")
if __name__ == "__main__":
    main()
    