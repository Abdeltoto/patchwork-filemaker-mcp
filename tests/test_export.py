import tempfile
import unittest
from pathlib import Path

from helpers import FIXTURES, mini_export
from patchwork import PatchworkError
from patchwork.export import Export


class ExportTests(unittest.TestCase):
    def setUp(self):
        self.export = mini_export()

    def test_layout_uuid_is_the_direct_child_not_the_first_object(self):
        self.assertEqual(self.export.layout("Dashboard").uuid, "LAYOUT-UUID")

    def test_layout_names_are_unescaped(self):
        self.assertEqual(self.export.layout("Plain & Simple").uuid, "PLAIN-UUID")

    def test_theme_without_uuid_asks_for_guids(self):
        with self.assertRaises(PatchworkError) as caught:
            self.export.theme("Bare")
        self.assertIn("patchwork guids", str(caught.exception))

    def test_theme_by_display_or_internal_name(self):
        self.assertEqual(self.export.theme("Apex Blue").uuid, "THEME-UUID")
        self.assertEqual(self.export.theme("com.filemaker.theme.apex_blue").name, "Apex Blue")

    def test_main_theme_is_the_most_used(self):
        self.assertEqual(self.export.main_theme(), "com.filemaker.theme.apex_blue")

    def test_field_catalog_and_next_id(self):
        catalog_uuid, base_ref, _ = self.export.field_catalog("Admin")
        self.assertEqual(catalog_uuid, "CATALOG-UUID")
        self.assertIn('UUID="BASE-UUID"', base_ref)
        self.assertEqual(self.export.next_field_id("Admin"), 41)

    def test_field_references_counts_layout_objects(self):
        self.assertEqual(self.export.field_references("LOGO-UUID"), 1)
        self.assertEqual(self.export.field_references("NEW-UUID"), 0)

    def test_unknown_names_raise_clear_errors(self):
        for call, message in (
            (lambda: self.export.layout("Nope"), "Layout not found: Nope"),
            (lambda: self.export.field("Admin", "Nope"), "Field not found: Admin::Nope"),
            (lambda: self.export.field_catalog("Nope"), "Base table not found: Nope"),
        ):
            with self.assertRaisesRegex(PatchworkError, message):
                call()

    def test_rejects_a_non_export(self):
        with self.assertRaisesRegex(PatchworkError, "not a FileMaker Save-as-XML export"):
            Export("<FMUpgradeToolPatch/>")

    def test_loads_utf16_exports(self):
        text = (FIXTURES / "mini-export.xml").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "utf16.xml"
            path.write_bytes(text.encode("utf-16"))
            self.assertEqual(Export.load(path).layout("Dashboard").uuid, "LAYOUT-UUID")


if __name__ == "__main__":
    unittest.main()
