from pathlib import Path
import unittest

from ckanext.lhm.gp_to_iso1939 import NSMAP, convert_metadata_dict


TEMPLATE = Path(__file__).resolve().parents[1] / "schemas" / "iso_template.xml"
ONLINE_PATH = (
    "./gmd:distributionInfo/gmd:MD_Distribution/gmd:transferOptions/"
    "gmd:MD_DigitalTransferOptions/gmd:onLine/gmd:CI_OnlineResource"
)


class ResourceLocatorTest(unittest.TestCase):
    def test_resource_fields_follow_their_resource(self):
        metadata = {
            "resources": [
                {
                    "url": "https://example.org/wms",
                    "name": "WMS",
                    "description": "Kartendienst",
                    "resource_locator_protocol": "OGC:WMS",
                    "resource_locator_function": "information",
                },
                {
                    "url": "https://example.org/download",
                    "name": "Download",
                    "description": "Datei zum Herunterladen",
                    "resource_locator_protocol": "WWW:DOWNLOAD-1.0-http--download",
                    "resource_locator_function": "download",
                },
                {"url": "https://example.org/other"},
                {"name": "No URL"},
            ]
        }

        tree = convert_metadata_dict(metadata, TEMPLATE, do_coverage_check=False)
        online_resources = tree.getroot().xpath(ONLINE_PATH, namespaces=NSMAP)

        self.assertEqual(len(online_resources), 3)
        expected = [
            ("https://example.org/wms", "Kartendienst", "OGC:WMS", "information"),
            (
                "https://example.org/download",
                "Datei zum Herunterladen",
                "WWW:DOWNLOAD-1.0-http--download",
                "download",
            ),
            ("https://example.org/other", None, None, None),
        ]
        for online, (url, description, protocol, function) in zip(online_resources, expected):
            self.assertEqual(online.xpath("string(./gmd:linkage/gmd:URL)", namespaces=NSMAP), url)
            self.assertEqual(
                online.xpath("string(./gmd:description/gco:CharacterString)", namespaces=NSMAP)
                or None,
                description,
            )
            self.assertEqual(
                online.xpath("string(./gmd:protocol/gco:CharacterString)", namespaces=NSMAP)
                or None,
                protocol,
            )
            codes = online.xpath(
                "./gmd:function/gmd:CI_OnLineFunctionCode", namespaces=NSMAP
            )
            self.assertEqual(codes[0].get("codeListValue") if codes else None, function)


if __name__ == "__main__":
    unittest.main()
