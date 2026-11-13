import json
import re
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from helpers import FIXTURES, FakeTool, filemaker_effect
from patchwork import PatchworkError, objects, ops
from patchwork.build import wrap
from patchwork.workspace import Workspace


def changed(effect, old, new):
    """FileMaker applying the patch, after turning `old` into `new` in it."""
    return lambda patch, text: effect(patch.replace(old, new), text)


class OpsTests(unittest.TestCase):
    fixture = "mini-export.xml"

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.src = self.tmp / "App.fmp12"
        self.src.write_bytes(b"fmp12")
        self.tool = FakeTool(filemaker_effect)
        self.tool.text = self.prepare((FIXTURES / self.fixture).read_text(encoding="utf-8"))
        patcher = mock.patch("patchwork.workspace.Workspace.runner", lambda ws, quiet=True: self.tool)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.ws = Workspace.create(self.src, "Admin", True, self.tmp, runner=self.tool)

    def prepare(self, text: str) -> str:
        return text

    def assertDropped(self, message: str, call):
        with self.assertRaisesRegex(PatchworkError, message):
            call()
        self.assertEqual(Workspace.locate(self.tmp).version, 0)
        self.assertFalse((self.tmp / ".patchwork" / "v001.fmp12").exists())


class ReadingTests(OpsTests):
    def test_status_names_the_source_version_account_and_contents(self):
        lines = ops.status(self.ws).splitlines()
        self.assertEqual(lines[0], f"source   {self.src.resolve()}")
        self.assertRegex(lines[1], r"^version  v000  \(open App\.fmp12, .+\)$")
        self.assertEqual(lines[2], "account  Admin")
        self.assertEqual(lines[3], "contents 1 tables, 2 layouts, 1 scripts, 1 value-lists, 1 custom-functions")

    def test_list_counts_every_kind_and_lists_fields_of_a_table(self):
        self.assertEqual(
            ops.list_objects(self.ws).splitlines(),
            [
                "layouts: 2",
                "scripts: 1",
                "value-lists: 1",
                "custom-functions: 1",
                "themes: 2",
                "tables: 1",
                "table-occurrences: 0",
                "fields: use `ls fields TABLE`",
            ],
        )
        self.assertEqual(ops.list_objects(self.ws, "fields", "Admin"), "Logo\tContainer\nLogo New\tContainer (calc)")
        self.assertEqual(ops.list_objects(self.ws, "layouts"), "Dashboard\nPlain & Simple")
        with self.assertRaisesRegex(PatchworkError, r"^Name the table: ls fields TABLE$"):
            ops.list_objects(self.ws, "fields")

    def test_show_gives_script_text_or_xml(self):
        self.assertEqual(ops.show(self.ws, "script", "Close Window"), "# Closes the window")
        self.assertIn('<Comment value="Closes the window">', ops.show(self.ws, "script", "Close Window", xml=True))
        ops.add_script(self.ws, "Empty")
        self.assertEqual(ops.show(self.ws, "script", "Empty"), "Empty has no steps.")

    def test_palette_lists_the_theme_colors(self):
        self.assertEqual(ops.palette(self.ws), "Apex Blue\n0091CE  1x")

    def test_uses_reports_references(self):
        self.assertIn("layout Dashboard", ops.uses(self.ws, "field", "Admin::Logo"))


class WritingTests(OpsTests):
    def test_add_field(self):
        self.assertEqual(
            ops.add_field(self.ws, "Admin", "Notes"), "v001  add field Admin::Notes\n  + field Admin::Notes"
        )
        self.assertIn("Notes\tText", ops.list_objects(self.ws, "fields", "Admin"))
        with self.assertRaisesRegex(PatchworkError, r"^Unknown field type: Txt\. Choose from Text, "):
            ops.add_field(self.ws, "Admin", "Other", type="Txt")

    def test_add_script_then_set_and_append_steps(self):
        self.assertEqual(ops.add_script(self.ws, "Hello", "Beep"), "v001  add script Hello\n  + script Hello")
        self.assertEqual(ops.show(self.ws, "script", "Hello"), "Beep")
        ops.set_steps(self.ws, "Close Window", "Beep\nHalt Script")
        self.assertEqual(ops.show(self.ws, "script", "Close Window"), "Beep\nHalt Script")
        text = ops.append_steps(self.ws, "Close Window", "Freeze Window")
        self.assertEqual(text, "v003  append steps to Close Window\n  ~ script Close Window")
        self.assertEqual(ops.show(self.ws, "script", "Close Window"), "Beep\nHalt Script\nFreeze Window")

    def test_custom_function(self):
        text = ops.add_custom_function(self.ws, "Twice", "x * 2", ["x"])
        self.assertEqual(text, "v001  add custom function Twice\n  + custom-function Twice")

    def test_replace_an_object(self):
        layout = objects.find(self.ws.export, "layout", "Plain & Simple").xml
        text = ops.replace(self.ws, "layout", "Plain & Simple", layout.replace('width="800"', 'width="900"'))
        self.assertEqual(text, "v001  edit layout Plain & Simple\n  ~ layout Plain & Simple")
        self.assertIn('width="900"', self.ws.export.layout("Plain & Simple").xml)

    def test_retheme_and_recolor(self):
        self.assertEqual(
            ops.retheme(self.ws, colors={"0091CE": "#00475A"}), "v001  edit theme Apex Blue\n  ~ theme Apex Blue"
        )
        self.assertEqual(ops.palette(self.ws), "Apex Blue\n00475A  1x")
        text = ops.recolor_layouts(self.ws, colors={"0091CE": "#112233"})
        self.assertEqual(text, "v002  edit 1 layout(s)\n  ~ layout Dashboard")
        with self.assertRaisesRegex(PatchworkError, r"^No layout would change\.$"):
            ops.recolor_layouts(self.ws, colors={"ABCDEF": "#112233"})

    def test_push_takes_only_a_full_patch(self):
        action = objects.add_object(self.ws.export, "value-list", objects.value_list_xml("Status", ["A"]))
        with self.assertRaisesRegex(PatchworkError, r"^Expected a full patch \(root <FMUpgradeToolPatch>\)\.$"):
            ops.push(self.ws, action)
        text = ops.push(self.ws, wrap(action, version=self.ws.export.version))
        self.assertEqual(text, "v001  push patch\n  + value-list Status")

    def test_dry_run_changes_nothing(self):
        text = ops.add_field(self.ws, "Admin", "Notes", dry_run=True)
        self.assertEqual(text, f"Dry run: patch written to {self.tmp.resolve() / '.patchwork' / 'p001.xml'}")
        self.assertEqual(self.ws.version, 0)


