import re
import unittest

from helpers import FIXTURES

from patchwork import PatchworkError
from patchwork.export import Export
from patchwork.place import own_bounds, top_level


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
        self.assertEqual(tops(xml), {"Rectangle": 0, "Email": 40, "Tier": 70, "Loyalty Tier": 90, "Notes": 120,
                                     "Side note": 20, "Text": 360})
        self.assertIn('size="350" absolute="0"', xml)
        self.assertIn('size="50" absolute="350"', xml)
        self.assertIn('<ObjectList membercount="7">', xml)
        self.assertIn('<TableOccurrenceReference id="1065091" name="Clients" UUID="TO-UUID">', xml)

    def test_background_rectangle_grows_with_the_row(self):
        rect = re.search(r'<LayoutObject [^>]*type="Rectangle"[\s\S]*?</LayoutObject>', placed()).group(0)
        self.assertEqual(own_bounds(rect).bottom, 350)

    def test_new_field_points_at_its_new_label_with_fresh_ids(self):
        xml = placed()
        field = re.search(r'<LayoutObject id="(\d+)"[^>]*>(?:(?!</LayoutObject>)[\s\S])*?TIER-UUID[\s\S]*?</LayoutObject>', xml).group(0)
        label = re.search(r'<LayoutObject id="(\d+)"[^>]*>(?:(?!</LayoutObject>)[\s\S])*?CDATA\[Loyalty Tier\]', xml)
        self.assertIn(f"<Label>{label.group(1)}</Label>", field)
        self.assertNotIn("TabOrder", field)
        self.assertNotIn("EDIT-UUID", field)
        self.assertEqual(xml.count("<UUID>EDIT-UUID</UUID>"), 1)

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
