# Transpose arrays label to name

# Hauptkategorien
main_group_transpose = {
    'Datensatz und Dokumente': 'dataset',
    'Gerät / Ding': 'device',
    'Online-Anwendung': 'online-application',
    'Online-Dienst': 'online-service',
    'Portale': 'portal',
    'Software': 'software'
}
# Themen
topic_group_transpose = {
    'Arbeiten': 'work',
    'Bauen': 'construction',
    'Bildung': 'education',
    'Energie': 'energy',
    'Gesundheit': 'health',
    'Gewerbe / Handwerk': 'craft',
    'Handel': 'trade',
    'Informations-Technologie': 'information-technology',
    'Kultur': 'culture',
    'Landwirtschaft': 'agriculture',
    'Mobilität': 'mobility',
    'Stadtplanung': 'urban-planning',
    'Tourismus & Freizeit': 'tourism',
    'Umwelt': 'environment',
    'Verwaltung': 'administration',
    'Wohnen': 'living'
}
# Organisation
org_transpose = {
    'Direktroium (DIR)': 'dir',
    'Gesundheitsreferat (GSR)': 'gsr',
    'Referat für Klima- und Umweltschutz (RKU)': 'rku',
    'Kommunalreferat (KR)': 'kr',
    'Sozialreferat (SOZ)': 'soz',
    'Kreisverwaltungsreferat (KVR)': 'kvr',
    'Referat für Stadtplanung und Bauordnung (PLAN)': 'plan',
    'Referat für Bildung und Sport (RBS)': 'rbs',
    'Mobilitätsreferat (MOR)': 'mor',
    'Baureferat (BAU)': 'bau',
    'KVR-GL (Kreisverwaltungsreferat - Geschäftsleitung)': 'kvr-gl',
    'BAU-J (Baureferat - Ingenieurbau)': 'bau-j',
    'BAU-T (Baureferat - Tiefbau)': 'bau-t',
    'MOR-GB2 (Mobilitätsreferat - Verkehrs- und Bezirksmanagement)': 'mor-gb2',
    'RKU-II-1 (Referat für Klima- und Umweltschutz - Geschäftsbereich Klimaschutz und Energie)': 'rku-ii-1',
    'PLAN-HAII (Referat für Stadtplanung und Bauordnung - Stadtplanung)': 'plan-haii',
    'RKU-GB-IV (Referat für Klima- und Umweltschutz - Umweltschutz)': 'rku-gb-iv',
    'GSR-SFM-GV (Gesundheitsreferat - Abteilung GV, Gräberverwaltung, Grabangelegenheiten Friedhof, Zentrale Bestattungsformalitäten, Bestattungen von Amts wegen': 'gsr-sfm-gv',
    'MOR-RL (Mobilitätsreferat - Referatsleitung)': 'mor-rl',
    'KR-BewA (Kommunalreferat - Bewertungsamt)': 'kr-bewa',
    'BAU-G (Baureferat - Gartenbau)': 'bau-g',
    'PLAN-HAIV (Referat für Stadtplanung und Bauordnung - Lokalbaukommission (LBK))': 'plan-haiv',
    'D-I-STA (Direktorium - Informationsbereitstellung / Anwenderbetreuung)': 'd-i-sta',
    'RKU-GB-I (Referat für Klima- und Umweltschutz - Umweltvorsorge)': 'rku-gb-i',
    'KR-GSM (Kommunalreferat - GeodatenService München)': 'kr-gsm',
    'PLAN-SG (Referat für Stadtplanung und Bauordnung - Referatsgeschäftsleitung)': 'plan-sg',
    'RKU-GB-III (Referat für Klima- und Umweltschutz - Naturschutz und Biodiversität)': 'rku-gb-iii',
    'KVR-I (Sicherheit und Ordnung, Prävention)': 'kvr-i',
    'PLAN-HAIII (Referat für Stadtplanung und Bauordnung - Stadtsanierung und Wohnungsbau)': 'plan-haiii',
    'RBS-A (Referat für Bildung und Sport - Allgemeinbildende Schulen)': 'rbs-a',
    'S-GL (Sozialreferat - Geschäftsleitung)': 's-gl',
    'RBS-ZIM (Referat für Bildung und Sport - Zentrales Immobilienmanagement)': 'rbs-zim',
    'PLAN-HAI (Referat für Stadtplanung und Bauordnung - Stadtentwicklungsplanung)': 'plan-hai',
    'MOR-GB1 (Mobilitätsreferat - Strategie)': 'mor-gb1',
    'RKU-GB-II (Referat für Klima- und Umweltschutz - Klimaschutz und Energie)': 'rku-gb-ii',
    'MOR-GL (Mobilitätsreferat - Geschäftsleitung)': 'mor-gl'
}
# Bool
bool_transpose = {
    'Nein': 'false',
    'nein': 'false',
    'Ja': 'true',
    'ja': 'true'
}
# Datentyp für Sheet Datenverzeichnis
dv_datentyp_transpose = {
    'BLOB': 'blob',
    'DATE/DATUM': 'date',
    'FLOAT': 'float8',
    'GEOMETRY/SDO_GEOMETRY': 'sdo_geometry',
    'GEOMETRY/ST_GEOMETRY': 'st_geometry',
    'OBJECT-ID/NUMBER': 'number_',
    'TEXT/CHAR': 'char',
    'TEXT/NVARCHAR2': 'nvarchar2',
    'TEXT/VARCHAR2': 'varchar2',
    'TIMESTAMP(6)': 'timestamp',
    'TIMESTAMP(9)': 'timestamp9'
}

