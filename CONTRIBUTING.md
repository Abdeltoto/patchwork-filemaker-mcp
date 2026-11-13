# Contributing to Patchwork

Thanks for helping. FileMaker developers know things about FMUpgradeTool that no documentation says: every verified finding makes this tool better for everyone.

## Three easy ways to help

1. **Share a finding.** You noticed FMUpgradeTool skips a patch, or needs an attribute the docs don't mention? Open a [field guide finding](https://github.com/Abdeltoto/patchwork-filemaker-mcp/issues/new?template=field-guide.yml). Say which FileMaker version, what you tried, what happened.
2. **Share a brand or a recipe.** A `brand.json` for another Claris starter theme, or a step-by-step patch recipe, goes in `examples/`.
3. **Fix or build.** Pick an issue labeled `good first issue`.

## Set up

You need Python 3.10 or later and Git. FileMaker is not needed for the unit tests.

```bash
git clone https://github.com/Abdeltoto/patchwork-filemaker-mcp
cd patchwork-filemaker-mcp
python -m venv .venv
. .venv/bin/activate                 # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -e ".[image]"
python -m unittest discover -s tests
```

The last line ends with `OK`. Some tests are skipped: they are the end-to-end tests, which need a real file (see below).

## Checks before a pull request

CI runs all of these and blocks on any failure. Run them locally with the same versions:

```bash
pip install ruff==0.17.5 mypy==2.4.1 import-linter==2.16 coverage==7.17.3

python -m unittest discover -s tests
ruff check src tests
ruff format --check src tests
mypy
PYTHONPATH=src lint-imports          # Windows PowerShell: $env:PYTHONPATH = "src"; lint-imports
```

CI runs `mypy` in a venv without Pillow. With Pillow 13 installed (`.[image]`), mypy reports `build.py:182: Module has no attribute "LANCZOS"`. Pillow 13 still provides `Image.LANCZOS` at run time, but its type hints do not declare it. To get the CI result, run mypy in a venv without Pillow:

```bash
python -m venv ../patchwork-lint
. ../patchwork-lint/bin/activate     # Windows PowerShell: ..\patchwork-lint\Scripts\Activate.ps1
pip install mypy==2.4.1
mypy
```

Coverage of the business logic must stay at 90 % or more:

```bash
coverage run -m unittest discover -s tests
coverage report --include="src/patchwork/ops.py,src/patchwork/workspace.py,src/patchwork/tools.py,src/patchwork/build.py,src/patchwork/objects.py,src/patchwork/script.py,src/patchwork/place.py,src/patchwork/uses.py,src/patchwork/export.py,src/patchwork/rebrand.py" --fail-under=90
```

CI also runs a `security` job: gitleaks on the whole history, pip-audit on what the package installs, and bandit on `src`. The workflows are in `.github/workflows/`.

Optional: `pip install pre-commit && pre-commit install` runs `ruff check` and `ruff format` on every commit.

## End-to-end tests

If you change how a patch is built, also run the end-to-end tests against the real Claris tools. They need the tools (`patchwork doctor` finds them) and the free [Invoice Solution](https://marketplace.claris.com/detail/2000.html), closed in FileMaker:

```bash
PATCHWORK_SAMPLE="/path/to/Invoice Solution.fmp12" python -m unittest discover -s tests -p test_integration.py -v
```

```powershell
$env:PATCHWORK_SAMPLE = "C:\path\to\Invoice Solution.fmp12"
python -m unittest discover -s tests -p test_integration.py -v
Remove-Item Env:PATCHWORK_SAMPLE
```

They work on a copy and check the content of every change, not only that FMUpgradeTool reported success. They take a few minutes. Remove the variable afterwards, or every later run of the suite includes them. Say in the pull request that they pass, and add a scenario for any new operation.

## Adding a test

Tests use `unittest` and live in `tests/test_*.py`. Import `helpers` before `patchwork`: it puts `src/` on the path.

| In `tests/helpers.py` | What it is |
|---|---|
| `FakeTool` | Stands in for the Claris tools. Keeps one export per `.fmp12`, records every patch in `.patches`. |
| `filemaker_effect` | Applies a patch to the fake export the way FMUpgradeTool does, for the shapes Patchwork writes. Pass it to `FakeTool`. |
| `mini_export()` | The small fictional export in `tests/fixtures/mini-export.xml`. |
| `FIXTURES` | `tests/fixtures/`: `mini-export.xml`, `layout-export.xml`, `built-steps.json`. |

A test of an operation, from a new working copy:

```python
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from helpers import FakeTool, filemaker_effect
from patchwork import ops
from patchwork.workspace import Workspace


class ValueListTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        src = self.tmp / "App.fmp12"
        src.write_bytes(b"fmp12")
        self.tool = FakeTool(filemaker_effect)
        patcher = mock.patch("patchwork.workspace.Workspace.runner", lambda ws, quiet=True: self.tool)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.ws = Workspace.create(src, "Admin", True, self.tmp, runner=self.tool)

    def test_a_new_value_list_is_a_new_version(self):
        text = ops.add_value_list(self.ws, "Status", ["Active", "Archived"])
        self.assertEqual(text.splitlines(), ["v001  add value list Status", "  + value-list Status"])
```

Run one file or one test:

```bash
cd tests
python -m unittest test_ops -v
python -m unittest test_ops.ReadingTests.test_status_names_the_source_version_account_and_contents
```

Rules for tests:

- A test must be able to fail. Break the code it protects for a moment, run it, and check that it fails.
- Check the message of an error (`assertRaisesRegex`), not just that some `PatchworkError` was raised.
- No dependence on test order, the clock or the network. Use a temporary folder, never the current one.
- To simulate a FileMaker that loses part of a patch, give `FakeTool` another effect. `tests/test_ops.py` has examples.
- Never change an existing test to make it pass.

## Git workflow

1. Branch from `main`, one topic per branch.
2. Small commits. Each one passes the tests. The history uses a short prefix and a sentence: `Tests: ...`, `Security: ...`, `CI: ...`, `Docs: ...`, `Refactor: ...`.
3. Open a pull request. The template asks how you checked it. CI runs on every pushed branch and on pull requests.
4. A release is a GitHub release: `release.yml` runs the tests, builds the package and publishes it to PyPI. Before one, update the version in `src/patchwork/__init__.py` and `server.json` (both places), and move the `Unreleased` section of `CHANGELOG.md` under the new version.

## Conventions

- Standard library only at runtime. Pillow stays optional. Development tools are pinned in CI, not added to `dependencies`.
- Python 3.10 syntax at most (`target-version = "py310"`). Lines up to 120 characters, ruff rules `E, F, W, I, B, UP`.
- A problem the user can fix raises `PatchworkError`, with a one-line message that says what to do next.
- A comment explains why, never what the next line does.
- The layer rules in [ARCHITECTURE.md](ARCHITECTURE.md) are checked by `lint-imports`. A new module goes into one of the contracts in `pyproject.toml`.
- Never commit a `.fmp12`, an export, or anything from a customer file. Fixtures are hand-written and fictional.
- A new technical choice gets a short note in [docs/decisions/](docs/decisions/).

By contributing you agree to the [Code of Conduct](CODE_OF_CONDUCT.md) and to license your work under the [MIT License](LICENSE).
