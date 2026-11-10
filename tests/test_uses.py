import unittest

from helpers import mini_export

from patchwork.uses import find_uses


class UsesTests(unittest.TestCase):
    def setUp(self):
        self.export = mini_export()

    def test_field_reference_and_bare_mention_in_its_table(self):
        found = find_uses(self.export, "field", "Admin::Logo")
        self.assertEqual(dict(found.references), {"layout Dashboard": 1})
        self.assertEqual(dict(found.mentions), {"field Admin::Logo New": 1})

    def test_text_inside_quotes_is_not_a_mention(self):
        self.assertNotIn("(2x)", find_uses(self.export, "field", "Admin::Logo").report())

    def test_custom_function_is_found_by_name(self):
        found = find_uses(self.export, "custom-function", "CardWindowHeight")
        self.assertEqual(dict(found.mentions), {"field Admin::Logo New": 1})
        self.assertFalse(found.references)

    def test_an_object_does_not_use_itself(self):
        self.assertEqual(find_uses(self.export, "table", "Admin").report(), "Nothing in the file uses table Admin.")
        self.assertFalse(find_uses(self.export, "script", "Close Window").references)

    def test_theme_used_by_layouts(self):
        found = find_uses(self.export, "theme", "Apex Blue")
        self.assertEqual(set(found.references), {"layout Dashboard", "layout Plain & Simple"})


if __name__ == "__main__":
    unittest.main()
