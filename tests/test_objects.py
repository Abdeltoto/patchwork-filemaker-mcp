import unittest

from helpers import mini_export

from patchwork import PatchworkError, objects
from patchwork.export import Export


class ObjectTests(unittest.TestCase):
    def setUp(self):
        self.export = mini_export()

    def test_items_skip_folders(self):
        self.assertEqual([i.name for i in objects.items(self.export, "scripts")], ["Close Window"])
        self.assertEqual(objects.find(self.export, "script", "Close Window").uuid, "SCRIPT-UUID")

    def test_items_do_not_depend_on_attribute_order(self):
        self.assertEqual([i.name for i in objects.items(self.export, "tables")], ["Admin"])

    def test_value_list_uuid_is_its_own_not_the_first_found(self):
        self.assertEqual(objects.find(self.export, "value-list", "Industries").uuid, "VL-UUID")

    def test_show_script_includes_its_steps(self):
        text = objects.show(self.export, "script", "Close Window")
        self.assertIn('<Script id="28" name="Close Window">', text)
        self.assertIn("Closes the window", text)

    def test_show_step_finds_a_real_example(self):
        self.assertIn('name="# (comment)"', objects.show(self.export, "step", "# (comment)"))
        with self.assertRaises(PatchworkError):
            objects.show(self.export, "step", "Set Field")

    def test_add_value_list_gets_next_id_catalog_and_uuid(self):
        action = objects.add_object(self.export, "value-list", objects.value_list_xml("Status", ["Active", "Archived"]))
        self.assertIn("<UUID>VL-CATALOG-UUID</UUID>", action)
        self.assertIn('<ValueList id="3" name="Status">', action)
        self.assertIn("Active\rArchived", action)
        self.assertRegex(action, r"<UUID>[0-9A-F-]{36}</UUID>")

    def test_add_custom_function_goes_in_an_object_list(self):
        action = objects.add_object(self.export, "custom-function", objects.custom_function_xml("Hello", ["who"], '"Hi " & who'))
        self.assertIn('<ObjectList membercount="1">', action)
        self.assertIn('<CustomFunction id="27" name="Hello" access="All">', action)
        self.assertIn("<Display>Hello ( who )</Display>", action)

    def test_add_refuses_duplicates(self):
        with self.assertRaises(PatchworkError):
            objects.add_object(self.export, "value-list", objects.value_list_xml("Industries", ["x"]))

    def test_add_script_with_steps_renumbers_and_renews(self):
        steps = objects.show(self.export, "step", "# (comment)")
        action = objects.add_script(self.export, "New Script", steps + "\n" + steps)
        self.assertIn('<Script id="29" name="New Script">', action)
        self.assertIn('<ObjectList membercount="2">', action)
        self.assertIn('index="0"', action)
        self.assertIn('index="1"', action)
        self.assertNotIn("hash=", action)
        self.assertNotIn("STEP-UUID", action)

    def test_append_steps_continues_the_index(self):
        action = objects.append_steps(self.export, "Close Window", objects.show(self.export, "step", "# (comment)"))
        self.assertIn('<ScriptReference id="28" name="Close Window" UUID="SCRIPT-UUID">', action)
        self.assertIn('index="1"', action)

    def test_set_steps_deletes_old_steps_then_adds(self):
        action = objects.set_steps(self.export, "Close Window", objects.show(self.export, "step", "# (comment)"))
        self.assertLess(action.index("<DeleteAction>"), action.index("<AddAction>"))
        self.assertIn('<ItemReference UUID="STEP-UUID" type="ScriptStepReference">', action)

    def test_replace_and_delete_use_the_object_uuid(self):
        xml = objects.show(self.export, "value-list", "Industries").replace("Retail", "Services")
        self.assertIn('<Replace type="ValueList" UUID="VL-UUID">', objects.replace_object(self.export, "value-list", "Industries", xml))
        self.assertIn('UUID="SCRIPT-UUID" type="ScriptReference"', objects.delete_object(self.export, "script", "Close Window"))
        field = objects.delete_object(self.export, "field", "Admin::Logo")
        self.assertIn('<ItemReference UUID="LOGO-UUID" type="FieldReference">', field)
        self.assertIn('<BaseTableReference id="129" name="Admin"', field)

    def test_unsupported_operations_are_refused(self):
        with self.assertRaises(PatchworkError):
            objects.replace_object(self.export, "script", "Close Window", "<Script></Script>")
        with self.assertRaises(PatchworkError):
            objects.delete_object(self.export, "theme", "Apex Blue")

    def test_diff_reports_added_changed_and_deleted(self):
        text = self.export.text
        after = Export(
            text.replace("<![CDATA[600]]>", "<![CDATA[640]]>")
            .replace('<ValueList id="2" name="Industries">', '<ValueList id="2" name="Sectors">')
        )
        self.assertEqual(
            objects.diff(self.export, after),
            ["~ custom-function CardWindowHeight", "- value-list Industries", "+ value-list Sectors"],
        )

    def test_normalize_ignores_uuid_bookkeeping(self):
        a = '<FMSaveAsXML File="a.fmp12"><UUID modifications="1" userName="x">U</UUID>'
        b = '<FMSaveAsXML File="b.fmp12"><UUID modifications="2" userName="FMUpgradeTool">U</UUID>'
        self.assertEqual(objects.normalize(a), objects.normalize(b))


if __name__ == "__main__":
    unittest.main()
