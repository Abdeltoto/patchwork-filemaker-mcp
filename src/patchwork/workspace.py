"""A versioned working copy of a FileMaker file, kept in <project>/.patchwork/.

    open    copy the source, give every object a UUID, export it        -> v000
    apply   patch the current version into a new one, export it again   -> v001, v002...
            and refuse the version if FMUpgradeTool changed nothing (it skips bad patches silently)
    undo    drop the last version
    save    copy the current version to a new .fmp12

The source file is never written. The password is never stored: it comes from PATCHWORK_PASSWORD.
"""

from __future__ import annotations

import json
import os
import shutil
import time
from dataclasses import dataclass
from pathlib import Path

from patchwork import PatchworkError
from patchwork.build import wrap
from patchwork.export import Export
from patchwork.objects import diff, normalize
from patchwork.tools import Runner, require_copy, require_source

FOLDER = ".patchwork"
WORKSPACE_ENV = "PATCHWORK_PROJECT"


@dataclass
class Result:
    version: int
    message: str
    changes: list[str]
    patch: Path


class Workspace:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.state_file = root / "state.json"
        if not self.state_file.is_file():
            raise PatchworkError(
                f"No Patchwork workspace in {root.parent}. Start with `patchwork open file.fmp12 --account NAME`."
            )
        self.state = json.loads(self.state_file.read_text(encoding="utf-8"))
        self._export: Export | None = None

    # ----- locate -----

    @staticmethod
    def locate(project: Path | None = None) -> Workspace:
        if project is None and os.environ.get(WORKSPACE_ENV):
            project = Path(os.environ[WORKSPACE_ENV])
        if project is not None:
            return Workspace(project.resolve() / FOLDER)
        here = Path.cwd().resolve()
        for folder in (here, *here.parents):
            if (folder / FOLDER / "state.json").is_file():
                return Workspace(folder / FOLDER)
        raise PatchworkError("No Patchwork workspace here. Start with `patchwork open file.fmp12 --account NAME`.")

    @staticmethod
    def create(
        src: Path,
        account: str,
        no_password: bool,
        project: Path | None = None,
        force: bool = False,
        runner: Runner | None = None,
    ) -> Workspace:
        src = require_source(src)
        project = (project or Path.cwd()).resolve()
        root = project / FOLDER
        if (root / "state.json").is_file():
            if not force:
                current = json.loads((root / "state.json").read_text(encoding="utf-8"))
                raise PatchworkError(
                    f"A workspace already exists here for {Path(current['source']).name}. "
                    "`patchwork save` your work, then pass --force to start over."
                )
            shutil.rmtree(root)
        root.mkdir(parents=True)
        (root / ".gitignore").write_text("*\n", encoding="utf-8")
        runner = runner or Runner(account, no_password, quiet=True)
        try:
            runner.generate_guids(src, root / "v000.fmp12")
            runner.export_xml(root / "v000.fmp12", root / "v000.xml", force=True)
        except Exception:
            shutil.rmtree(root, ignore_errors=True)
            raise
        state = {
            "source": str(src),
            "account": account,
            "no_password": no_password,
            "versions": [{"n": 0, "message": f"open {src.name}", "time": now(), "changes": []}],
        }
        (root / "state.json").write_text(json.dumps(state, indent=2), encoding="utf-8")
        return Workspace(root)

    # ----- state -----

    @property
    def version(self) -> int:
        return self.state["versions"][-1]["n"]

    def file(self, n: int | None = None) -> Path:
        return self.root / f"v{self.version if n is None else n:03d}.fmp12"

    def export_path(self, n: int | None = None) -> Path:
        return self.root / f"v{self.version if n is None else n:03d}.xml"

    @property
    def export(self) -> Export:
        if self._export is None:
            self._export = Export.load(self.export_path())
        return self._export

    def runner(self, quiet: bool = True) -> Runner:
        return Runner(self.state["account"], self.state.get("no_password", False), quiet=quiet)

    def save_state(self) -> None:
        self.state_file.write_text(json.dumps(self.state, indent=2), encoding="utf-8")

    # ----- operations -----

    def apply(
        self, actions: str | list[str], message: str, runner: Runner | None = None, dry_run: bool = False
    ) -> Result:
        """Apply patch actions (or a full FMUpgradeToolPatch) as a new version."""
        parts = [actions] if isinstance(actions, str) else actions
        text = (
            parts[0]
            if len(parts) == 1 and "<FMUpgradeToolPatch" in parts[0]
            else wrap(*parts, version=self.export.version)
        )
        n = self.version + 1
        patch = self.root / f"p{n:03d}.xml"
        patch.write_text(text, encoding="utf-8")
        if dry_run:
            return Result(self.version, message, [], patch)
        runner = runner or self.runner()
        out, xml = self.file(n), self.export_path(n)
        try:
            runner.apply(self.file(), patch, out, force=True)
            runner.export_xml(out, xml, force=True)
            after = Export.load(xml)
            if normalize(after.text) == normalize(self.export.text):
                raise PatchworkError(
                    "FMUpgradeTool reported success but the file did not change: this patch was skipped. "
                    "See docs/fmupgradetool-field-guide.md. The patch is kept in " + str(patch)
                )
        except Exception:
            for leftover in (out, xml):
                if leftover.exists():
                    leftover.unlink()
            raise
        changes = diff(self.export, after)
        self.state["versions"].append({"n": n, "message": message, "time": now(), "changes": changes})
        self.save_state()
        self._export = after
        return Result(n, message, changes, patch)

    def undo(self) -> int:
        if self.version == 0:
            raise PatchworkError("Nothing to undo: this is the opened file.")
        n = self.version
        for path in (self.file(n), self.export_path(n)):
            if path.exists():
                path.unlink()
        self.state["versions"].pop()
        self.save_state()
        self._export = None
        return self.version

    def save(self, dest: Path, force: bool = False) -> Path:
        dest = require_copy(Path(self.state["source"]), dest, force)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(self.file(), dest)
        return dest

    def log(self) -> list[dict]:
        return self.state["versions"]


def now() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")