# Restliche
update_zyklus_transpose = {
    "Auf Anforderung": "auf_anforderung",
    "15-minütig": "15-minuetig",
    "Stündlich": "stuendlich",
    "Täglich": "taeglich",
    "Wöchentlich": "woechentlich",
    "Monatlich": "monatlich",
    "Quartalsweise": "quartalsweise",
    "Jährlich": "jaehrlich",
    "Zweijährlich": "zweijaehrlich",
    "Keine Aktualisierung": "kein",
    "k.A.": "k.A."
}

objekttyp_transpose = {
    "Punkt": "punkt",
    "Linie": "linie",
    "Fläche": "flaeche",
    "Raster (ArcGIS-Raster)": "raster",
    "Sachdaten": "sachdaten",
    "ANNO": "anno",
    "Multipatch": "multipatch",
    "k.A.": "k.A."
}
lagegenauigkeit_transpose = {
    None: "",
    "Tachymeter (1 cm)": "tachymeter",
    "Diff-GPS / SAPOS (3 cm)": "diff_gps",
    "GPS (Handy o.ä.) (1 m)": "gps",
    "Satellit (1 m)": "satellit",
    "Auf Basis Kataster (Flurstücke / Gebäude) (3 cm)": "kataster",
    "Auf Basis Baublöcke (30 cm)": "baubloecke",
    "Auf Basis Luftbild (30 cm)": "luftbild",
    "Auf Basis Stadtbezirke (-teil -viertel)(10m)": "stadtbezirk",
    "Auf Basis Stadtplan (10m)": "stadtplan",
    "k.A.": "k.A."
}
archivwuerdigkeit_transpose = {
    "Noch offen": "noch_offen",
    "Archivwürdig": "archivwuerdig",
    "Nicht archivwürdig": "nicht_archivwuerdig",
    "k.A.": "k.A."
}
lhm_intern_transpose = {
    "Uneingeschränkt": "uneingeschraenkt",
    "Mit Einschränkungen": "eingeschraenkt",
    "Kein Zugriff": "kein_zugriff",
    "k.A.": "k.A."
}

geoinfoweb_transpose = {
    "Alle Nutzer": "alle_nutzer",
    "Bestimmte Organisationseinheiten": "organisationseinheiten",
    "Bestimmte (\u00fcbergreifende) Gruppe(n)": "gruppen",
    "Ausgenommen Bezirksausschüsse": "ohne_bezirksausschuesse",
    "Keine": "keine"
}

geoserviceplattform_transpose = {
    "Alle Nutzer": "alle_nutzer",
    "Bestimmte Organisationseinheiten": "organisationseinheiten",
    "Bestimmte (\u00fcbergreifende) Gruppe(n)": "gruppen",
    "Ausgenommen Bezirksausschüsse": "ohne_bezirksausschuesse",
    "Keine": "keine"
}

lhm_extern_transpose = {
    "Mit Nutzungsbedingungen/ -vereinbarungen": "nutzungsbedingungen",
    "Mit Einschränkungen": "einschraenkungen",
    "Kein Zugriff": "kein_zugriff",
    "k.A.": "k.A."
}
nutzungsoptionen_transpose = {
    "Nutzung für Backendverarbeitung und Präsentation": "backend_praesentation",
    "Nutzung durch externe Auftragnehmer mit Nutzungsbedingungen/ -vereinbarungen": "externe_auftragnehmer",
    "Nutzung durch Externe (nicht Auftragnehmer) mit Nutzungsbedingungen/ -vereinbarungen": "externe_nicht_auftragnehmer",
    "Einschränkungen bei Inhalten oder Attributen": "einschraenkungen_inhalte_attribute"
}
datenabgabe_extern_transpose = {
    "Keine": "keine",
    "im Rahmen der Nutzungsbedingungen": "im_rahmen_nutzungsbedingungen",
    "über den Rahmen der Nutzungsbedingungen hinaus": "ueber_rahmen_nutzungsbedingungen"
}
open_data_transpose = {
    "Ja": "ja",
    "Nur bestimmte Attribute & Inhalte": "teilweise",
    "Nein": "nein",
    "k.A.": "k.A."
}
hvd_transpose ={
    "Ja": "ja",
    "Nur bestimmte Attribute & Inhalte": "teilweise",
    "Nein": "nein",
    "k.A.": "k.A."
}
hvd_kategorie_transpose = {
    "Georaum": "georaum",
    "Erdbeobachtung und Umwelt": "erdbeobachtung_umwelt",
    "Meteorologie": "meteorologie",
    "Statistik": "statistik",
    "Unternehmen und Eigentümerschaft von Unternehmen": "unternehmen",
    "Mobilität": "mobilitaet",
    #"-": "keine",
    '"-"': "keine",
    "k.A.": "k.A."
}

