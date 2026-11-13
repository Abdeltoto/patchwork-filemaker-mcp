import io
import json
import os
import re
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from helpers import FIXTURES
from patchwork import PatchworkError, ops
from patchwork.mcp import serve
from patchwork.workspace import Workspace


class FakeTool:
    """Stands in for FMUpgradeTool + FMDeveloperTool. `effect(patch, text)` returns the new export."""

    def __init__(self, effect=None):
        self.text = (FIXTURES / "mini-export.xml").read_text(encoding="utf-8")
        self.effect = effect or (lambda patch, text: text)

    def generate_guids(self, src, dest, force=False):
        shutil.copyfile(src, dest)

    def export_xml(self, src, out, force=False):
        out.write_text(self.text, encoding="utf-8")

    def apply(self, src, patch, dest, force=False):
        self.text = self.effect(patch.read_text(encoding="utf-8"), self.text)
        shutil.copyfile(src, dest)


def add_value_list_effect(patch, text):
    added = re.search(r"<ValueList [\s\S]*?</ValueList>", patch)
    if added and "Status" in patch:
        return text.replace("</ValueListCatalog>", added.group(0).replace("\r", "\n") + "\n</ValueListCatalog>")
    return text


def empty_value_list_effect(patch, text):
    return text.replace(
        "</ValueListCatalog>", '<ValueList id="3" name="Status">\n<UUID>NEW</UUID>\n</ValueList>\n</ValueListCatalog>'
    )


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.src = self.tmp / "App.fmp12"
        self.src.write_bytes(b"fmp12")
        self.tool = FakeTool(add_value_list_effect)
        self.patcher = mock.patch("patchwork.workspace.Workspace.runner", lambda ws, quiet=True: self.tool)
        self.patcher.start()
        self.ws = Workspace.create(self.src, "Admin", True, self.tmp, runner=self.tool)

    def tearDown(self):
        self.patcher.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_open_makes_v000_and_hides_itself_from_git(self):
        self.assertEqual(self.ws.version, 0)
        self.assertTrue((self.tmp / ".patchwork" / "v000.xml").is_file())
        self.assertEqual((self.tmp / ".patchwork" / ".gitignore").read_text(), "*\n")
        self.assertEqual(Workspace.locate(self.tmp).version, 0)

    def test_change_creates_a_version_with_its_diff(self):
        text = ops.add_value_list(self.ws, "Status", ["Active", "Archived"])
        self.assertIn("v001  add value list Status", text)
        self.assertIn("+ value-list Status", text)
        self.assertEqual(Workspace.locate(self.tmp).log()[-1]["changes"], ["+ value-list Status"])

    def test_skipped_patch_is_refused_and_leaves_no_version(self):
        with self.assertRaises(PatchworkError) as caught:
            ops.add_custom_function(self.ws, "Hello", "1")
        self.assertIn("skipped", str(caught.exception))
        self.assertEqual(self.ws.version, 0)
        self.assertFalse((self.tmp / ".patchwork" / "v001.fmp12").exists())

    def test_content_lost_by_filemaker_drops_the_version(self):
        self.tool.effect = empty_value_list_effect
        with self.assertRaises(PatchworkError) as caught:
            ops.add_value_list(self.ws, "Status", ["Active", "Archived"])
        self.assertIn("instead of ['Active', 'Archived']", str(caught.exception))
        self.assertEqual(self.ws.version, 0)

    def test_undo_and_save(self):
        ops.add_value_list(self.ws, "Status", ["Active"])
        self.assertEqual(ops.undo(self.ws), "Back to v000")
        with self.assertRaisesRegex(PatchworkError, "The destination is the source file"):
            self.ws.save(self.src)
        self.assertIn("Saved v000", ops.save(self.ws, str(self.tmp / "out.fmp12")))

    def test_dry_run_writes_the_patch_only(self):
        text = ops.add_value_list(self.ws, "Status", ["Active"], dry_run=True)
        self.assertIn("p001.xml", text)
        self.assertEqual(self.ws.version, 0)

    def test_delete_refuses_a_referenced_object_without_force(self):
        self.tool.effect = lambda patch, text: text.replace('<Field id="24" name="Logo"', '<Field id="24" name="Gone"')
        with self.assertRaises(PatchworkError) as caught:
            ops.delete(self.ws, "field", "Admin::Logo")
        self.assertIn("layout Dashboard", str(caught.exception))
        self.assertIn("--force", str(caught.exception))
        self.assertEqual(self.ws.version, 0)
        text = ops.delete(self.ws, "field", "Admin::Logo", force=True)
        self.assertIn("- field Admin::Logo", text)
        self.assertIn("Warning, review these", text)

    def test_reopening_needs_force(self):
        ops.add_value_list(self.ws, "Status", ["Active"])
        with self.assertRaisesRegex(PatchworkError, "A workspace already exists here for App.fmp12"):
            Workspace.create(self.src, "Admin", True, self.tmp, runner=self.tool)
        self.assertEqual(Workspace.locate(self.tmp).version, 1)
        self.assertTrue((self.tmp / ".patchwork" / "v001.fmp12").is_file())


