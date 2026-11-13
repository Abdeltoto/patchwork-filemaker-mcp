import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import helpers  # noqa: F401
from patchwork import PatchworkError, tools


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
            with self.assertRaisesRegex(PatchworkError, rf"^Set {tools.PASSWORD_ENV} in your shell"):
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

    def test_a_missing_tool_names_its_variable(self):
        with mock.patch.object(tools, "find_tool", return_value=None):
            for name, variable in (("FMUpgradeTool", "FM_UPGRADE_TOOL"), ("FMDeveloperTool", "FM_DEVELOPER_TOOL")):
                with self.assertRaisesRegex(PatchworkError, f"{name} not found.*set {variable} to its path"):
                    tools.require_tool(name)

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


class RunnerCommandTests(unittest.TestCase):
    """What each Runner command executes, and what it prints: never the password or the key."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        for name in ("FMUpgradeTool.exe", "FMDeveloperTool.exe"):
            (self.tmp / name).write_bytes(b"")
        env = {
            tools.PASSWORD_ENV: "s3cret-pw",
            "FM_UPGRADE_TOOL": str(self.tmp / "FMUpgradeTool.exe"),
            "FM_DEVELOPER_TOOL": str(self.tmp / "FMDeveloperTool.exe"),
        }
        patcher = mock.patch.dict(os.environ, env)
        patcher.start()
        self.addCleanup(patcher.stop)
        os.environ.pop(tools.KEY_ENV, None)
        self.printed = []
        self.runner = tools.Runner("Admin", echo=self.printed.append)

    def ran(self, call):
        with mock.patch("subprocess.run") as run:
            run.return_value.returncode = 0
            call()
        return run.call_args[0][0]

    def test_export_passes_the_password_to_fmdevelopertool_and_prints_stars(self):
        out = self.tmp / "out.xml"
        out.write_text("x")
        command = self.ran(lambda: self.runner.export_xml(self.tmp / "a.fmp12", out, force=True))
        self.assertEqual(command[1:5], ["--saveAsXML", str(self.tmp / "a.fmp12"), "Admin", "s3cret-pw"])
        self.assertEqual(command[-1], "-f")
        self.assertNotIn("s3cret-pw", self.printed[0])
        self.assertIn(" Admin *** -t ", self.printed[0])

    def test_generate_guids_hides_the_password(self):
        dest = self.tmp / "b.fmp12"
        dest.write_bytes(b"x")
        command = self.ran(lambda: self.runner.generate_guids(self.tmp / "a.fmp12", dest, force=True))
        self.assertEqual(command[command.index("-src_pwd") + 1], "s3cret-pw")
        self.assertEqual(command[-1], "-force")
        self.assertNotIn("s3cret-pw", self.printed[0])

    def test_the_encryption_key_is_passed_only_when_set_and_never_printed(self):
        dest = self.tmp / "b.fmp12"
        dest.write_bytes(b"x")
        command = self.ran(lambda: self.runner.apply(self.tmp / "a.fmp12", self.tmp / "p.xml", dest))
        self.assertNotIn("-src_key", command)
        with mock.patch.dict(os.environ, {tools.KEY_ENV: "file-k3y"}):
            command = self.ran(lambda: self.runner.apply(self.tmp / "a.fmp12", self.tmp / "p.xml", dest))
        self.assertEqual(command[command.index("-src_key") + 1], "file-k3y")
        self.assertNotIn("file-k3y", self.printed[1])
        self.assertNotIn("s3cret-pw", self.printed[1])

    def test_a_command_whose_output_is_missing_failed(self):
        with self.assertRaisesRegex(PatchworkError, r"^FMDeveloperTool failed \(exit 0\)\.$"):
            self.ran(lambda: self.runner.export_xml(self.tmp / "a.fmp12", self.tmp / "never-written.xml"))


class PathCheckTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)

    def test_the_source_must_be_an_existing_fmp12(self):
        with self.assertRaisesRegex(PatchworkError, r"^Source file not found: "):
            tools.require_source(self.tmp / "missing.fmp12")
        (self.tmp / "notes.txt").write_text("x")
        with self.assertRaisesRegex(PatchworkError, r"^The source must be a \.fmp12 file: notes\.txt$"):
            tools.require_source(self.tmp / "notes.txt")

    def test_the_destination_must_be_an_fmp12(self):
        (self.tmp / "a.fmp12").write_bytes(b"x")
        with self.assertRaisesRegex(PatchworkError, r"^The destination must end in \.fmp12\.$"):
            tools.require_copy(self.tmp / "a.fmp12", self.tmp / "b.txt", force=True)

    def test_xml_files_need_the_expected_root(self):
        with self.assertRaisesRegex(PatchworkError, r"^File not found: "):
            tools.require_root(self.tmp / "p.xml", "FMUpgradeToolPatch")
        (self.tmp / "p.xml").write_text("<FMSaveAsXML>", encoding="utf-8")
        with self.assertRaisesRegex(
            PatchworkError, r"^p\.xml has root <FMSaveAsXML>, expected <FMUpgradeToolPatch>\.$"
        ):
            tools.require_root(self.tmp / "p.xml", "FMUpgradeToolPatch")
        (self.tmp / "p.xml").write_bytes(b"not xml")
        with self.assertRaisesRegex(PatchworkError, r"^p\.xml has root <unreadable>"):
            tools.require_root(self.tmp / "p.xml", "FMUpgradeToolPatch")
        (self.tmp / "p.xml").write_text("<FMUpgradeToolPatch>", encoding="utf-8")
        tools.require_root(self.tmp / "p.xml", "FMUpgradeToolPatch")

    def test_fmdevelopertool_is_found_next_to_fmupgradetool(self):
        upgrade = self.tmp / "FMUpgradeTool.exe"
        upgrade.write_bytes(b"")
        located = {"FMUpgradeTool": [upgrade], "FMDeveloperTool": []}
        with mock.patch.object(tools, "candidates", side_effect=lambda name: located[name]):
            self.assertIsNone(tools.find_tool("FMDeveloperTool"))
            (self.tmp / "FMDeveloperTool.exe").write_bytes(b"")
            self.assertEqual(tools.find_tool("FMDeveloperTool"), self.tmp / "FMDeveloperTool.exe")


class TimeoutTests(unittest.TestCase):
    """A Claris tool that hangs (a dialog, a locked file) must not block Patchwork forever."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tool = Path(tmp.name) / "FMUpgradeTool.exe"
        self.tool.write_bytes(b"")
        self.runner = tools.Runner("Admin", no_password=True, quiet=True)

    def validate(self, env, run):
        with (
            mock.patch.dict(os.environ, {"FM_UPGRADE_TOOL": str(self.tool), **env}),
            mock.patch("subprocess.run", side_effect=run) as patched,
        ):
            self.runner.validate(self.tool.with_name("a.fmp12"), self.tool.with_name("p.xml"))
        return patched.call_args.kwargs["timeout"]

    def test_every_command_has_a_time_limit_settable_from_the_environment(self):
        done = mock.Mock(returncode=0, stdout="", stderr="")
        os.environ.pop(tools.TIMEOUT_ENV, None)
        self.assertEqual(self.validate({}, lambda *a, **k: done), tools.DEFAULT_TIMEOUT)
        self.assertEqual(self.validate({tools.TIMEOUT_ENV: "90"}, lambda *a, **k: done), 90)

    def test_a_tool_that_does_not_answer_is_stopped_with_a_clear_message(self):
        def hang(command, **kwargs):
            raise subprocess.TimeoutExpired(command, kwargs["timeout"])

        with self.assertRaisesRegex(
            PatchworkError,
            r"^FMUpgradeTool did not finish within 5 s and was stopped\. Is a FileMaker dialog waiting, "
            r"or the file open elsewhere\? Set PATCHWORK_TOOL_TIMEOUT to wait longer\.$",
        ):
            self.validate({tools.TIMEOUT_ENV: "5"}, hang)

    def test_a_bad_time_limit_is_refused(self):
        for value in ("0", "-3", "soon"):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(
                    PatchworkError, rf"^PATCHWORK_TOOL_TIMEOUT must be a number of seconds above 0, got: {value}$"
                ),
            ):
                self.validate({tools.TIMEOUT_ENV: value}, lambda *a, **k: None)


if __name__ == "__main__":
    unittest.main()
