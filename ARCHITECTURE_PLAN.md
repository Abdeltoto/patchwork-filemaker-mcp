# Architecture plan

[ARCHITECTURE.md](ARCHITECTURE.md) describes the code as it is. This file says what must stay true as the code grows, where a new piece goes, and which structural changes are proposed next.

**Status: draft.** Written from a reading of the code at `e5a0fbb`. The rules in sections 1 and 2 are already enforced. The steps in section 4 are proposals: none is decided until it has a note in [docs/decisions/](docs/decisions/).

## 1. What must stay true

These are the promises the README makes to the user. A change that breaks one is not a refactor, it is a new decision.

| Rule | Where it is kept | Decision |
|---|---|---|
| The source file is never written | `tools.require_source`, `require_copy`, `Workspace.save` | [0002](docs/decisions/0002-versioned-working-copy.md) |
| Every change is a new version that can be dropped | `Workspace.apply`, `Workspace.undo` | [0002](docs/decisions/0002-versioned-working-copy.md) |
| A change FMUpgradeTool skipped is refused | `Workspace.apply` (export compared), `ops.run` (expected line and content check) | [0003](docs/decisions/0003-verify-by-re-export.md) |
| No runtime dependency | `dependencies = []`, `pip-audit` in CI | [0001](docs/decisions/0001-standard-library-only.md) |
| The password is read from the environment and never printed or stored | `tools.password`, `tools.redact` | [0005](docs/decisions/0005-password-from-environment.md) |
| Only `tools` starts a process | import-linter contracts | [0009](docs/decisions/0009-layer-contracts.md) |
| One bad MCP call never stops the server | `mcp.Server.handle` | [0007](docs/decisions/0007-mcp-guard-rails.md) |
| Text read from a `.fmp12` is data, never instructions | `mcp.INSTRUCTIONS`, `templates/AGENTS.md` | [0007](docs/decisions/0007-mcp-guard-rails.md) |

## 2. Layer plan

Five layers. An import goes down, never up. The contracts are in `pyproject.toml` under `[tool.importlinter]` and run in the CI `lint` job.

| Layer | Modules | May import | Holds |
|---|---|---|---|
| Interfaces | `__main__`, `cli`, `mcp` | everything below | Argument parsing, JSON-RPC, printing. No FileMaker logic. |
| Application | `ops`, `rebrand`, `project` | working copy, domain, `tools` | One function per user action. Builds the patch, applies it, checks the result. The three do not import each other. |
| Working copy | `workspace` | domain, `tools` | `.patchwork/`: versions, state, undo, save. |
| Domain | `export`, `objects`, `build`, `script`, `place`, `uses` | each other only | Reads exports and builds patch XML. Imports nothing from the layers above and starts no process. |
| Claris tools | `tools` | nothing in the package | Finds and runs FMUpgradeTool and FMDeveloperTool. Path checks. |

### Where a new piece goes

- **A new object kind or patch shape** (for example: edit a field): the XML goes in `objects` or `build`, with a unit test on a fixture export. No I/O.
- **A new user action**: one function in `ops` that returns text, built on `ops.run` so that the expected line and the content check are not skipped. Then one argparse command in `cli`, one entry in `mcp.TOOLS`, one section in `docs/mcp-tools.md`, and a line in `CHANGELOG.md`.
- **A new script step readable as text**: `script.STEP_IDS` and its builder, with a round-trip test (text to XML to text).
- **A new call to a Claris tool**: a method on `tools.Runner`. Nothing else calls `subprocess`.
- **A new module**: add it to a contract in `pyproject.toml` in the same commit. A module that is in no contract is not checked.
- **A finding about FMUpgradeTool**: `docs/fmupgradetool-field-guide.md`, with the FileMaker version it was seen on.

## 3. Gaps seen in the code

Facts, not judgments. Each one is the starting point of a step in section 4.