class McpTests(unittest.TestCase):
    def converse(self, *messages, project=None):
        stdin = io.StringIO("".join(json.dumps(m) + "\n" for m in messages))
        stdout = io.StringIO()
        serve(project, stdin, stdout)
        return [json.loads(line) for line in stdout.getvalue().splitlines()]

    def test_handshake_and_tool_list(self):
        replies = self.converse(
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}},
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        )
        self.assertEqual(len(replies), 2)
        self.assertEqual(replies[0]["result"]["serverInfo"]["name"], "patchwork")
        names = {t["name"] for t in replies[1]["result"]["tools"]}
        self.assertTrue(
            {"patchwork_open", "patchwork_show", "patchwork_add_script", "patchwork_undo", "patchwork_save"} <= names
        )

    def test_errors_come_back_as_tool_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            reply = self.converse(
                {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {"name": "patchwork_status", "arguments": {}},
                },
                project=Path(tmp),
            )[0]
        self.assertTrue(reply["result"]["isError"])
        self.assertIn("patchwork open", reply["result"]["content"][0]["text"])

    def test_unknown_method(self):
        reply = self.converse({"jsonrpc": "2.0", "id": 4, "method": "resources/list"})[0]
        self.assertEqual(reply["error"]["code"], -32601)

    def test_tools_that_can_lose_work_are_marked_destructive(self):
        reply = self.converse({"jsonrpc": "2.0", "id": 5, "method": "tools/list"})[0]
        annotations = {t["name"]: t["annotations"] for t in reply["result"]["tools"]}
        destructive = {
            "patchwork_open",
            "patchwork_delete",
            "patchwork_undo",
            "patchwork_save",
            "patchwork_push",
            "patchwork_replace",
        }
        for name, hints in annotations.items():
            self.assertEqual(hints["destructiveHint"], name in destructive, name)

    def test_mcp_never_replaces_or_deletes_outside_the_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            project, outside = Path(tmp) / "project", Path(tmp) / "other"
            project.mkdir()
            (outside / ".patchwork").mkdir(parents=True)
            (outside / ".patchwork" / "state.json").write_text("{}", encoding="utf-8")
            other = outside / "Other.fmp12"
            other.write_bytes(b"other client")
            src = project / "App.fmp12"
            src.write_bytes(b"fmp12")
            Workspace.create(src, "Admin", True, project, runner=FakeTool())

            def call(ident, name, arguments):
                return {
                    "jsonrpc": "2.0",
                    "id": ident,
                    "method": "tools/call",
                    "params": {"name": name, "arguments": arguments},
                }

            env = {k: v for k, v in os.environ.items() if k != "PATCHWORK_ALLOW_OUTSIDE"}
            with mock.patch.dict(os.environ, env, clear=True):
                replies = self.converse(
                    call(1, "patchwork_save", {"dest": str(other), "force": True}),
                    call(
                        2,
                        "patchwork_open",
                        {
                            "source": str(other),
                            "account": "Admin",
                            "no_password": True,
                            "project": str(outside),
                            "force": True,
                        },
                    ),
                    call(3, "patchwork_save", {"dest": str(project / "Saved.fmp12"), "force": True}),
                    project=project,
                )
            self.assertIn("outside the project folder", replies[0]["result"]["content"][0]["text"])
            self.assertEqual(other.read_bytes(), b"other client")
            self.assertIn("outside the project folder", replies[1]["result"]["content"][0]["text"])
            self.assertTrue((outside / ".patchwork" / "state.json").is_file())
            self.assertFalse(replies[2]["result"]["isError"], replies[2])
            self.assertTrue((project / "Saved.fmp12").is_file())


if __name__ == "__main__":
    unittest.main()
