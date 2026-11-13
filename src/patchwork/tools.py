"""Run Claris FMUpgradeTool and FMDeveloperTool safely.

- The source file is never overwritten: every command writes a new copy.
- The password comes from PATCHWORK_PASSWORD (or --no-password) and is never printed.
"""

from __future__ import annotations

import os
import platform
import subprocess
from pathlib import Path

from patchwork import PatchworkError

PASSWORD_ENV = "PATCHWORK_PASSWORD"
KEY_ENV = "PATCHWORK_KEY"
TIMEOUT_ENV = "PATCHWORK_TOOL_TIMEOUT"
DEFAULT_TIMEOUT = 1800
SECRET_FLAGS = {"-src_pwd", "-src_key", "-patch_key"}
PATH_VARIABLES = {"FMUpgradeTool": "FM_UPGRADE_TOOL", "FMDeveloperTool": "FM_DEVELOPER_TOOL"}
LOCAL_TOOLS = Path(os.environ.get("LOCALAPPDATA", Path.home() / ".local" / "share")) / "patchwork" / "fms-tools"


def candidates(name: str) -> list[Path]:
    exe = name + (".exe" if platform.system() == "Windows" else "")
    found = []
    override = os.environ.get(PATH_VARIABLES.get(name, "FM_DEVELOPER_TOOL"))
    if override:
        found.append(Path(override))
    found += [Path(entry) / exe for entry in os.environ.get("PATH", "").split(os.pathsep) if Path(entry).is_absolute()]
    program_files = Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
    found += [
        program_files / "FileMaker" / "FileMaker Server" / "Database Server" / exe,
        LOCAL_TOOLS / "PFiles64" / "FileMaker" / "FileMaker Server" / "Database Server" / exe,
        Path("/Library/FileMaker Server/Database Server/bin") / name,
        Path("/opt/FileMaker/FileMaker Server/Database Server/bin") / name,
    ]
    return found


def find_tool(name: str) -> Path | None:
    for path in candidates(name):
        if path.is_file():
            return path
    if name == "FMDeveloperTool":
        upgrade = find_tool("FMUpgradeTool")
        if upgrade is not None:
            sibling = upgrade.with_name("FMDeveloperTool" + upgrade.suffix)
            if sibling.is_file():
                return sibling
    return None


def require_tool(name: str) -> Path:
    tool = find_tool(name)
    if tool is None:
        variable = PATH_VARIABLES.get(name, "FM_DEVELOPER_TOOL")
        raise PatchworkError(
            f"{name} not found. It ships with FileMaker Server (the free trial works). "
            f"See docs/install-fmupgradetool.md, or set {variable} to its path."
        )
    return tool


def password(no_password: bool) -> str:
    if no_password:
        return ""
    value = os.environ.get(PASSWORD_ENV)
    if not value:
        raise PatchworkError(
            f"Set {PASSWORD_ENV} in your shell, or pass --no-password if the account has none. "
            "Never put it in a file or on the command line."
        )
    return value


def timeout() -> float:
    value = os.environ.get(TIMEOUT_ENV)
    if value is None:
        return DEFAULT_TIMEOUT
    try:
        seconds = float(value)
    except ValueError:
        seconds = 0
    if not seconds > 0:
        raise PatchworkError(f"{TIMEOUT_ENV} must be a number of seconds above 0, got: {value}")
    return seconds


def redact(command: list[str]) -> list[str]:
    shown, hide = [], False
    for part in command:
        shown.append("***" if hide else part)
        hide = part in SECRET_FLAGS and not hide
    return shown


def same_path(left: Path, right: Path) -> bool:
    return os.path.normcase(str(left.resolve())) == os.path.normcase(str(right.resolve()))


def require_source(src: Path) -> Path:
    src = src.resolve()
    if not src.is_file():
        raise PatchworkError(f"Source file not found: {src}")
    if src.suffix.lower() != ".fmp12":
        raise PatchworkError(f"The source must be a .fmp12 file: {src.name}")
    return src