| # | Gap | Where |
|---|---|---|
| G1 | The workspace has no lock. `state.json` is rewritten in place. Two processes on the same `.patchwork/` (two agents, or the CLI next to the MCP server) can both build version N+1. | `workspace.Workspace.apply`, `save_state` |
| G2 | Every version keeps a full `.fmp12` and a full XML export. Nothing removes old ones. | `workspace.Workspace.file`, `export_path` |
| G3 | Every MCP call builds a new `Workspace` and reads the whole export again. The cost on a large file was never measured (also noted in decisions 0003 and 0008). | `mcp.Server.workspace`, `export.Export.load` |
| G4 | An action is declared in three places by hand: `cli` (argparse), `mcp.TOOLS` (schema), `docs/mcp-tools.md`. No test compares them. | `cli.py`, `mcp.py`, `docs/mcp-tools.md` |
| G5 | The types of MCP arguments are not checked against their schema. A wrong type reaches `ops`. | `mcp.Server.call` |
| G6 | `ops` returns text only. An agent has to read `v001  message` and `+ field ...` lines to know what changed. | `ops.describe`, `mcp.Server.handle` |
| G7 | `rebrand` has its own apply-export-check loop in a temporary folder, beside the one in `workspace`. It is not an MCP tool. | `rebrand.rebrand`, `rebrand.step` |
| G8 | The export is read with regular expressions. Decision 0001 marks the reason as *to be confirmed*. | `export.py`, `objects.py` |
| G9 | The end-to-end tests need a real file and the Claris tools, so CI skips all 11. Only a developer's machine proves that a patch works on FileMaker. | `tests/test_integration.py` |
| G10 | The version number is written in `patchwork/__init__.py` and twice in `server.json`. No test checks that they match. | `__init__.py`, `server.json` |
| G11 | `patchwork_uses` changes nothing but is not marked read-only (noted in decision 0007). | `mcp.TOOLS` |

## 4. Proposed steps

In order. Each step is small enough for one pull request and keeps every rule of section 1.

### Now: before the next release

1. **Publish what is already fixed.** The MCP guard rails, the relative `PATH` fix and the tool timeout are in `[Unreleased]`, so `pip install filemaker-patchwork` still gives 0.1.0 without them. Release 0.1.1. *Done when:* PyPI and `server.json` show the same version as `__init__.py`.
2. **One test for the version (G10).** A unit test reads `server.json` and compares both versions with `patchwork.__version__`. *Layer:* tests only.
3. **One test for the tool list (G4).** A unit test checks that every name in `mcp.TOOLS` has a heading in `docs/mcp-tools.md`, and that the count the README states is the real one. *Layer:* tests only.
4. **Mark `patchwork_uses` read-only (G11)**, or write in decision 0007 why it is not.

### Next: safety of the working copy

5. **Lock the workspace (G1).** `Workspace.apply` and `undo` take an exclusive lock file in `.patchwork/` (`os.open` with `O_CREAT | O_EXCL`, standard library, works on Windows). The file holds the process id, so a lock left by a crash can be told from a live one. A second writer gets a `PatchworkError` that says who holds it. Write `state.json` to a temporary file, then `os.replace`. *Layer:* working copy. *Done when:* a test starts two applies and one is refused.
6. **Check MCP argument types (G5).** A small validator in `mcp` for the schema subset the tools use: `string`, `boolean`, `array` of strings, `object`, `enum`. A wrong type is a tool error that names the argument. *Layer:* interfaces. No dependency.
7. **Prune old versions (G2).** `patchwork prune --keep N` removes the `.fmp12` and `.xml` of old versions and keeps their line in the log. `undo` refuses to go below the oldest kept version. Needs a decision note: it changes what "undo always works" means. *Layer:* working copy, then `ops`, `cli`, `mcp`.

### Later: measure first

8. **Measure a large file (G3).** Time `open`, one `add-field` and one `show` on a real solution of several hundred megabytes. Record the numbers in decisions 0003 and 0008. Only then decide whether the MCP server keeps the `Export` in memory between calls (keyed on the version number and the file's modification time).
9. **Structured results (G6).** `ops` functions return the `Result` they already have. `cli` and `mcp` format it. MCP then adds `structuredContent` (version, changes, warnings) beside the text. This moves formatting up into the interfaces, where the layer plan says printing belongs.
10. **One change loop (G7).** `rebrand` reuses the apply-export-check of `workspace` on a temporary workspace, in place of its own `step`. After that, a `patchwork_rebrand` MCP tool is one entry in `mcp.TOOLS`.
11. **Decide on the XML reader (G8).** Confirm or replace the regular expressions. Keeping them is a valid outcome if the reason is written: a replace patch needs the exact text of a block, which a parser does not give back. Close the *to be confirmed* in decision 0001 either way.
12. **End-to-end tests outside a laptop (G9).** The Claris tools cannot be put in a public CI image. Options to study: a self-hosted runner with FileMaker Server, or recorded exports (before and after each patch) checked in as fixtures so that the diff and check logic runs in CI against real output.

## 5. Out of scope

- Record data. FMUpgradeTool does not change it. The Data API and OData do.
- Hosted or open files. Patchwork works on a closed copy.
- An HTTP transport. The MCP server is stdio only, started by the agent on the developer's machine.
- A runtime dependency, an MCP SDK included (decision 0001).

## 6. Changing this plan

A step that is done moves to `CHANGELOG.md` and leaves this file. A step that is refused gets one line here with the reason. A rule of section 1 or 2 changes only with a decision note.
