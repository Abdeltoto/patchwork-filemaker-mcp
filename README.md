<!-- mcp-name: io.github.Abdeltoto/patchwork -->
<div align="center">

<img src="https://raw.githubusercontent.com/Abdeltoto/patchwork-filemaker-mcp/main/docs/images/banner.png" alt="Patchwork: let your AI agent edit FileMaker" width="100%">

<br>

[![CI](https://img.shields.io/github/actions/workflow/status/Abdeltoto/patchwork-filemaker-mcp/ci.yml?branch=main&style=flat-square&label=CI)](https://github.com/Abdeltoto/patchwork-filemaker-mcp/actions/workflows/ci.yml)
[![Stars](https://img.shields.io/github/stars/Abdeltoto/patchwork-filemaker-mcp?style=flat-square&color=8b5cf6)](https://github.com/Abdeltoto/patchwork-filemaker-mcp/stargazers)
[![License: MIT](https://img.shields.io/badge/license-MIT-14b8a6?style=flat-square)](https://github.com/Abdeltoto/patchwork-filemaker-mcp/blob/main/LICENSE)
![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white)
![FileMaker 2026](https://img.shields.io/badge/FileMaker-2026-000000?style=flat-square&logo=claris&logoColor=white)
![MCP server](https://img.shields.io/badge/MCP-server-000000?style=flat-square&logo=modelcontextprotocol&logoColor=white)
![Zero dependencies](https://img.shields.io/badge/dependencies-0-f59e0b?style=flat-square)
[![PRs welcome](https://img.shields.io/badge/PRs-welcome-ff69b4?style=flat-square)](https://github.com/Abdeltoto/patchwork-filemaker-mcp/blob/main/CONTRIBUTING.md)

<a href="#connect-your-agent"><img src="https://img.shields.io/badge/Claude_Code-191919?style=for-the-badge&logo=claude&logoColor=D97757" alt="Claude Code"></a>
<a href="#connect-your-agent"><img src="https://img.shields.io/badge/Cursor-000000?style=for-the-badge&logo=cursor&logoColor=white" alt="Cursor"></a>
<a href="#connect-your-agent"><img src="https://img.shields.io/badge/Codex-000000?style=for-the-badge&logo=data:image/svg%2bxml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI+PHJlY3QgeD0iMS41IiB5PSIzIiB3aWR0aD0iMjEiIGhlaWdodD0iMTgiIHJ4PSI0IiBmaWxsPSJub25lIiBzdHJva2U9IiNmZmYiIHN0cm9rZS13aWR0aD0iMiIvPjxwYXRoIGQ9Ik02LjUgOWwzLjUgMy0zLjUgMyIgZmlsbD0ibm9uZSIgc3Ryb2tlPSIjZmZmIiBzdHJva2Utd2lkdGg9IjIiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCIvPjxwYXRoIGQ9Ik0xMi41IDE1LjVoNSIgc3Ryb2tlPSIjZmZmIiBzdHJva2Utd2lkdGg9IjIiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIvPjwvc3ZnPg==" alt="Codex"></a>
<a href="#connect-your-agent"><img src="https://img.shields.io/badge/Antigravity-1a1a2e?style=for-the-badge&logo=google&logoColor=4285F4" alt="Google Antigravity"></a>

**[Quick start](#quick-start)** · **[Examples](#see-it-in-action)** · **[Connect your agent](#connect-your-agent)** · **[What it can change](#what-it-can-change)** · **[Field guide](https://github.com/Abdeltoto/patchwork-filemaker-mcp/blob/main/docs/fmupgradetool-field-guide.md)** · **[Français](https://github.com/Abdeltoto/patchwork-filemaker-mcp/blob/main/README.fr.md)**

<br>

<img src="https://raw.githubusercontent.com/Abdeltoto/patchwork-filemaker-mcp/main/docs/images/demo.gif" alt="Real session on Claris Invoice: one sentence asks for a Loyalty Tier field under Contact Email. The agent calls patchwork_add_field and patchwork_place_field, the field appears on the layout, and the change is verified by re-export." width="100%">

</div>

<br>

> **Friday, 4 PM. A client asks for "just one more field" on the detail layout.**
> You know the drill: define the field, copy the label, nudge every object below it, stretch the part… then do it all again on the next layout.
>
> **Patchwork lets your AI agent do those clicks for you.** Just ask, in your own words, the way you would ask a colleague. Your agent adds the field and places it right where you said, writes scripts, creates value lists and restyles layouts, in a real `.fmp12` file. Every change is checked, every change can be undone, and your original file is never touched.

Free and open source. Works with Claude Code, Cursor, Codex and Antigravity.

<p align="center"><a href="https://youtu.be/AkFhBpB0YYY"><img src="https://raw.githubusercontent.com/Abdeltoto/patchwork-filemaker-mcp/main/docs/images/video-card.jpg" alt="Watch the 90-second Patchwork intro on YouTube" width="80%"></a><br><sub>▶ <a href="https://youtu.be/AkFhBpB0YYY">Watch the 90-second intro on YouTube</a> · <a href="https://youtu.be/g5UkJLiYAhA">Version française</a></sub></p>

## Requirements

- Python 3.10 or later, on Windows, macOS or Linux.
- The Claris command-line tools FMUpgradeTool and FMDeveloperTool. They come with the FileMaker Server installer (the free trial works), and no server has to run: [install the Claris tools](https://github.com/Abdeltoto/patchwork-filemaker-mcp/blob/main/docs/install-fmupgradetool.md). Verified with FileMaker 2026 (26.0.3).
- A closed `.fmp12` and a Full Access account.

## Quick start

Three commands, then you just talk to your agent.

```bash
pip install filemaker-patchwork
patchwork doctor          # finds the Claris command-line tools
patchwork init .          # wires this folder for Claude Code, Cursor, Codex and Antigravity
```

No install with [uv](https://docs.astral.sh/uv/): `uvx filemaker-patchwork doctor`, and `uvx filemaker-patchwork mcp` as the MCP server command.

Then ask your agent: *"Open Invoice.fmp12 and add a Status field to Clients."* That's it.

### Good to know

- **It changes structure, not records.** Fields, scripts, layouts, value lists, themes. For your data, use the Data API or OData.
- **It works on closed files, not hosted ones.** Edit a copy, test it, then deploy it as you usually do.
- **It needs the Claris command-line tools** (FMUpgradeTool and FMDeveloperTool). They come with the FileMaker Server installer, the free trial works, and no server has to run: [install the Claris tools](https://github.com/Abdeltoto/patchwork-filemaker-mcp/blob/main/docs/install-fmupgradetool.md). Patchwork itself has no other dependency.

## See it in action

Four real sessions on the free [Claris Invoice solution](https://marketplace.claris.com/detail/2000.html). For each one: what was asked, what the agent did, and the file before and after. No mockups.

<p align="center"><img src="https://raw.githubusercontent.com/Abdeltoto/patchwork-filemaker-mcp/main/docs/images/example-schema.png" alt="Prompt: add a Loyalty Tier field and a value list. The field and the value list appear in the file." width="100%"></p>

<p align="center"><img src="https://raw.githubusercontent.com/Abdeltoto/patchwork-filemaker-mcp/main/docs/images/example-script.png" alt="Prompt: write a Say Hello script. The agent copies a real dialog step and creates a two-step script." width="100%"></p>

<p align="center"><img src="https://raw.githubusercontent.com/Abdeltoto/patchwork-filemaker-mcp/main/docs/images/example-cleanup.png" alt="Prompt: remove the Dev layouts. Six layouts are deleted and the agent warns about three scripts that pointed at them." width="100%"></p>

<p align="center"><img src="https://raw.githubusercontent.com/Abdeltoto/patchwork-filemaker-mcp/main/docs/images/example-rebrand.png" alt="Prompt: rebrand for Maple and Oak. The blue Claris header becomes a forest green Maple and Oak header." width="100%"></p>

## How it works

<p align="center"><img src="https://raw.githubusercontent.com/Abdeltoto/patchwork-filemaker-mcp/main/docs/images/how-it-works.jpg" alt="An AI agent stitches patches onto a FileMaker file, with a verified check and an undo arrow" width="80%"></p>

Why can't your agent just do this on its own? A FileMaker file is a binary file, and its structure hides behind dialogs an agent cannot click. Claris does ship a command-line way in, [FMUpgradeTool](https://help.claris.com/en/app-upgrade-tool-guide/content/index.html), but it is picky: every object is addressed by a UUID, and a patch that is slightly wrong is **silently skipped**, while the tool still prints `Patch File Applied`.

Patchwork is the careful assistant in between:

| | |
|:-:|---|
| 🧵 **Writes the patch** | Reads the file's XML export and builds a patch with the right UUIDs, ids and catalog structure, so your agent doesn't have to |
| 🔍 **Checks the result** | Re-exports the file after every change and compares it with the previous version. If FileMaker skipped something, the change is refused, not silently lost |
| 🧭 **Warns before breaking** | Before a delete, it lists the scripts, layouts and calculations that use the object, and waits for your OK |
| 🕐 **Keeps every version** | Each change is a numbered version with its diff. Changed your mind? `undo` always works |
| 🔒 **Protects the original** | Everything happens on a working copy. `save` writes a new file and never overwrites yours |

More in [how it works](https://github.com/Abdeltoto/patchwork-filemaker-mcp/blob/main/docs/how-it-works.md).

## Connect your agent

One command sets everything up. Run `patchwork init .` in your project folder, new or existing: it adds the rules, the skills and the MCP configuration for every agent, and keeps the files you already have.

| Agent | Configuration written by `init` | Then |
|---|---|---|
| <img src="https://cdn.simpleicons.org/claude/D97757" width="16"> **Claude Code** | `.mcp.json` · `CLAUDE.md` · `.claude/skills/` | Run `claude` in the folder and approve `patchwork` |
| <img src="https://cdn.simpleicons.org/cursor/808080" width="16"> **Cursor** | `.cursor/mcp.json` · `.cursor/skills/` | Enable `patchwork` in Settings › MCP |
| ⌨️ **Codex** | `.codex/config.toml` · `AGENTS.md` · `.agents/skills/` | Trust the project when Codex asks |
| <img src="https://cdn.simpleicons.org/google/4285F4" width="16"> **Antigravity** | `.agents/mcp_config.json` · `AGENTS.md` · `.agents/skills/` | Open the folder as a workspace |

Every agent gets the same 21 tools through `patchwork mcp`, a stdio MCP server. Your file's password stays yours: set it once in your shell with `PATCHWORK_PASSWORD`, and agents never see it. Manual setup: [AI agents](https://github.com/Abdeltoto/patchwork-filemaker-mcp/blob/main/docs/ai-agents.md). Every tool, its parameters, answers and errors: [MCP tools reference](https://github.com/Abdeltoto/patchwork-filemaker-mcp/blob/main/docs/mcp-tools.md).

## What it can change

Fields, plain-text scripts, value lists, colors and fonts, even a full rebrand. Every operation below was tried on real files and confirmed by re-exporting them.

| | Add | Edit | Delete |
|---|:-:|:-:|:-:|
| **Fields** · text, number, date, time, timestamp, container, calculation, global | ✅ | | ✅ |
| **Scripts**, read and written as FileMaker text | ✅ | ✅ | ✅ |
| **Value lists** | ✅ | ✅ | ✅ |
| **Custom functions** | ✅ | ✅ | ✅ |
| **Layouts** · place a field with its label, whole layout, colors, fonts, swap a field | ✅ field | ✅ | ✅ |
| **Themes** · colors, fonts, name | | ✅ | |
| **Tables**, table occurrences | 👁 read | | |

> [!TIP]
> Scripts read and write the way the Script Workspace shows them, one step per line:
> `Set Field [ Clients::Status ; "Gold" ]`. Edit the text of `patchwork show script NAME` and send it back with `set-steps`: untouched lines keep their exact step, and every step is re-read after the change, so a dropped parameter is caught.

What FMUpgradeTool cannot do (record data, a brand-new theme, a single layout object on its own) is listed in [the field guide](https://github.com/Abdeltoto/patchwork-filemaker-mcp/blob/main/docs/fmupgradetool-field-guide.md).

## Use it without an agent

Prefer the terminal? Everything the agent does is a plain command you can run yourself:

```bash
export PATCHWORK_PASSWORD='...'                     # Windows: $env:PATCHWORK_PASSWORD = '...'
patchwork open "Invoice.fmp12" --account Admin     # working copy, version v000 (--no-password if the account has none)
patchwork add-field Clients "Loyalty Tier"
patchwork add-value-list "Loyalty Tiers" Bronze Silver Gold
patchwork log                                       # every version and what changed
patchwork undo
patchwork save "Invoice v2.fmp12"
```

<details>
<summary><b>All commands</b></summary>

<br>

| Command | What it does |
|---|---|
| `open SRC --account NAME` | Starts a working copy in `.patchwork/` (version v000). The source is never modified |
| `status`, `log` | Current version, and every version with what changed |
| `ls [KIND] [TABLE]` | Lists layouts, scripts, value lists, custom functions, themes, tables, fields |
| `show KIND NAME` | Prints a script as FileMaker text (`--xml` for XML), anything else as XML. `show step NAME` prints a real example of a step |
| `palette [--theme NAME]` | Colors a theme uses, most frequent first |
| `add-field TABLE NAME` | Adds a field: `--type`, `--calc`, `--global`, `--image logo.png` |
| `add-value-list NAME VALUES...` | Adds a custom value list |
| `add-custom-function NAME --calc` | Adds a custom function, with `--param` |
| `add-script NAME STEPS.txt` | Creates a script from FileMaker script text (or `<Step>` XML) |
| `set-steps`, `append-steps` | Rewrites a script with edited text from `show`, or adds steps at the end |
| `place-field LAYOUT TO::FIELD --near FIELD` | Puts a field on a layout below another one, with a copy of its look and label. `--side right`, `--label` |
| `add KIND FILE.xml` | Adds a value list or a custom function from XML |
| `replace KIND NAME FILE.xml` | Replaces an object with your edited version of `show` |
| `uses KIND NAME` | Lists what references an object, and where its name appears in calculations |
| `delete KIND NAME` | Deletes a script, layout, value list, custom function or field. Refused while other objects reference it, unless `--force` |
| `retheme`, `recolor-layouts` | Rewrites colors and fonts of a theme, or of the layouts' local styles |
| `push PATCH.xml` | Applies a hand-written FMUpgradeTool patch, with the same checks |
| `undo` | Drops the last version |
| `save DEST` | Writes the current version to a new `.fmp12` |
| `rebrand SRC DEST --brand brand.json` | One shot: colors, fonts, logo and theme name on a whole solution |
| `mcp` | The MCP server for agents |
| `init DIR` | Wires a folder for Claude Code, Cursor, Codex and Antigravity |
| `doctor` | Shows which Claris tools Patchwork found. Exit code 2 if one is missing |
| `tool guids\|export\|validate\|apply\|new-file` | Runs one Claris tool directly, file to file, with the same path checks |

Every editing command takes `-m "note"` for the log and `--dry-run` to write the patch without applying it. `-C DIR`, before the command, picks the project folder: `patchwork -C ~/crm status`. Without it, Patchwork uses `PATCHWORK_PROJECT`, then the nearest `.patchwork/` from the current folder upward. `open` is the exception: it creates `.patchwork/` in the `-C` folder, else in the current folder. `patchwork COMMAND --help` lists every option. More in [examples and recipes](https://github.com/Abdeltoto/patchwork-filemaker-mcp/tree/main/examples).

</details>

## Environment variables

Patchwork reads these from the environment. It never loads a `.env` file: set them in your shell or in the `env` block of your MCP client. [`.env.example`](https://github.com/Abdeltoto/patchwork-filemaker-mcp/blob/main/.env.example) lists them.

| Variable | Used for |
|---|---|
| `PATCHWORK_PASSWORD` | Password of the account given to `open`. Required unless `--no-password`. Never printed |
| `PATCHWORK_KEY` | Encryption key, for files with encryption at rest. Passed to FMUpgradeTool when a patch is validated or applied, not when the file is copied or exported. Never printed. A full session on an encrypted file is to be confirmed |
| `PATCHWORK_PROJECT` | Project folder holding `.patchwork/`, when `-C` is not given. Not used by `open` |
| `FM_UPGRADE_TOOL`, `FM_DEVELOPER_TOOL` | Paths of the Claris tools, when `doctor` does not find them |
| `PATCHWORK_ALLOW_OUTSIDE` | `1` lets MCP tools use `force` outside the project folder. Not in release 0.1.0 |
| `PATCHWORK_TOOL_TIMEOUT` | Seconds before a Claris tool that does not answer is stopped. Default 1800. Not in release 0.1.0 |
| `PATCHWORK_SAMPLE` | Tests only: a copy of the Claris Invoice solution for the end-to-end tests |

## Run from source and test

```bash
git clone https://github.com/Abdeltoto/patchwork-filemaker-mcp
cd patchwork-filemaker-mcp
python -m venv .venv
. .venv/bin/activate                 # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -e ".[image]"
python -m unittest discover -s tests
```

The unit tests need neither FileMaker nor the Claris tools. The end-to-end tests, lint and coverage checks are in [CONTRIBUTING.md](https://github.com/Abdeltoto/patchwork-filemaker-mcp/blob/main/CONTRIBUTING.md).

## Repository layout

```
src/patchwork/        the package: CLI, MCP server, FileMaker logic
  skills/, templates/ what `patchwork init` copies into a project
tests/                unit tests, fixtures/ (fictional exports), test_integration.py (real files)
docs/                 guides, MCP tools reference, decisions/
examples/             recipes and the Maple & Oak brand
scripts/              extract-fms-tools.ps1 (Claris tools from the .msi, Windows)
brand.schema.json     JSON schema of brand.json
server.json           entry for the MCP registry
```

How the modules fit together: [ARCHITECTURE.md](https://github.com/Abdeltoto/patchwork-filemaker-mcp/blob/main/ARCHITECTURE.md).

## The FMUpgradeTool field guide

The [field guide](https://github.com/Abdeltoto/patchwork-filemaker-mcp/blob/main/docs/fmupgradetool-field-guide.md) collects every trap FMUpgradeTool sets without telling you, found the hard way on real files. Useful even if you never use Patchwork. A taste:

- without `--generateGUIDs`, theme and field patches are skipped;
- a layout's UUID is **not** the first `<UUID>` inside it;
- replacing one layout object is skipped, replacing the whole layout works;
- deleting a script step needs a `ScriptReference` inside each `ScriptStepReference`.

Found another one? [Add it](https://github.com/Abdeltoto/patchwork-filemaker-mcp/issues/new?template=field-guide.yml).

## FAQ

<details>
<summary><b>Does it work on hosted files?</b></summary>
<br>
It works on closed <code>.fmp12</code> files on disk. Take a copy of the hosted file, edit it, test it, then deploy it as you usually do, or move the data with the Claris Data Migration Tool.
</details>

<details>
<summary><b>Can the agent change records?</b></summary>
<br>
No, FMUpgradeTool changes structure only. For records, use the Data API or OData. The <code>fm-data</code> skill explains how.
</details>

<details>
<summary><b>Which FileMaker versions?</b></summary>
<br>
Developed and verified with FileMaker 2026 (26.0.3). Earlier versions that ship FMUpgradeTool and <code>FMDeveloperTool --saveAsXML</code> should work but are untested. A report either way is very welcome.
</details>

<details>
<summary><b>macOS and Linux?</b></summary>
<br>
Wherever the Claris tools run. CI runs on Windows, macOS and Linux.
</details>

<details>
<summary><b>Is my password safe with an agent?</b></summary>
<br>
Yes. It is read from the <code>PATCHWORK_PASSWORD</code> environment variable, passed to the Claris tools, and printed as <code>***</code>. It is never written in a configuration file or shown to the agent.
</details>

## Contributing

Found a new FMUpgradeTool trap, wrote a recipe, or want a new operation? Everything is welcome: start with [CONTRIBUTING.md](https://github.com/Abdeltoto/patchwork-filemaker-mcp/blob/main/CONTRIBUTING.md). And if Patchwork gives you your Friday afternoon back, a ⭐ helps other FileMaker developers find it.

<a href="https://star-history.com/#Abdeltoto/patchwork-filemaker-mcp&Date">
  <img src="https://api.star-history.com/svg?repos=Abdeltoto/patchwork-filemaker-mcp&type=Date" alt="Star history" width="600">
</a>

## License

[MIT](https://github.com/Abdeltoto/patchwork-filemaker-mcp/blob/main/LICENSE). Patchwork is a community project, not affiliated with or endorsed by Claris International Inc. FileMaker and Claris are trademarks of Claris International Inc. Other product names and logos belong to their owners.
