import re
import unittest

from helpers import ROOT

WORKFLOWS = sorted((ROOT / ".github" / "workflows").glob("*.yml"))


class WorkflowTests(unittest.TestCase):
    def test_every_action_is_pinned_to_a_commit(self):
        for path in WORKFLOWS:
            for ref in re.findall(r"^\s*-?\s*uses:\s*(\S+)", path.read_text(encoding="utf-8"), re.M):
                with self.subTest(workflow=path.name, action=ref):
                    self.assertRegex(ref, r"@[0-9a-f]{40}$")

    def test_every_workflow_starts_with_read_only_permissions(self):
        for path in WORKFLOWS:
            with self.subTest(workflow=path.name):
                self.assertRegex(path.read_text(encoding="utf-8"), r"(?m)^permissions:\n  contents: read$")

    def test_build_tools_are_pinned(self):
        for path in WORKFLOWS:
            for command in re.findall(r"pip install ([^\n&|]+)", path.read_text(encoding="utf-8")):
                for package in command.split():
                    if package.startswith("-") or package.startswith(('"', ".")):
                        continue
                    with self.subTest(workflow=path.name, package=package):
                        self.assertIn("==", package)


if __name__ == "__main__":
    unittest.main()
