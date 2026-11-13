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


BUSINESS_LOGIC = ["ops", "workspace", "tools", "build", "objects", "script", "place", "uses", "export", "rebrand"]


class CoverageGateTests(unittest.TestCase):
    def test_ci_fails_below_90_percent_on_the_business_logic(self):
        ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        gate = re.search(r'coverage report --include="([^"]+)" --fail-under=(\d+)', ci)
        self.assertIsNotNone(gate, "no blocking coverage report in ci.yml")
        self.assertGreaterEqual(int(gate.group(2)), 90)
        self.assertEqual(gate.group(1).split(","), [f"src/patchwork/{name}.py" for name in BUSINESS_LOGIC])


class DependencyFloorTests(unittest.TestCase):
    def test_pillow_floor_is_the_newest_each_python_can_install(self):
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        image = re.search(r"(?m)^image = \[(.*)\]$", pyproject).group(1)
        self.assertEqual(
            re.findall(r'"([^"]*)"', image),
            ["Pillow>=13; python_version >= '3.11'", "Pillow>=12.3; python_version < '3.11'"],
        )


if __name__ == "__main__":
    unittest.main()
