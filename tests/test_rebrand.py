import json
import re
import shutil
import tempfile
import unittest
from pathlib import Path

from helpers import FIXTURES

from patchwork import PatchworkError
from patchwork.rebrand import Brand, rebrand


class FakeRunner:
    """Stands in for FMUpgradeTool: applies the effect of each patch to the fixture export."""

    def __init__(self, ignore_theme=False):
        self.text = (FIXTURES / "mini-export.xml").read_text(encoding="utf-8")
        self.ignore_theme = ignore_theme
        self.patches = []

    def generate_guids(self, src, dest, force=False):
        shutil.copyfile(src, dest)

    def export_xml(self, src, out, force=False):
        out.write_text(self.text, encoding="utf-8")

    def apply(self, src, patch, dest, force=False):
        xml = patch.read_text(encoding="utf-8")
        self.patches.append(xml)
        if 'type="Theme"' in xml and not self.ignore_theme:
            name = re.search(r'<Theme Display="([^"]*)"', xml).group(1)
            self.text = self.text.replace('Display="Apex Blue"', f'Display="{name}"')
        added = re.search(r'<Field id="(\d+)" name="([^"]*)"', xml)
        if added:
            field = f'<Field id="{added.group(1)}" name="{added.group(2)}" fieldtype="Calculated" datatype="Binary">\n\t\t\t\t\t\t\t<UUID>BRAND-UUID</UUID>\n\t\t\t\t\t\t</Field>\n\t\t\t\t\t'
            fields = self.text.index("<FieldsForTables")
            end = self.text.index("</ObjectList>", fields)
            self.text = self.text[:end] + field + self.text[end:]
        if 'type="Layout"' in xml:
            self.text = re.sub(r'<FieldReference id="24" name="Logo"( repetition="1")? UUID="LOGO-UUID">', r'<FieldReference id="41" name="Brand Logo"\1 UUID="BRAND-UUID">', self.text)
        shutil.copyfile(src, dest)


class RebrandTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.src = self.tmp / "Invoice.fmp12"
        self.src.write_bytes(b"fmp12")
        (self.tmp / "logo.png").write_bytes(b"\x89PNG\r\n")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def brand(self, **extra):
        data = {"name": "Acme", "colors": {"0091CE": "#00475A"}, **extra}
        path = self.tmp / "brand.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        return Brand.load(path)

    def test_full_rebrand_with_logo(self):
        runner = FakeRunner()
        brand = self.brand(logo={"image": "logo.png", "replace": "Admin::Logo"})
        report = rebrand(self.src, self.tmp / "out.fmp12", brand, runner, say=lambda _: None)
        self.assertEqual(report.theme, "Acme")
        self.assertEqual(report.layouts, ["Dashboard"])
        self.assertEqual(report.logo_refs, 1)
        self.assertTrue((self.tmp / "out.fmp12").exists())
        self.assertIn("<AddAction>", runner.patches[0])
        self.assertIn('<Replace type="Theme" UUID="THEME-UUID">', runner.patches[0])
        self.assertIn('name="Brand Logo" repetition="1" UUID="BRAND-UUID"', runner.patches[1])
        self.assertFalse(report.work.exists())

    def test_silently_ignored_patch_is_detected(self):
        with self.assertRaises(PatchworkError) as caught:
            rebrand(self.src, self.tmp / "out.fmp12", self.brand(), FakeRunner(ignore_theme=True), say=lambda _: None)
        self.assertIn("missing", str(caught.exception))
        self.assertFalse((self.tmp / "out.fmp12").exists())

    def test_source_is_never_the_destination(self):
        with self.assertRaisesRegex(PatchworkError, "The destination is the source file"):
            rebrand(self.src, self.src, self.brand(), FakeRunner(), say=lambda _: None)

    def test_brand_file_is_validated(self):
        with self.assertRaisesRegex(PatchworkError, "Unknown key\\(s\\) in brand file: colour"):
            self.brand(colour={"a": "b"})
        with self.assertRaisesRegex(PatchworkError, "Logo image not found"):
            self.brand(logo={"image": "missing.png", "replace": "Admin::Logo"})
        with self.assertRaisesRegex(PatchworkError, "6-digit hex value like 2F5D50: BLUE"):
            self.brand(colors={"0091CE": "blue"})


if __name__ == "__main__":
    unittest.main()
