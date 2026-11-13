import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import helpers  # noqa: F401
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


if __name__ == "__main__":
    unittest.main()
