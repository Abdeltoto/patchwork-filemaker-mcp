# 0006. Never run a Claris tool found in the current folder

## Context

Patchwork passes the password to the tool it runs. On Windows, a lookup through `PATH` could pick an `FMUpgradeTool.exe` placed in the current folder, for example inside a project an agent was asked to open. The security audit rated this High (H1).

## Choice

`tools.candidates` looks, in order, at `FM_UPGRADE_TOOL` or `FM_DEVELOPER_TOOL`, the absolute folders of `PATH`, then the install locations of FileMaker Server and the folder `scripts/extract-fms-tools.ps1` extracts to. Relative `PATH` entries such as `.` are skipped. `FMDeveloperTool` is also looked for next to the `FMUpgradeTool` found.

## Consequences

- A tool in the current folder is never run, even if `PATH` contains `.`.
- A user who keeps the tools in an unusual place sets the two variables.
- `test_tool_in_the_current_folder_is_never_picked` changes the current folder for its duration, because the bug it guards against depends on it.
