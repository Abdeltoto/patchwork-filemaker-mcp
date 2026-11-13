import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import helpers  # noqa: F401

from patchwork import PatchworkError
from patchwork import tools


class SafetyTests(unittest.TestCase):
    def test_redact_hides_password_and_key(self):
        shown = tools.redact(["tool", "--update", "-src_pwd", "secret", "-src_key", "file-key", "-v"])
        self.assertEqual(shown, ["tool", "--update", "-src_pwd", "***", "-src_key", "***", "-v"])

    def test_copy_must_differ_from_the_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "App.fmp12"
            src.write_bytes(b"x")
            with self.assertRaisesRegex(PatchworkError, "The destination is the source file"):
                tools.require_copy(src, Path(tmp) / "APP.fmp12" if os.name == "nt" else src, force=True)

    def test_copy_refuses_to_overwrite_without_force(self):
        with tempfile.TemporaryDirectory() as tmp:
            src, dest = Path(tmp) / "a.fmp12", Path(tmp) / "b.fmp12"
            src.write_bytes(b"x")
            dest.write_bytes(b"y")
            with self.assertRaisesRegex(PatchworkError, "already exists. Pass --force"):
                tools.require_copy(src, dest, force=False)
            self.assertEqual(tools.require_copy(src, dest, force=True), dest.resolve())

    def test_root_tag_reads_utf8_and_utf16(self):
        with tempfile.TemporaryDirectory() as tmp:
            utf8, utf16 = Path(tmp) / "p.xml", Path(tmp) / "s.xml"
            utf8.write_text('<?xml version="1.0"?>\n<!-- note -->\n<FMUpgradeToolPatch version="1">', encoding="utf-8")
            utf16.write_bytes('<?xml version="1.0"?>\n<FMSaveAsXML>'.encode("utf-16"))
            self.assertEqual(tools.root_tag(utf8), "FMUpgradeToolPatch")
            self.assertEqual(tools.root_tag(utf16), "FMSaveAsXML")

    def test_password_comes_from_the_environment_only(self):
        with mock.patch.dict(os.environ, {tools.PASSWORD_ENV: "secret"}):
            self.assertEqual(tools.password(False), "secret")
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(tools.password(True), "")
            with self.assertRaises(PatchworkError):
                tools.password(False)

    def test_runner_never_prints_the_password(self):
        with tempfile.TemporaryDirectory() as tmp:
            tool = Path(tmp) / "FMUpgradeTool.exe"
            tool.write_bytes(b"")
            printed = []
            env = {tools.PASSWORD_ENV: "secret", "FM_UPGRADE_TOOL": str(tool)}
            with mock.patch.dict(os.environ, env), mock.patch("subprocess.run") as run:
                run.return_value.returncode = 0
                tools.Runner("Admin", echo=printed.append).validate(Path(tmp) / "a.fmp12", Path(tmp) / "p.xml")
            self.assertIn("secret", run.call_args[0][0])
            self.assertNotIn("secret", printed[0])
            self.assertIn("--validatePatch", printed[0])

    def test_failure_mentions_error_803(self):
        with tempfile.TemporaryDirectory() as tmp:
            tool = Path(tmp) / "FMUpgradeTool.exe"
            tool.write_bytes(b"")
            with mock.patch.dict(os.environ, {"FM_UPGRADE_TOOL": str(tool)}), mock.patch("subprocess.run") as run:
                run.return_value.returncode = 1
                run.return_value.stdout = "Error: 803"
                run.return_value.stderr = ""
                with self.assertRaises(PatchworkError) as caught:
                    tools.Runner("Admin", no_password=True, quiet=True).validate(
                        Path(tmp) / "a.fmp12", Path(tmp) / "p.xml"
                    )
            self.assertIn("open in FileMaker", str(caught.exception))

    def test_tool_in_the_current_folder_is_never_picked(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake = Path(tmp) / ("FMUpgradeTool.exe" if os.name == "nt" else "FMUpgradeTool")
            fake.write_bytes(b"")
            fake.chmod(0o755)
            env = {k: v for k, v in os.environ.items() if k not in ("FM_UPGRADE_TOOL", "FM_DEVELOPER_TOOL")}
            env["PATH"] = os.pathsep.join([".", ""])
            previous = os.getcwd()
            os.chdir(tmp)
            try:
                with mock.patch.dict(os.environ, env, clear=True):
                    for name in ("FMUpgradeTool", "FMDeveloperTool"):
                        found = tools.find_tool(name)
                        self.assertFalse(found is not None and tools.same_path(found.parent, Path(tmp)), found)
            finally:
                os.chdir(previous)


if __name__ == "__main__":
    unittest.main()