schema_transpose = {
    "BAUG": "baug",
    "BAUJ": "bauj",
    "BAUT": "baut",
    "BEWA": "bewa",
    "DIRSTAT": "dirstat",
    "GSR": "gsr",
    "KVR": "kvr",
    "KVRBRAND": "kvrbrand",
    "MOR": "mor",
    "PLAN": "plan",
    "RGU": "rgu",
    "RKU": "rku",
    "SCU": "scu",
    "SOZ": "soz",
    "VABLOCK": "vablock",
    "VAGGD": "vaggd",
    "VAGRUND": "vagrund",
    "VAORTHO": "vaortho",
    "VAREGIO": "varegio",
    # MB_CHANGE FOR DOWNLOAD BUTTON ###
    "MOBIDAM": "mobidam",
    "MOBIDAM_SST": "mobidam_sst",
    ###################################
    "VA3D": "va3d",
    # PLAN-DB
    "BAU": "bau",
    "BPLAN": "bplan",
    "DENK": "denk",
    "ENP": "enp",
    "EWO": "ewo",
    "FIS": "fis",
    "FNP": "fnp",
    "GEB": "geb",
    "GEN": "gen",
    "GRENZ": "grenz",
    "GRUEN": "gruen",
    "HAII_PRIO": "haii_prio",
    "INNENSTADT": "innenstadt",
    "LBK": "lbk",
    "REG": "reg",
    "SIED": "sied",
    "SOZ": "soz",
    "STAPL": "stapl",
    "UNB": "unb",
    "ZEN": "zen"
}

sichtbarkeit_transpose = {
    "Privat": True,
    "Öffentlich":False
}

datenquelle_transpose = {
    "Geodatenpool": "geodatenpool",
    "Mobidam":"mobidam",
    "PLAN-DB": "plan-db"
}

resource_format_transpose = {
    "Oracle-DB": "oracle-db",
    "XLSX": "XLSX",
    "PDF": "PDF",
    "WCS": "WCS",
    "WFS": "WFS",
    "WMS": "WMS",
    "WMTS": "WMTS",
    "WMTS-KVP": "wmts_kvp",
    "JSON": "JSON",
    "XML/GML": "XML/GML",
    "ArcGIS Kartenservice": "ArcGIS Kartenservice",
    "ArcGIS Feature Service": "arcgis_rest",
    "ArcGIS Map Service": "arcgis_rest_img",
    "URL": "URL",
    "Link":"Link"
}


# Reversing keys and values for reverse transpose arrays

main_group_transpose_r = {value: key for key, value in main_group_transpose.items()}
topic_group_transpose_r = {value: key for key, value in topic_group_transpose.items()}
org_transpose_r = {value: key for key, value in org_transpose.items()}
bool_transpose_r = {value: key for key, value in bool_transpose.items()}
dv_datentyp_transpose_r = {value: key for key, value in dv_datentyp_transpose.items()}
update_zyklus_transpose_r = {value: key for key, value in update_zyklus_transpose.items()}
objekttyp_transpose_r = {value: key for key, value in objekttyp_transpose.items()}
lagegenauigkeit_transpose_r = {value: key for key, value in lagegenauigkeit_transpose.items()}
archivwuerdigkeit_transpose_r = {value: key for key, value in archivwuerdigkeit_transpose.items()}
lhm_intern_transpose_r = {value: key for key, value in lhm_intern_transpose.items()}
geoinfoweb_transpose_r = {value: key for key, value in geoinfoweb_transpose.items()}
geoserviceplattform_transpose_r = {value: key for key, value in geoserviceplattform_transpose.items()}
lhm_extern_transpose_r = {value: key for key, value in lhm_extern_transpose.items()}
nutzungsoptionen_transpose_r = {value: key for key, value in nutzungsoptionen_transpose.items()}
datenabgabe_extern_transpose_r = {value: key for key, value in datenabgabe_extern_transpose.items()}
open_data_transpose_r = {value: key for key, value in open_data_transpose.items()}
hvd_transpose_r = {value: key for key, value in hvd_transpose.items()}
hvd_kategorie_transpose_r = {value: key for key, value in hvd_kategorie_transpose.items()}
schema_transpose_r = {value: key for key, value in schema_transpose.items()}
sichtbarkeit_transpose_r = {value: key for key, value in sichtbarkeit_transpose.items()}
datenquelle_transpose_r = {value: key for key, value in datenquelle_transpose.items()}
resource_format_transpose_r = {value: key for key, value in resource_format_transpose.items()}