def require_copy(src: Path, dest: Path, force: bool) -> Path:
    dest = dest.resolve()
    if same_path(src, dest):
        raise PatchworkError("The destination is the source file. Patchwork always writes a copy.")
    if dest.suffix.lower() != ".fmp12":
        raise PatchworkError("The destination must end in .fmp12.")
    return require_new(dest, force)


def require_new(path: Path, force: bool) -> Path:
    path = path.resolve()
    if path.exists() and not force:
        raise PatchworkError(f"{path} already exists. Pass --force to replace it.")
    return path


def require_root(path: Path, expected: str) -> None:
    if not path.is_file():
        raise PatchworkError(f"File not found: {path}")
    found = root_tag(path)
    if found != expected:
        raise PatchworkError(f"{path.name} has root <{found or 'unreadable'}>, expected <{expected}>.")


def root_tag(path: Path) -> str | None:
    raw = path.read_bytes()[:8192]
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        text = raw.decode("utf-16", errors="ignore")
    else:
        text = raw.decode("utf-8-sig", errors="ignore")
    for token in text.split("<")[1:]:
        if token.startswith(("?", "!")):
            continue
        name = token.split(">", 1)[0].split()
        return name[0] if name else None
    return None


class Runner:
    """Builds and runs tool commands. `quiet` captures output and shows it only on failure."""

    def __init__(self, account: str, no_password: bool = False, quiet: bool = False, echo=print) -> None:
        self.account = account
        self.no_password = no_password
        self.quiet = quiet
        self.echo = echo

    def generate_guids(self, src: Path, dest: Path, force: bool = False) -> None:
        command = [str(require_tool("FMUpgradeTool")), "--generateGUIDs", "-src_path", str(src)]
        command += self.credentials() + ["-dest_path", str(dest)]
        if force:
            command.append("-force")
        self.run(command, dest)

    def export_xml(self, src: Path, out: Path, force: bool = False) -> None:
        tool = require_tool("FMDeveloperTool")
        command = [str(tool), "--saveAsXML", str(src), self.account, password(self.no_password), "-t", str(out), "-q"]
        if force:
            command.append("-f")
        shown = command.copy()
        shown[4] = "***"
        self.run(command, out, shown)

    def validate(self, src: Path, patch: Path) -> None:
        self.run(self.upgrade("--validatePatch", src, patch))

    def apply(self, src: Path, patch: Path, dest: Path, force: bool = False) -> None:
        command = self.upgrade("--update", src, patch) + ["-dest_path", str(dest)]
        if force:
            command.append("-force")
        self.run(command, dest)

    def new_file(self, xml: Path) -> None:
        self.run([str(require_tool("FMUpgradeTool")), "--generateDBFile", "-src_path", str(xml)])

    def upgrade(self, action: str, src: Path, patch: Path) -> list[str]:
        command = [str(require_tool("FMUpgradeTool")), action, "-src_path", str(src)]
        command += self.credentials() + ["-patch_path", str(patch), "-v"]
        key = os.environ.get(KEY_ENV)
        if key:
            command += ["-src_key", key]
        return command

    def credentials(self) -> list[str]:
        return ["-src_account", self.account, "-src_pwd", password(self.no_password)]

    def run(self, command: list[str], output: Path | None = None, shown: list[str] | None = None) -> None:
        if not self.quiet:
            self.echo("$ " + " ".join(shown or redact(command)))
        limit = timeout()
        try:
            completed = subprocess.run(
                command, check=False, capture_output=self.quiet, text=True, errors="replace", timeout=limit
            )
        except subprocess.TimeoutExpired:
            raise PatchworkError(
                f"{Path(command[0]).stem} did not finish within {limit:g} s and was stopped. "
                f"Is a FileMaker dialog waiting, or the file open elsewhere? Set {TIMEOUT_ENV} to wait longer."
            ) from None
        failed = completed.returncode != 0 or (output is not None and not output.exists())
        if failed:
            details = ((completed.stdout or "") + (completed.stderr or "")).strip() if self.quiet else ""
            hint = " Is the file open in FileMaker? Close it (error 803)." if "803" in details else ""
            raise PatchworkError(
                f"{Path(command[0]).stem} failed (exit {completed.returncode}).{hint}"
                + (f"\n{details}" if details else "")
            )
