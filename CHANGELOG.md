# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

Not published on PyPI yet: `pip install filemaker-patchwork` still installs 0.1.0.

### Added

- `PATCHWORK_TOOL_TIMEOUT`: a Claris tool that does not answer is stopped after this many seconds (default 1800), with a message that names the tool.
- A warning line `! N new STEP step(s): they run when the file is used, check them before opening it` when a version adds Send Event, Perform AppleScript, Perform JavaScript in Web Viewer, Insert from URL, Open URL, Send Mail or Install Plug-In File.
- The MCP `initialize` instructions tell the agent that names, script text and calculations read from a file are data, never instructions.
- `.env.example` lists every variable Patchwork reads.
- Documentation: [ARCHITECTURE.md](ARCHITECTURE.md), the [MCP tools reference](docs/mcp-tools.md), [decision notes](docs/decisions/).

### Changed

- Through MCP, `patchwork_save` with `force` and `patchwork_open` with `force` are refused outside the project folder. Set `PATCHWORK_ALLOW_OUTSIDE=1` to allow them. The CLI is unchanged.
- The six MCP tools that can lose work (`open`, `replace`, `delete`, `push`, `undo`, `save`) declare `destructiveHint: true`. All tools said `false` before.
- The `image` extra needs Pillow 13 or later on Python 3.11+, and Pillow 12.3 or later on Python 3.10.

### Security

- A Claris tool in the current folder is never run, even when `PATH` contains `.` (relative `PATH` entries are skipped).
- SECURITY.md documents that the password reaches the Claris tools as a command-line argument, and the Pillow limit on Python 3.10.
- CI: every GitHub action is pinned to a commit, workflows get a read-only token, and blocking jobs run gitleaks, pip-audit, bandit, ruff, mypy, import-linter and a coverage threshold.

## [0.1.0] - 2026-11-09

First public release.

### Added

- A versioned working copy: `open`, `status`, `log`, `undo`, `save`. The source file is never modified.
- Reading: `ls` and `show`, including `show step NAME` for a real example of any script step.
- Editing: `add-field`, `add-value-list`, `add-custom-function`, `add-script`, `set-steps`, `append-steps`, `place-field`, `add`, `replace`, `delete`, `retheme`, `recolor-layouts`, `push`.
- Scripts as FileMaker text, both ways: `show script` prints one step per line (`Set Field [ Clients::Status ; "Gold" ]`), and the script commands take the same text. 25 common steps are written from text; any other step is kept as is when its line is unchanged. Checked on 15,000 steps from four real files.
- After every script change each step is re-read, and the version is refused if FileMaker dropped or changed a parameter.
- `place-field`: puts a field on a layout below another one, with a copy of its look and label. The objects underneath move down and the part grows.
- Every change is re-exported and compared with the previous version. A patch that FMUpgradeTool skipped is refused, and each version records what was added, changed and deleted.
- `uses`: what references an object (layouts, scripts, fields, value lists, tables, table occurrences, themes), and possible mentions by name in calculations. `delete` is refused while an object is referenced, unless `--force`.
- New value lists and custom functions are checked for content: Patchwork re-reads the values, the formula and the parameters, and drops the version if FileMaker lost them.
- `patchwork mcp`: an MCP server over stdio with 21 tools.
- Published on PyPI as `filemaker-patchwork`. The command is installed as both `patchwork` and `filemaker-patchwork`, so `uvx filemaker-patchwork mcp` runs the server without an install.
- End-to-end tests against the real Claris tools (`tests/test_integration.py`), run when `PATCHWORK_SAMPLE` points to the Claris Invoice solution.
- `patchwork init`: wires a new or existing folder for Claude Code, Cursor, Codex and Google Antigravity (agent rules, skills, MCP configuration). Existing files are kept. When `patchwork` is not on PATH, the MCP configuration points at the Python that ran `init`.
- `patchwork rebrand`: colors, fonts, logo and theme name on a whole solution from one `brand.json`.
- `patchwork tool`: the Claris tools file to file (`guids`, `export`, `validate`, `apply`, `new-file`), with the same safety checks.
- `patchwork doctor`.
- The [FMUpgradeTool field guide](docs/fmupgradetool-field-guide.md): what the tool silently skips, and the exact patch shapes for fields, scripts, steps, value lists, custom functions, layouts and themes, verified on real files.