class DroppedVersionTests(OpsTests):
    """FMUpgradeTool reports success, but the result is not what was asked: the version is dropped."""

    def test_the_expected_object_is_missing(self):
        self.tool.effect = changed(filemaker_effect, 'name="Notes"', 'name="Other"')
        self.assertDropped(
            r"`\+ field Admin::Notes` is missing from the result\. Version dropped\.",
            lambda: ops.add_field(self.ws, "Admin", "Notes"),
        )

    def test_a_step_comes_back_changed(self):
        self.tool.effect = changed(filemaker_effect, 'id="90" name="Halt Script"', 'id="93" name="Beep"')
        self.assertDropped(
            r"step 2 came back as `Beep` instead of `Halt Script`",
            lambda: ops.set_steps(self.ws, "Close Window", "Beep\nHalt Script"),
        )

    def test_a_step_goes_missing(self):
        def drop_second_step(patch, text):
            return filemaker_effect(re.sub(r'<Step index="1"[\s\S]*?</Step>', "", patch), text)

        self.tool.effect = drop_second_step
        self.assertDropped(
            r"the script has 1 steps instead of 2", lambda: ops.add_script(self.ws, "Hello", "Beep\nHalt Script")
        )

    def test_the_formula_or_parameters_of_a_custom_function_are_lost(self):
        self.tool.effect = changed(filemaker_effect, "CDATA[x * 2]", "CDATA[]")
        self.assertDropped(
            r"the formula is missing from the result",
            lambda: ops.add_custom_function(self.ws, "Twice", "x * 2", ["x"]),
        )
        self.tool.effect = changed(filemaker_effect, '<Parameter name="x">', '<Parameter name="y">')
        self.assertDropped(
            r"the parameters are \['y'\] instead of \['x'\]",
            lambda: ops.add_custom_function(self.ws, "Twice", "x * 2", ["x"]),
        )


class PlaceFieldTests(OpsTests):
    fixture = "layout-export.xml"

    def prepare(self, text: str) -> str:
        """Real exports always have a theme catalog; this fixture is cut down to layouts."""
        return text.replace("<LayoutCatalog>", '<ThemeCatalog membercount="0"></ThemeCatalog>\n<LayoutCatalog>', 1)

    def test_place_a_field_on_a_layout(self):
        text = ops.place_field(self.ws, "Clients Details", "Clients::Loyalty Tier", "Email")
        self.assertEqual(text, "v001  place Clients::Loyalty Tier on Clients Details\n  ~ layout Clients Details")
        self.assertIn('UUID="TIER-UUID"', self.ws.export.layout("Clients Details").xml)

    def test_a_field_missing_from_the_result_drops_the_version(self):
        self.tool.effect = changed(filemaker_effect, 'UUID="TIER-UUID"', 'UUID="LOST-UUID"')
        self.assertDropped(
            r"Clients::Loyalty Tier is not on 'Clients Details' in the result\. Version dropped\.",
            lambda: ops.place_field(self.ws, "Clients Details", "Clients::Loyalty Tier", "Email"),
        )


class LoadJsonTests(unittest.TestCase):
    def test_empty_dict_file_or_text(self):
        self.assertEqual(ops.load_json(None), {})
        self.assertEqual(ops.load_json(""), {})
        self.assertEqual(ops.load_json({"a": 1}), {"a": 1})
        self.assertEqual(ops.load_json('{"a": 1}'), {"a": 1})
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "brand.json"
            path.write_text(json.dumps({"b": 2}), encoding="utf-8")
            self.assertEqual(ops.load_json(str(path)), {"b": 2})
        with self.assertRaises(json.JSONDecodeError):
            ops.load_json("{not json")


if __name__ == "__main__":
    unittest.main()
