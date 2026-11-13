"""End-to-end tests against the real Claris tools. Skipped unless PATCHWORK_SAMPLE is set.

    PATCHWORK_SAMPLE=/path/to/"Invoice Solution.fmp12" python -m unittest discover -s tests -p test_integration.py -v

The sample is the free Invoice Solution from the Claris Marketplace (account Admin, no password),
closed in FileMaker. It is only read: every test works on a copy and puts the copy back to v000.
Set PATCHWORK_PASSWORD if your sample has a password, PATCHWORK_SAMPLE_ACCOUNT if it is not Admin.
"""

import io
import json
import os
import re
import shutil
import tempfile
import unittest
from pathlib import Path

import helpers  # noqa: F401  (puts src/ on the path)
from patchwork import PatchworkError, objects, ops
from patchwork.build import wrap
from patchwork.mcp import serve
from patchwork.tools import find_tool
from patchwork.workspace import Workspace

SAMPLE = os.environ.get("PATCHWORK_SAMPLE", "")
READY = (
    bool(SAMPLE) and Path(SAMPLE).is_file() and bool(find_tool("FMUpgradeTool")) and bool(find_tool("FMDeveloperTool"))
)


@unittest.skipUnless(
    READY, "set PATCHWORK_SAMPLE to a closed copy of the Claris Invoice solution, with the Claris tools installed"
)
class RealFileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="patchwork-it-"))
        cls.source = cls.tmp / "Sample.fmp12"
        shutil.copyfile(SAMPLE, cls.source)
        ops.open_file(
            str(cls.source),
            os.environ.get("PATCHWORK_SAMPLE_ACCOUNT", "Admin"),
            no_password=not os.environ.get("PATCHWORK_PASSWORD"),
            project=str(cls.tmp),
        )

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def setUp(self):
        self.ws = Workspace.locate(self.tmp)

    def tearDown(self):
        ws = Workspace.locate(self.tmp)
        while ws.version > 0:
            ws.undo()

    def current(self):
        return Workspace.locate(self.tmp).export

    @staticmethod
    def values(ws, name):
        text = re.search(
            r"<CustomValues>\s*<Text><!\[CDATA\[([\s\S]*?)\]\]>", objects.find(ws.export, "value-list", name).xml
        ).group(1)
        return re.split(r"\r\n|\r|\n", text)

    def test_fields(self):
        self.assertIn("+ field Clients::IT Note", ops.add_field(self.ws, "Clients", "IT Note", comment="integration"))
        self.assertIn(
            "+ field Clients::IT Upper",
            ops.add_field(
                Workspace.locate(self.tmp), "Clients", "IT Upper", calc="Upper ( Clients::Name )", context="Clients"
            ),
        )
        self.assertIn("IT Upper\tText (calc)", ops.list_objects(Workspace.locate(self.tmp), "fields", "Clients"))
        self.assertIn("- field Clients::IT Note", ops.delete(Workspace.locate(self.tmp), "field", "Clients::IT Note"))

    def test_place_field_inserts_a_row(self):
        ops.add_field(self.ws, "Clients", "IT Tier")
        before = self.current().layout("Clients Details").xml
        result = ops.place_field(
            Workspace.locate(self.tmp), "Clients Details", "Clients::IT Tier", "Contact Email", "Tier"
        )
        self.assertIn("~ layout Clients Details", result)
        after = self.current().layout("Clients Details").xml
        self.assertIn("<Data><![CDATA[Tier]]></Data>", after)
        self.assertEqual(after.count("<LayoutObject "), before.count("<LayoutObject ") + 2)

        def size(xml):
            return int(re.search(r'<Definition type="Body" [^>]*size="(\d+)"', xml).group(1))

        self.assertGreater(size(after), size(before))

    def test_value_list_add_replace_delete(self):
        ops.add_value_list(self.ws, "IT Tiers", ["Bronze", "Silver"])
        ws = Workspace.locate(self.tmp)
        self.assertEqual(self.values(ws, "IT Tiers"), ["Bronze", "Silver"])
        edited = ops.show(ws, "value-list", "IT Tiers").replace("Silver", "Silver\nGold")
        self.assertIn("~ value-list IT Tiers", ops.replace(ws, "value-list", "IT Tiers", edited))
        self.assertEqual(self.values(Workspace.locate(self.tmp), "IT Tiers"), ["Bronze", "Silver", "Gold"])
        self.assertIn("- value-list IT Tiers", ops.delete(Workspace.locate(self.tmp), "value-list", "IT Tiers"))

    def test_custom_function_add_replace_delete(self):
        ops.add_custom_function(self.ws, "ITGreet", '"Hello " & who', ["who"])
        ws = Workspace.locate(self.tmp)
        added = objects.find(ws.export, "custom-function", "ITGreet").xml
        self.assertIn('"Hello " & who', added, "the formula was dropped")
        self.assertIn('<Parameter name="who">', added)
        edited = ops.show(ws, "custom-function", "ITGreet").replace('"Hello "', '"Hi "')
        self.assertIn("~ custom-function ITGreet", ops.replace(ws, "custom-function", "ITGreet", edited))
        self.assertIn('"Hi "', objects.find(self.current(), "custom-function", "ITGreet").xml)
        self.assertIn("- custom-function ITGreet", ops.delete(Workspace.locate(self.tmp), "custom-function", "ITGreet"))

    def test_script_steps_keep_every_parameter(self):
        dialog = ops.show(self.ws, "step", "Show Custom Dialog").replace('CDATA["Message"]', 'CDATA["IT Title"]', 1)
        dialog = re.sub(
            r'(<Parameter type="Message">[\s\S]*?CDATA\[)[\s\S]*?(\]\]>)',
            r'\1"Hello " & Get ( AccountName )\2',
            dialog,
            count=1,
        )
        comment = re.sub(r'Comment value="[^"]*"', 'Comment value="IT first"', ops.show(self.ws, "step", "# (comment)"))
        self.assertIn("+ script IT Hello", ops.add_script(self.ws, "IT Hello", comment + "\n" + dialog))
        script = ops.show(Workspace.locate(self.tmp), "script", "IT Hello", xml=True)
        self.assertIn('"Hello " & Get ( AccountName )', script, "a step parameter was dropped")
        self.assertEqual(script.count("<Step "), 2)
        ops.append_steps(Workspace.locate(self.tmp), "IT Hello", comment.replace("IT first", "IT appended"))
        self.assertIn("IT appended", ops.show(Workspace.locate(self.tmp), "script", "IT Hello"))
        ops.set_steps(Workspace.locate(self.tmp), "IT Hello", comment.replace("IT first", "IT only"))
        script = ops.show(Workspace.locate(self.tmp), "script", "IT Hello", xml=True)
        self.assertEqual(script.count("<Step "), 1)
        self.assertIn("IT only", script)
        self.assertIn("- script IT Hello", ops.delete(Workspace.locate(self.tmp), "script", "IT Hello"))

    def test_script_text_round_trip_with_every_supported_step(self):
        text = "\n".join(
            [
                "# Mark a client as Gold¶and tell the user",
                "Set Error Capture [ On ]",
                "Allow User Abort [ Off ]",
                "Freeze Window",
                'Go to Layout [ "Clients Details" ]',
                "Set Variable [ $count ; Value: Get ( FoundCount ) ]",
                "If [ $count = 0 ]",
                '    Show Custom Dialog [ "Nothing to do" ; "No client in the found set." ]',
                "    Exit Script [ Text Result: False ]",
                "Else If [ $count > 100 ]",
                '    Show Custom Dialog [ "Many clients" ; "Continue with " & $count & " clients?" ; Buttons: "Continue", "Cancel" ]',
                "Else",
                "    Beep",
                "End If",
                "Loop",
                '    Set Field [ Clients::Status ; "Gold" /* tier; not a separator */ ]',
                "    Exit Loop If [ Get ( RecordNumber ) = Get ( FoundCount ) ]",
                "End Loop",
                "Commit Records/Requests [ Skip data entry validation: Off ; With dialog: Off ; Force Commit: Off ]",
                "Refresh Window [ Flush cached join results: On ; Flush cached external data: Off ]",
                'Perform Script [ "Sort Clients" ; Parameter: "gold" ]',
                "New Record/Request",
                "Delete Record/Request [ With dialog: Off ]",
                "Show All Records",
                "Go to Layout [ original layout ]",
                "// Close Window [ Current Window ]",
                "Halt Script",
            ]
        )
        self.assertIn("+ script IT Text", ops.add_script(self.ws, "IT Text", text))
        shown = ops.show(Workspace.locate(self.tmp), "script", "IT Text")
        self.assertEqual(shown, text)
        edited = shown.replace('"Gold"', '"Platinum"').replace("Halt Script", "Exit Script [ Text Result: True ]")
        self.assertIn("~ script IT Text", ops.set_steps(Workspace.locate(self.tmp), "IT Text", edited))
        self.assertEqual(ops.show(Workspace.locate(self.tmp), "script", "IT Text"), edited)

    def test_delete_a_referenced_layout_needs_force(self):
        self.assertIn("script Set Dates", ops.uses(self.ws, "layout", "Dev Invoices"))
        with self.assertRaises(PatchworkError):
            ops.delete(self.ws, "layout", "Dev Invoices")
        self.assertEqual(Workspace.locate(self.tmp).version, 0)
        text = ops.delete(self.ws, "layout", "Dev Invoices", force=True)
        self.assertIn("- layout Dev Invoices", text)
        self.assertIn("~ script Set Dates", text)

    def test_retheme_renames_and_recolors(self):
        text = ops.retheme(self.ws, colors={"0091CE": "2F5D50"}, rename="IT Forest")
        self.assertIn("+ theme IT Forest", text)
        self.assertIn("- theme Apex Blue", text)
        self.assertIn("rgba(18.4314%,36.4706%,31.3725%,1)", self.current().theme("IT Forest").xml)

    def test_a_lone_layout_object_replace_is_refused(self):
        layout = self.ws.export.layout("Clients Details").xml
        obj = re.search(r'<LayoutObject [^>]*type="Text"[\s\S]*?</LayoutObject>', layout).group(0)
        uuid = re.search(r"<UUID[^>]*>([^<]+)</UUID>", obj).group(1)
        moved = re.sub(r'top="(\d+)', lambda m: f'top="{int(m.group(1)) + 1}', obj, count=1)
        patch = wrap(
            f'\t\t<ReplaceAction>\n\t\t\t<Replace type="LayoutObject" UUID="{uuid}">\n{moved}\n\t\t\t</Replace>\n\t\t</ReplaceAction>\n',
            version=self.ws.export.version,
        )
        with self.assertRaises(PatchworkError) as caught:
            ops.push(self.ws, patch)
        self.assertIn("did not change", str(caught.exception))

    def test_undo_and_save_never_touch_the_source(self):
        before = self.source.read_bytes()
        ops.add_value_list(self.ws, "IT Undo", ["A"])
        self.assertEqual(ops.undo(Workspace.locate(self.tmp)), "Back to v000")
        with self.assertRaises(PatchworkError):
            ops.save(Workspace.locate(self.tmp), str(self.source))
        out = self.tmp / "saved.fmp12"
        ops.save(Workspace.locate(self.tmp), str(out))
        self.assertTrue(out.is_file())
        self.assertEqual(self.source.read_bytes(), before)

    def test_mcp_round_trip(self):
        calls = [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}},
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": "patchwork_add_value_list", "arguments": {"name": "IT MCP", "values": ["X", "Y"]}},
            },
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "patchwork_delete", "arguments": {"kind": "layout", "name": "Dashboard"}},
            },
        ]
        out = io.StringIO()
        serve(self.tmp, io.StringIO("".join(json.dumps(c) + "\n" for c in calls)), out)
        replies = {r["id"]: r for r in map(json.loads, out.getvalue().splitlines())}
        self.assertFalse(replies[2]["result"]["isError"])
        self.assertIn("+ value-list IT MCP", replies[2]["result"]["content"][0]["text"])
        self.assertTrue(replies[3]["result"]["isError"])
        self.assertIn("Not deleted", replies[3]["result"]["content"][0]["text"])


if __name__ == "__main__":
    unittest.main()
