import tempfile
import unittest
from pathlib import Path

from helpers import TEAL, mini_export

from patchwork import PatchworkError
from patchwork import build


class BuildTests(unittest.TestCase):
    def setUp(self):
        self.export = mini_export()

    def test_recolor_keeps_alpha_and_ignores_unmapped_colors(self):
        css = "rgba(0%,56.8627%,80.7843%,0.2) rgba(100%,100%,100%,1)"
        out = build.recolor(css, {"#0091CE": "#00475A"})
        self.assertEqual(out, "rgba(0%,27.8431%,35.2941%,0.2) rgba(100%,100%,100%,1)")

    def test_palette_counts_colors_most_frequent_first(self):
        css = "rgba(0%,56.8627%,80.7843%,1) rgba(100%,100%,100%,1) rgba(0%,56.8627%,80.7843%,0.5)"
        self.assertEqual(build.palette(css), [("0091CE", 2), ("FFFFFF", 1)])

    def test_recolor_rejects_a_bad_color(self):
        with self.assertRaisesRegex(PatchworkError, "6-digit hex value like 2F5D50: TEAL"):
            build.recolor("", {"0091CE": "teal"})

    def test_theme_patch_replaces_by_uuid_with_new_colors_fonts_and_name(self):
        patch = build.theme_patch(
            self.export, "Apex Blue", "Acme", {"0091CE": "00475A"}, {"HelveticaNeue,HelveticaNeue": "Georgia,Georgia"}
        )
        self.assertIn('<Replace type="Theme" UUID="THEME-UUID">', patch)
        self.assertIn('Display="Acme"', patch)
        self.assertIn(TEAL, patch)
        self.assertIn("-fm-font-family(Georgia,Georgia)", patch)
        self.assertTrue(
            patch.startswith('<?xml version="1.0" encoding="UTF-8"?>\n<FMUpgradeToolPatch version="2.3.0.0">')
        )

    def test_add_field_uses_the_catalog_and_next_id(self):
        field = build.field_xml(self.export, "Admin", "Status", "Text", comment="State")
        patch = build.add_field_patch(self.export, "Admin", field)
        self.assertIn("<UUID>CATALOG-UUID</UUID>\n\t\t\t\t\t<TagList></TagList>", patch)
        self.assertIn('<FieldsForTables membercount="1">', patch)
        self.assertIn('<Field id="41" name="Status" fieldtype="Normal" datatype="Text"', patch)

    def test_add_field_refuses_an_existing_name(self):
        with self.assertRaisesRegex(PatchworkError, "Admin::Logo already exists"):
            build.field_xml(self.export, "Admin", "Logo", "Container")

    def test_calc_field_carries_its_context(self):
        field = build.field_xml(
            self.export, "Admin", "Logo Calc", "Container", is_global=True, calc='Base64Decode ( "AA==" ; "x.png" )'
        )
        self.assertIn('fieldtype="Calculated" datatype="Binary"', field)
        self.assertIn('global="True"', field)
        self.assertIn('name="Admin" UUID="TO-UUID"', field)

    def test_calc_too_long_is_refused(self):
        with self.assertRaisesRegex(PatchworkError, "Calculation too long"):
            build.field_xml(self.export, "Admin", "Big", "Text", calc="x" * (build.CALC_MAX_CHARS + 1))

    def test_image_calc_embeds_the_png(self):
        with tempfile.TemporaryDirectory() as tmp:
            png = Path(tmp) / "logo.png"
            png.write_bytes(b"\x89PNG\r\n")
            self.assertEqual(build.image_calc(png), 'Base64Decode ( "iVBORw0K" ; "logo.png" )')

    def test_layouts_patch_only_touches_changed_layouts_and_keeps_repetition(self):
        patch, names = build.layouts_patch(
            self.export, None, {"0091CE": "00475A"}, {}, ("Admin::Logo", "Admin::Logo New")
        )
        self.assertEqual(names, ["Dashboard"])
        self.assertIn('<Replace type="Layout" UUID="LAYOUT-UUID">', patch)
        self.assertIn('<FieldReference id="40" name="Logo New" repetition="1" UUID="NEW-UUID">', patch)
        self.assertIn(TEAL, patch)
        self.assertNotIn("PLAIN-UUID", patch)

    def test_layouts_patch_rejects_unknown_layouts(self):
        with self.assertRaisesRegex(PatchworkError, "Layout not found: Missing"):
            build.layouts_patch(self.export, ["Missing"])

    def test_swap_refuses_fields_from_two_tables(self):
        with self.assertRaisesRegex(PatchworkError, "same table"):
            build.layouts_patch(self.export, None, {}, {}, ("Admin::Logo", "Other::Logo"))

    def test_extract_layout_wraps_the_full_block(self):
        patch = build.extract_layout_patch(self.export, "Plain & Simple")
        self.assertIn('<Replace type="Layout" UUID="PLAIN-UUID">', patch)
        self.assertIn('<Layout id="6" name="Plain &amp; Simple" width="800">', patch)


if __name__ == "__main__":
    unittest.main()
