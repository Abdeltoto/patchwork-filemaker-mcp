"""`patchwork init`: a project folder wired for Claude Code, Cursor, Codex and Google Antigravity.

Antigravity and Codex read AGENTS.md; Claude Code reads CLAUDE.md, which imports it.
Skills go to .cursor/skills, .claude/skills and .agents/skills (Antigravity, Codex).
Existing files are never overwritten, so `init` can wire an existing folder.
"""

from __future__ import annotations

import json
import shutil
import sys
from importlib import resources
from pathlib import Path

SKILL_HOMES = (".cursor/skills", ".claude/skills", ".agents/skills")


class Init:
    def __init__(self, root: Path):
        self.root = root
        self.written: list[str] = []
        self.kept: list[str] = []

    def write(self, relative: str, text: str) -> None:
        path = self.root / relative
        if path.exists():
            self.kept.append(relative)
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        self.written.append(relative)

    def report(self) -> str:
        lines = [f"Project ready: {self.root}"]
        lines += [f"  + {name}" for name in self.written]
        if self.kept:
            lines.append(f"  kept {len(self.kept)} existing file(s): {', '.join(self.kept)}")
        return "\n".join(lines)


def init_project(directory: Path, name: str, skills: bool = True) -> Init:
    root = directory.resolve()
    root.mkdir(parents=True, exist_ok=True)
    init = Init(root)
    values = {"NAME": name.strip() or root.name}
    init.write("AGENTS.md", template("AGENTS.md", values))
    init.write("CLAUDE.md", "@AGENTS.md\n")
    init.write("standards/naming.md", template("naming.md", values))
    init.write(".gitignore", template("gitignore", values))
    init.write("patches/.gitkeep", "")
    for relative, text in mcp_configs(root).items():
        init.write(relative, text)
    if skills:
        source = resources.files("patchwork") / "skills"
        for home in SKILL_HOMES:
            for skill in source.iterdir():
                if skill.is_dir():
                    init.write(f"{home}/{skill.name}/SKILL.md", (skill / "SKILL.md").read_text(encoding="utf-8"))
    return init


def server_command() -> tuple[str, list[str]]:
    """`patchwork` when agents can find it on PATH, otherwise this Python with `-m patchwork`."""
    if shutil.which("patchwork"):
        return "patchwork", []
    return sys.executable, ["-m", "patchwork"]


def mcp_configs(root: Path) -> dict[str, str]:
    command, prefix = server_command()
    server = {"command": command, "args": [*prefix, "mcp"]}
    cursor = {
        "mcpServers": {
            "patchwork": {
                **server,
                "args": [*prefix, "-C", "${workspaceFolder}", "mcp"],
                "env": {"PATCHWORK_PASSWORD": "${env:PATCHWORK_PASSWORD}"},
            }
        }
    }
    claude = {"mcpServers": {"patchwork": {**server, "env": {"PATCHWORK_PASSWORD": "${PATCHWORK_PASSWORD:-}"}}}}
    antigravity = {"mcpServers": {"patchwork": {**server, "cwd": str(root)}}}
    codex = (
        "[mcp_servers.patchwork]\n"
        f"command = {json.dumps(command)}\n"
        f"args = {json.dumps(server['args'])}\n"
        f"cwd = {json.dumps(str(root))}\n"
        'env_vars = ["PATCHWORK_PASSWORD"]\n'
    )
    return {
        ".cursor/mcp.json": json.dumps(cursor, indent=2) + "\n",
        ".mcp.json": json.dumps(claude, indent=2) + "\n",
        ".agents/mcp_config.json": json.dumps(antigravity, indent=2) + "\n",
        ".codex/config.toml": codex,
    }


def template(name: str, values: dict[str, str]) -> str:
    text = (resources.files("patchwork") / "templates" / name).read_text(encoding="utf-8")
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", value)
    return text
