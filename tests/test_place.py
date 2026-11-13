import re
import unittest

from helpers import FIXTURES
from patchwork import PatchworkError
from patchwork.export import Export
from patchwork.place import own_bounds, place_field, top_level


def placed(**kwargs):
    from patchwork.place import place_field

    export = Export.load(FIXTURES / "layout-export.xml")
    args = {"layout": "Clients Details", "field": "Clients::Loyalty Tier", "near": "Email"} | kwargs
    xml, _ = place_field(export, **args)
    return xml


def tops(xml: str) -> dict[str, float]:
    """Top of each top-level object, keyed by its field name or text."""
    found = {}
    for part in re.finditer(r"<Part [\s\S]*?</Part>", xml):
        for obj in top_level(part.group(0), 0):
            key = re.search(r'<FieldReference [^>]*name="([^"]*)"', obj.xml) or re.search(r"CDATA\[([^\]]*)", obj.xml)
            found[key.group(1) if key else re.search(r'type="([^"]*)"', obj.xml).group(1)] = obj.box.top
    return found


class PlaceFieldTests(unittest.TestCase):
    def test_inserts_a_row_below_with_a_copied_label(self):
        xml = placed(label="Tier")
        self.assertEqual(
            tops(xml),
            {"Rectangle": 0, "Email": 40, "Tier": 70, "Loyalty Tier": 90, "Notes": 120, "Side note": 20, "Text": 360},
        )
        self.assertIn('size="350" absolute="0"', xml)
        self.assertIn('size="50" absolute="350"', xml)
        self.assertIn('<ObjectList membercount="7">', xml)
        self.assertIn('<TableOccurrenceReference id="1065091" name="Clients" UUID="TO-UUID">', xml)

    def test_background_rectangle_grows_with_the_row(self):
        rect = re.search(r'<LayoutObject [^>]*type="Rectangle"[\s\S]*?</LayoutObject>', placed()).group(0)
        self.assertEqual(own_bounds(rect).bottom, 350)

    def test_new_field_points_at_its_new_label_with_fresh_ids(self):
        xml = placed()
        field = re.search(
            r'<LayoutObject id="(\d+)"[^>]*>(?:(?!</LayoutObject>)[\s\S])*?TIER-UUID[\s\S]*?</LayoutObject>', xml
        ).group(0)
        label = re.search(r'<LayoutObject id="(\d+)"[^>]*>(?:(?!</LayoutObject>)[\s\S])*?CDATA\[Loyalty Tier\]', xml)
        self.assertIn(f"<Label>{label.group(1)}</Label>", field)
        self.assertNotIn("TabOrder", field)
        self.assertNotIn("EDIT-UUID", field)
        self.assertEqual(xml.count("<UUID>EDIT-UUID</UUID>"), 1)

    def test_the_row_gap_is_copied_up_to_40_points(self):
        text = (FIXTURES / "layout-export.xml").read_text(encoding="utf-8")
        for notes_top, tier_top in ((110, 130), (115, 100)):
            with self.subTest(gap=notes_top - 70):
                moved = text.replace(
                    '<Bounds top="70" left="10" bottom="100"', f'<Bounds top="{notes_top}" left="10" bottom="200"'
                )
                xml, _ = place_field(Export(moved), "Clients Details", "Clients::Loyalty Tier", "Email")
                self.assertEqual(tops(xml)["Loyalty Tier"], tier_top)

    def test_right_places_the_field_and_label_beside_without_moving_anything(self):
        text = (FIXTURES / "layout-export.xml").read_text(encoding="utf-8")
        clear = text.replace('<Bounds top="20" left="210" bottom="70"', '<Bounds top="200" left="210" bottom="250"')
        xml, _ = place_field(Export(clear), "Clients Details", "Clients::Loyalty Tier", "Email", side="right")
        self.assertEqual(xml.count('<Bounds top="20" left="210" bottom="40" right="400"></Bounds>'), 1)
        self.assertEqual(xml.count('<Bounds top="40" left="210" bottom="70" right="400"></Bounds>'), 1)
        before, after = tops(clear), tops(xml)
        self.assertEqual({k: after[k] for k in before}, before)
        self.assertIn('<ObjectList membercount="7">', xml)
        self.assertIn('size="300" absolute="0"', xml)

    def test_right_is_refused_past_the_layout_edge(self):
        text = (FIXTURES / "layout-export.xml").read_text(encoding="utf-8").replace('width="600"', 'width="390"')
        with self.assertRaisesRegex(PatchworkError, "^No room right of 'Email': it would go past the edge"):
            place_field(Export(text), "Clients Details", "Clients::Loyalty Tier", "Email", side="right")

    def test_side_must_be_below_or_right(self):
        with self.assertRaisesRegex(PatchworkError, r"^side is below or right\.$"):
            placed(side="above")

    def test_below_is_refused_when_a_field_is_in_the_way(self):
        text = (FIXTURES / "layout-export.xml").read_text(encoding="utf-8")
        text = text.replace('<Bounds top="70" left="10" bottom="100"', '<Bounds top="60" left="10" bottom="100"')
        with self.assertRaisesRegex(
            PatchworkError, "^No room below 'Email': it would cover field Notes. Try side=right"
        ):
            place_field(Export(text), "Clients Details", "Clients::Loyalty Tier", "Email")

    def test_right_is_refused_when_something_is_there(self):
        with self.assertRaisesRegex(PatchworkError, "would cover object 5"):
            placed(side="right")

    def test_a_field_already_on_the_layout_is_refused(self):
        with self.assertRaisesRegex(PatchworkError, "already on"):
            placed(field="Clients::Notes")

    def test_near_must_be_on_the_layout(self):
        with self.assertRaisesRegex(PatchworkError, "No field 'Phone'"):
            placed(near="Phone")


if __name__ == "__main__":
    unittest.main()
