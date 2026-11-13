import contextlib
import io
import json
import runpy
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from helpers import FakeTool, filemaker_effect
from patchwork.cli import main


def run(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(list(argv))
    return code, out.getvalue(), err.getvalue()


class CliTests(unittest.TestCase):
    def test_commands_outside_a_workspace_explain_how_to_start(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, _, err = run("-C", tmp, "status")
        self.assertEqual(code, 1)
        self.assertIn("patchwork open", err)
        self.assertEqual(err.count("\n"), 1)

    def test_init_wires_every_agent(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "crm"
            code, _, _ = run("init", str(target), "--name", "CRM")
            self.assertEqual(code, 0)
            self.assertIn("# CRM", (target / "AGENTS.md").read_text(encoding="utf-8"))
            self.assertEqual((target / "CLAUDE.md").read_text(encoding="utf-8"), "@AGENTS.md\n")
            for home in (".cursor", ".claude", ".agents"):
                self.assertTrue((target / home / "skills" / "patchwork" / "SKILL.md").is_file(), home)
            cursor = json.loads((target / ".cursor" / "mcp.json").read_text(encoding="utf-8"))
            self.assertEqual(cursor["mcpServers"]["patchwork"]["args"][-3:], ["-C", "${workspaceFolder}", "mcp"])
            self.assertIn("patchwork", json.loads((target / ".mcp.json").read_text(encoding="utf-8"))["mcpServers"])
            self.assertIn(
                "patchwork",
                json.loads((target / ".agents" / "mcp_config.json").read_text(encoding="utf-8"))["mcpServers"],
            )
            self.assertIn(
                'env_vars = ["PATCHWORK_PASSWORD"]', (target / ".codex" / "config.toml").read_text(encoding="utf-8")
            )
            self.assertIn(".patchwork/", (target / ".gitignore").read_text(encoding="utf-8"))

    def test_init_on_an_existing_folder_keeps_its_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            (target / "AGENTS.md").write_text("mine\n", encoding="utf-8")
            code, out, _ = run("init", str(target))
            self.assertEqual(code, 0)
            self.assertEqual((target / "AGENTS.md").read_text(encoding="utf-8"), "mine\n")
            self.assertTrue((target / ".cursor" / "mcp.json").is_file())
            self.assertIn("kept 1 existing file(s): AGENTS.md", out)

    def test_agents_can_start_the_server_without_patchwork_on_path(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch("patchwork.project.shutil.which", return_value=None):
            run("init", tmp)
            server = json.loads((Path(tmp) / ".mcp.json").read_text(encoding="utf-8"))["mcpServers"]["patchwork"]
            self.assertEqual(server["command"], sys.executable)
            self.assertEqual(server["args"], ["-m", "patchwork", "mcp"])
            self.assertIn(
                'args = ["-m", "patchwork", "mcp"]', (Path(tmp) / ".codex" / "config.toml").read_text(encoding="utf-8")
            )

    def test_help_lists_the_editing_commands(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), self.assertRaises(SystemExit) as caught:
            main(["--help"])
        self.assertEqual(caught.exception.code, 0)
        for command in ("open", "add-field", "add-script", "set-steps", "place-field", "delete", "undo", "save"):
            self.assertRegex(out.getvalue(), rf"(?m)^ {{4}}{command} ")


class SessionTests(unittest.TestCase):
    """A whole session through the command line, against a fake FileMaker."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.src = self.tmp / "App.fmp12"
        self.src.write_bytes(b"fmp12")
        self.tool = FakeTool(filemaker_effect)
        patcher = mock.patch("patchwork.workspace.Runner", lambda *a, **k: self.tool)
        patcher.start()
        self.addCleanup(patcher.stop)

    def cli(self, *argv):
        return run("-C", str(self.tmp), *argv)

    def test_open_change_undo_and_save(self):
        code, out, _ = self.cli("open", str(self.src), "--account", "Admin", "--no-password")
        self.assertEqual(
            (code, out.splitlines()[0]), (0, f"Opened App.fmp12 as v000 in {self.tmp.resolve() / '.patchwork'}")
        )
        code, out, _ = self.cli("add-value-list", "Status", "Active", "Archived", "-m", "statuses")
        self.assertEqual(code, 0)
        self.assertIn("v001  statuses", out)
        self.assertIn("v001  ", self.cli("log")[1])
        self.assertEqual(self.cli("undo")[1], "Back to v000\n")
        code, out, _ = self.cli("save", str(self.tmp / "Out.fmp12"))
        self.assertEqual(code, 0)
        self.assertTrue((self.tmp / "Out.fmp12").is_file())

    def test_steps_can_come_from_stdin_or_a_file(self):
        self.cli("open", str(self.src), "--account", "Admin", "--no-password")
        with mock.patch("sys.stdin", io.StringIO("Beep\n")):
            code, out, err = self.cli("add-script", "Ring", "-")
        self.assertEqual(code, 0, err)
        self.assertIn('name="Beep"', self.tool.patches[-1])
        code, _, err = self.cli("append-steps", "Ring", str(self.tmp / "missing.txt"))
        self.assertEqual((code, err), (1, f"patchwork: File not found: {self.tmp / 'missing.txt'}\n"))

    def test_ctrl_c_exits_with_130(self):
        with mock.patch("patchwork.cli.Workspace.locate", side_effect=KeyboardInterrupt):
            self.assertEqual(self.cli("status")[0], 130)


class DoctorTests(unittest.TestCase):
    def test_doctor_shows_the_tools_and_fails_when_one_is_missing(self):
        found = {"FMUpgradeTool": Path("/fms/FMUpgradeTool"), "FMDeveloperTool": Path("/fms/FMDeveloperTool")}
        with mock.patch("patchwork.cli.find_tool", side_effect=found.get):
            code, out, _ = run("doctor")
        self.assertEqual(code, 0)
        self.assertRegex(out, r"(?m)^FMUpgradeTool +\S*FMUpgradeTool$")
        with mock.patch("patchwork.cli.find_tool", side_effect={"FMUpgradeTool": found["FMUpgradeTool"]}.get):
            code, out, _ = run("doctor")
        self.assertEqual(code, 2)
        self.assertRegex(out, r"(?m)^FMDeveloperTool +missing - ships next to FMUpgradeTool$")


class PlumbingTests(unittest.TestCase):
    """`patchwork tool ...`: the checks run before any Claris tool is called."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.src = self.tmp / "App.fmp12"
        self.src.write_bytes(b"fmp12")
        self.patch = self.tmp / "p.xml"
        self.patch.write_text("<FMUpgradeToolPatch>", encoding="utf-8")
        patcher = mock.patch("patchwork.cli.Runner")
        self.runner = patcher.start().return_value
        self.addCleanup(patcher.stop)

    def tool(self, *argv):
        return run("tool", *argv)

    def test_guids_writes_a_copy(self):
        dest = self.tmp / "Copy.fmp12"
        self.assertEqual(self.tool("guids", str(self.src), str(dest), "--account", "Admin")[0], 0)
        self.runner.generate_guids.assert_called_once_with(self.src.resolve(), dest.resolve(), False)
        code, _, err = self.tool("guids", str(self.src), str(self.src), "--account", "Admin")
        self.assertEqual(
            (code, err), (1, "patchwork: The destination is the source file. Patchwork always writes a copy.\n")
        )

    def test_export_does_not_overwrite_without_force(self):
        out = self.tmp / "out" / "App.xml"
        self.assertEqual(self.tool("export", str(self.src), str(out), "--account", "Admin")[0], 0)
        self.runner.export_xml.assert_called_once_with(self.src.resolve(), out.resolve(), False)
        out.write_text("old")
        code, _, err = self.tool("export", str(self.src), str(out), "--account", "Admin")
        self.assertEqual((code, err), (1, f"patchwork: {out.resolve()} already exists. Pass --force to replace it.\n"))
        self.assertEqual(self.runner.export_xml.call_count, 1)

    def test_validate_and_apply_need_a_patch_file(self):
        code, out, _ = self.tool("validate", str(self.src), str(self.patch), "--account", "Admin")
        self.assertEqual(code, 0)
        self.assertTrue(out.startswith("Valid syntax."))
        dest = self.tmp / "New.fmp12"
        self.assertEqual(self.tool("apply", str(self.src), str(self.patch), str(dest), "--account", "Admin")[0], 0)
        self.runner.apply.assert_called_once_with(self.src.resolve(), self.patch.resolve(), dest.resolve(), False)
        self.patch.write_text("<FMSaveAsXML>", encoding="utf-8")
        code, _, err = self.tool("apply", str(self.src), str(self.patch), str(dest), "--account", "Admin")
        self.assertEqual(code, 1)
        self.assertIn("expected <FMUpgradeToolPatch>", err)
        self.assertEqual(self.runner.apply.call_count, 1)

    def test_new_file_needs_a_full_export(self):
        code, _, err = self.tool("new-file", str(self.patch))
        self.assertEqual(code, 1)
        self.assertIn("has root <FMUpgradeToolPatch>, expected <FMSaveAsXML>", err)
        self.runner.new_file.assert_not_called()
        self.patch.write_text("<FMSaveAsXML>", encoding="utf-8")
        self.assertEqual(self.tool("new-file", str(self.patch))[0], 0)
        self.runner.new_file.assert_called_once_with(self.patch.resolve())


class RebrandCommandTests(unittest.TestCase):
    def test_rebrand_reports_what_it_rewrote(self):
        report = mock.Mock(theme="Acme", layouts=["A", "B"], logo_refs=3, work=Path("work"))
        with (
            mock.patch("patchwork.cli.Brand.load") as load,
            mock.patch("patchwork.cli.rebrand", return_value=report) as rebrand,
            mock.patch("patchwork.cli.Runner"),
        ):
            code, out, _ = run("rebrand", "a.fmp12", "b.fmp12", "--brand", "brand.json", "--account", "Admin")
        self.assertEqual(code, 0)
        load.assert_called_once_with(Path("brand.json"))
        self.assertEqual(rebrand.call_args[0][:2], (Path("a.fmp12"), Path("b.fmp12")))
        self.assertIn("  layouts    2 rewritten\n", out)
        self.assertIn("  logo       on 3 layout object(s)\n", out)
        self.assertNotIn("work files", out)


class ModuleTests(unittest.TestCase):
    def test_python_m_patchwork_exits_with_the_command_code(self):
        with (
            tempfile.TemporaryDirectory() as tmp,
            mock.patch.object(sys, "argv", ["patchwork", "-C", tmp, "status"]),
            contextlib.redirect_stderr(io.StringIO()),
            self.assertRaises(SystemExit) as caught,
        ):
            sys.modules.pop("patchwork.__main__", None)
            runpy.run_module("patchwork", run_name="__main__")
        self.assertEqual(caught.exception.code, 1)


if __name__ == "__main__":
    unittest.main()
