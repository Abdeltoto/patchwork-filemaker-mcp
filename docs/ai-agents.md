# Using Patchwork with AI agents

Patchwork gives an AI agent direct, checked access to the structure of a FileMaker file. It works the same way in Claude Code, Cursor, Codex and Google Antigravity:

- **`patchwork mcp`** is an MCP server over stdio. The agent calls tools such as `patchwork_add_field` and gets plain-text results back, including the diff of every change.
- **`AGENTS.md` and the skills** teach the agent the workflow: open, look, change, check, save.

## Wire a folder

```bash
cd my-filemaker-project
patchwork init .
```

`init` works on a new or an existing folder and never overwrites a file you already have. It writes:

```
AGENTS.md                    rules every agent reads first (Codex, Antigravity, Cursor)
CLAUDE.md                    imports AGENTS.md for Claude Code
standards/naming.md          your naming conventions, filled in with the agent
patches/.gitkeep             hand-written patches, if you keep any
.gitignore                   ignores .fmp12 files and backups, .patchwork/, raw/, .env files
.mcp.json                    MCP server for Claude Code
.cursor/mcp.json             MCP server for Cursor
.codex/config.toml           MCP server for Codex
.agents/mcp_config.json      MCP server for Antigravity
.cursor/skills/  .claude/skills/  .agents/skills/
```

Set the password once in your shell, never in a file the agent reads:

```bash
export PATCHWORK_PASSWORD='...'          # macOS, Linux
$env:PATCHWORK_PASSWORD = '...'          # Windows PowerShell
```

Then ask, for example:

> Open `Invoice.fmp12` with the Admin account. Add a "Loyalty Tier" field to Clients with a value list Bronze / Silver / Gold, and a script "Set Loyalty Tier" that sets it to Gold. Show me the log, then save as `Invoice v2.fmp12`.

## Each agent

The examples below show `"command": "patchwork"`. That is what `init` writes when `patchwork` is on your PATH. If it is not (common on Windows, where pip's Scripts folder often is not), `init` writes the full path of the Python that ran it, with `-m patchwork` in front of the arguments, so the agent starts the right install even from a virtual environment. Run `patchwork init .` again from the Python you want if you change it; delete the four config files first, since `init` never overwrites.

On Windows with a real file, each of the four config files starts the server with its command, arguments and working folder, lists the tools and reads the file's tables. The Claude Code and Codex CLIs read their files as shown below.

### Claude Code

`.mcp.json` at the root of the project:

```json
{
  "mcpServers": {
    "patchwork": {
      "command": "patchwork",
      "args": ["mcp"],
      "env": { "PATCHWORK_PASSWORD": "${PATCHWORK_PASSWORD:-}" }
    }
  }
}
```

Claude Code asks you to approve project servers the first time you run `claude` in the folder. Until then, `claude mcp list` shows it as "Pending approval", which is expected. After that it shows "Connected". You can also add it without a file: `claude mcp add patchwork -- patchwork mcp`.

### Cursor

`.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "patchwork": {
      "command": "patchwork",
      "args": ["-C", "${workspaceFolder}", "mcp"],
      "env": { "PATCHWORK_PASSWORD": "${env:PATCHWORK_PASSWORD}" }
    }
  }
}
```

Enable the server in Cursor Settings > MCP. `-C ${workspaceFolder}` makes sure the working copy is kept in your project, whatever folder Cursor starts the server from.

### Codex

`.codex/config.toml`:

```toml
[mcp_servers.patchwork]
command = "patchwork"
args = ["mcp"]
cwd = "/path/to/my-filemaker-project"
env_vars = ["PATCHWORK_PASSWORD"]
```

Codex loads project configuration only for trusted projects: accept the prompt when Codex first opens the folder, or add it to `~/.codex/config.toml`:

```toml
[projects.'/path/to/my-filemaker-project']
trust_level = "trusted"
```

Until then, `codex mcp list` does not show `patchwork` at all. `env_vars` passes the password through from your shell without writing it anywhere.

### Google Antigravity

`.agents/mcp_config.json`:

```json
{
  "mcpServers": {
    "patchwork": {
      "command": "patchwork",
      "args": ["mcp"],
      "cwd": "/path/to/my-filemaker-project"
    }
  }
}
```

Antigravity reads `AGENTS.md` and the skills in `.agents/skills/`. Start it from a shell where `PATCHWORK_PASSWORD` is set.

The Codex and Antigravity files hold the absolute path of the project. If you move the folder, delete them and run `patchwork init .` again.

## The tools

| Tool | What it does |
|---|---|
| `patchwork_open` | Starts a working copy of a closed file. Never modifies the source |
| `patchwork_status`, `patchwork_log` | Current version, history with diffs |
| `patchwork_list`, `patchwork_show` | Lists objects. Prints a script as FileMaker text, anything else as XML, and a real example of any script step |
| `patchwork_add_field`, `patchwork_add_value_list`, `patchwork_add_custom_function`, `patchwork_add_script` | Creates objects. Scripts are written as text, one step per line |
| `patchwork_set_steps`, `patchwork_append_steps` | Edits a script from its text. Each step is re-read after the change |
| `patchwork_place_field` | Puts a field on a layout below another, with a copy of its look and label |
| `patchwork_uses` | What references an object, and where its name appears in calculations |
| `patchwork_replace`, `patchwork_delete` | Replaces or deletes an object. A delete is refused while other objects reference it, until the agent passes `force` after asking you |
| `patchwork_retheme`, `patchwork_recolor_layouts`, `patchwork_palette` | Colors and fonts |
| `patchwork_push` | Applies a hand-written patch, with the same checks |
| `patchwork_undo`, `patchwork_save` | Drops the last version, writes a new `.fmp12` |

An error comes back as a tool result with `isError`, so the agent can read it and try again. It never stops the server. Parameters, answers and errors of each tool: [MCP tools reference](mcp-tools.md).

## The skills

| Skill | When the agent uses it |
|---|---|
| `patchwork` | Any change to a file: the loop, writing script steps, editing layouts, what is refused and why |
| `fm-standards` | Before creating schema: asks for naming conventions one question at a time and records them |
| `fm-explore` | Mapping an existing solution |
| `fm-data` | Records, through the Data API or OData. Never schema |

## Why it is safe to let an agent do this

- The agent works on a copy. The source file is opened read-only and `save` refuses to overwrite it.
- Every change is a version. "Undo that" always works.
- The agent cannot report a change that did not happen. Patchwork re-reads the file after each patch and refuses a version when FMUpgradeTool skipped it.
- The agent never sees the password. It is an environment variable, printed as `***`.
- Exports and copies stay in `.patchwork/`, which Git ignores.
- Not in release 0.1.0 yet: the six tools that can lose work are marked destructive, `force` is refused outside the project folder unless `PATCHWORK_ALLOW_OUTSIDE=1`, and the agent is told that text read from the file is data, not instructions.
