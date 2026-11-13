# MCP tools reference

`patchwork mcp` is an MCP server over stdio. It is the only API Patchwork exposes: there is no HTTP endpoint. This page lists its 21 tools as defined in [`src/patchwork/mcp.py`](../src/patchwork/mcp.py). The parameter tables were generated from that file. The example outputs come from a real session on the Claris Invoice solution.

## Protocol

- Transport: one JSON-RPC 2.0 message per line on stdin, one reply per line on stdout.
- Methods: `initialize`, `ping`, `tools/list`, `tools/call`. Any other method gets error `-32601`.
- A message without `id` (a notification such as `notifications/initialized`) gets no reply.
- `initialize` answers with the protocol version the client asked for (default `2025-06-18`), `serverInfo` `{"name": "patchwork", "version": ...}` and `instructions` for the agent.

Start it by hand to try it:

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | patchwork -C . mcp
```

## Responses

Every tool answers with plain text, in a `tools/call` result:

```json
{"jsonrpc": "2.0", "id": 6, "result": {"content": [{"type": "text", "text": "v001  loyalty\n  + field Clients::Loyalty Tier"}], "isError": false}}
```

An editing tool answers with the new version, its message and what changed (at most 40 lines, then `... and N more`):

```
v001  loyalty
  + field Clients::Loyalty Tier
```

`+` added, `~` changed, `-` deleted. A line starting with `!` warns about new steps that act outside the file: Send Event, Perform AppleScript, Perform JavaScript in Web Viewer, Insert from URL, Open URL, Send Mail, Install Plug-In File (`objects.OUTSIDE_STEPS`). Not in release 0.1.0.

```
! 1 new Insert from URL step(s): they run when the file is used, check them before opening it
```

With `dry_run: true`, nothing is applied:

```
Dry run: patch written to C:\...\.patchwork\p002.xml
```

## Errors

| Case | What comes back |
|---|---|
| A problem the user can fix (object not found, delete refused, path refused, FMUpgradeTool skipped the patch) | A normal result with `"isError": true` and the message as text. The server keeps running. |
| Unknown tool | `isError: true`, text `Unknown tool: NAME`. |
| A required argument is missing | JSON-RPC error `-32603`, for example `KeyError: 'kind'`. The arguments are not validated against the schema. |
| Unknown method | JSON-RPC error `-32601`, `Method not found: resources/list`. |
| A line that is not JSON | JSON-RPC error `-32700`, `Parse error`, with `id: null`. |

Examples from the real session:

```
script not found: Nope
```

```
Refused to replace C:\Windows\Temp\x.fmp12: it is outside the project folder C:\...\pw-mcp-session. Ask the user, or set PATCHWORK_ALLOW_OUTSIDE=1.
```

Every editing tool can also answer with one of these, and then no version is recorded:

- `FMUpgradeTool reported success but the file did not change: this patch was skipped. ...` (the patch is kept in `.patchwork/`);
- `FMUpgradeTool reported success but `+ field ...` is missing from the result. Version dropped.`;
- `FMUpgradeTool applied the patch but ... Version dropped.` (a value, formula, parameter or step that FileMaker lost);
- `FMUpgradeTool did not finish within N s and was stopped. ...` (see `PATCHWORK_TOOL_TIMEOUT`, not in release 0.1.0).

## Project folder and paths

- Every tool except `patchwork_open` works on the workspace of the project folder. That folder is, in order: the folder of the last `patchwork_open`, `-C DIR` given to `patchwork mcp`, `PATCHWORK_PROJECT`, then the nearest `.patchwork/` from the current folder upward.
- `patchwork_save` with `force: true`, and `patchwork_open` with `force: true`, are refused outside the project folder unless `PATCHWORK_ALLOW_OUTSIDE=1`. Not in release 0.1.0.

## Annotations

`tools/list` gives each tool `readOnlyHint`, `destructiveHint` and `idempotentHint`. Six tools are marked destructive: `patchwork_open`, `patchwork_replace`, `patchwork_delete`, `patchwork_push`, `patchwork_undo`, `patchwork_save`. In release 0.1.0 every tool says `destructiveHint: false`.

## Common editing parameters

Every tool that creates a version also takes:

| Parameter | Type | Notes |
|---|---|---|
| `message` | string | Kept in the version log. Default: a description such as `add field Clients::Status`. |
| `dry_run` | boolean | Only write the patch to `.patchwork/`, do not apply it. |

They are not repeated below.

---

## Working copy

### `patchwork_open`

Opens a closed `.fmp12` as a new working copy (v000). Never modifies the source. The password comes from `PATCHWORK_PASSWORD`. Destructive: with `force` it replaces an existing workspace.

| Parameter | Type | Required | Notes |
|---|---|:-:|---|
| `source` | string | yes | Path of the `.fmp12`. |
| `account` | string | yes | A Full Access account. |
| `no_password` | boolean | | The account has no password. |
| `project` | string | | Folder for `.patchwork/`. Default: the server's project folder, else the source file's folder. |
| `force` | boolean | | Replace an existing workspace. |

```json
{"name": "patchwork_open", "arguments": {"source": "Invoice.fmp12", "account": "Admin", "no_password": true}}
```

```
Opened Invoice.fmp12 as v000 in C:\...\pw-mcp-session\.patchwork
source   C:\...\pw-mcp-session\Invoice.fmp12
version  v000  (open Invoice.fmp12, 2026-11-12 22:39:27)
account  Admin
contents 6 tables, 24 layouts, 61 scripts, 12 value-lists, 3 custom-functions
```

Errors: `Set PATCHWORK_PASSWORD in your shell, or pass --no-password ...`, `Source file not found: ...`, `A workspace already exists here for X.fmp12. ...`, a Claris tool failure (`... Is the file open in FileMaker? Close it (error 803).`).

### `patchwork_status`

Current version, source file and object counts. Read-only. No parameters. The output is the same block as the end of `patchwork_open`.

### `patchwork_log`

Every version with its time, message and up to 10 changes. Read-only. No parameters.

```
v000  2026-11-12 22:39:27  open Invoice.fmp12
v001  2026-11-12 22:39:35  loyalty
        + field Clients::Loyalty Tier
v002  2026-11-12 22:39:41  add script Say Hello
        + script Say Hello
```

### `patchwork_undo`

Drops the last version and its files. Destructive. No parameters.

```
Back to v001
```

Error on v000: `Nothing to undo: this is the opened file.`

### `patchwork_save`

Writes the current version to a new `.fmp12`. Never the source. Destructive.

| Parameter | Type | Required | Notes |
|---|---|:-:|---|
| `dest` | string | yes | Must end in `.fmp12` and differ from the source. |
| `force` | boolean | | Replace an existing file. Inside the project folder only. |

```
Saved v001 to C:\...\pw-mcp-session\Invoice v2.fmp12
```

Errors: `The destination is the source file. Patchwork always writes a copy.`, `... already exists. Pass --force to replace it.`, `Refused to replace ...: it is outside the project folder ...`.

## Reading

### `patchwork_list`

Lists object names, one per line. Read-only.

| Parameter | Type | Required | Notes |
|---|---|:-:|---|
| `kind` | string | | One of `layouts`, `scripts`, `value-lists`, `custom-functions`, `themes`, `tables`, `table-occurrences`, `fields`. Empty: a count per kind. |
| `table` | string | | Required with `kind: fields`. Each field comes as `name<TAB>type`, with ` (calc)` for a calculation. |

```json
{"name": "patchwork_list", "arguments": {"kind": "value-lists"}}
```

```
United States
Industries
...
```

### `patchwork_show`

One object. A script comes as FileMaker text, one step per line. Any other kind comes as its Save-as-XML block. Read-only.

| Parameter | Type | Required | Notes |
|---|---|:-:|---|
| `kind` | string | yes | One of `layout`, `script`, `value-list`, `custom-function`, `theme`, `field`, `step`. `field` takes `Table::Field`. `step` gives the XML of a real step of that name found in the file, such as `Set Field`. |
| `name` | string | yes | |
| `xml` | boolean | | A script as XML instead of text. |

```json
{"name": "patchwork_show", "arguments": {"kind": "script", "name": "Close Window"}}
```

```
# ========================================
# 	Purpose:
# 		Closes the current window
...
Close Window [ Current Window ]
```

Errors: `script not found: NAME`, `No script in this file uses the step 'NAME'. Look at another file for an example.`

### `patchwork_uses`

What references an object (certain) and where its name appears in calculations (possible). Call it before a delete or a rename. Not marked read-only, although it changes nothing.

| Parameter | Type | Required | Notes |
|---|---|:-:|---|
| `kind` | string | yes | One of `layout`, `script`, `value-list`, `custom-function`, `theme`, `table`, `table-occurrence`, `field`. |
| `name` | string | yes | `Table::Field` for a field. |

```
layout Dev Invoices is referenced by 3 object(s):
  script Delete ALL Records  (1x)
  script Load Dashboard  (1x)
  script Set Dates  (1x)
```

### `patchwork_palette`

Colors of a theme, most frequent first. Read-only.

| Parameter | Type | Required | Notes |
|---|---|:-:|---|
| `theme` | string | | Display or internal name. Default: the theme most layouts use. |

```
Apex Blue
FFFFFF  582x
E6E6E6  193x
0091CE  169x
...
```

## Creating

### `patchwork_add_field`

Adds a field to a table. The version is dropped if the field is missing from the re-export.

| Parameter | Type | Required | Notes |
|---|---|:-:|---|
| `table` | string | yes | Base table name. |
| `name` | string | yes | |
| `type` | string | | `Text` (default), `Number`, `Date`, `Time`, `Timestamp`, `Container`. |
| `calc` | string | | A formula: the field becomes a calculation. |
| `is_global` | boolean | | Global storage. |
| `comment` | string | | |
| `context` | string | | Table occurrence the calculation is evaluated from. |

The CLI's `--image` option has no MCP equivalent.

```json
{"name": "patchwork_add_field", "arguments": {"table": "Clients", "name": "Loyalty Tier", "message": "loyalty"}}
```

```
v001  loyalty
  + field Clients::Loyalty Tier
```

### `patchwork_add_value_list`

Adds a custom value list. The version is dropped if FileMaker stored other values.

| Parameter | Type | Required | Notes |
|---|---|:-:|---|
| `name` | string | yes | |
| `values` | array of string | yes | |

### `patchwork_add_custom_function`

Adds a custom function. The version is dropped if the formula or the parameters are missing from the result.

| Parameter | Type | Required | Notes |
|---|---|:-:|---|
| `name` | string | yes | |
| `calc` | string | yes | The formula. |
| `params` | array of string | | Parameter names. |

### `patchwork_add_script`

Creates a script. Each step is re-read after the change, and the version is dropped if one came back different.

| Parameter | Type | Required | Notes |
|---|---|:-:|---|
| `name` | string | yes | |
| `steps` | string | | FileMaker script text, one step per line, or `<Step>` XML. Empty: a script with no steps. |

Text is understood for these 25 steps: `# (comment)`, Allow User Abort, Beep, Close Window, Commit Records/Requests, Delete Record/Request, Else, Else If, End If, End Loop, Exit Loop If, Exit Script, Freeze Window, Go to Layout, Halt Script, If, Loop, New Record/Request, Perform Script, Refresh Window, Set Error Capture, Set Field, Set Variable, Show All Records, Show Custom Dialog. For any other step, use `patchwork_show kind=step` and send `<Step>` XML.

```json
{"name": "patchwork_add_script", "arguments": {"name": "Say Hello", "steps": "Show Custom Dialog [ \"Hello\" ; \"Hi\" ]"}}
```

```
v002  add script Say Hello
  + script Say Hello
```

## Editing

### `patchwork_set_steps`

Replaces all the steps of a script with the text from `patchwork_show`, edited. Lines left as they were keep their exact step, whatever the step.

| Parameter | Type | Required | Notes |
|---|---|:-:|---|
| `script` | string | yes | Script name. |
| `steps` | string | yes | Script text or `<Step>` XML. |

### `patchwork_append_steps`

Adds steps at the end of a script. Same parameters as `patchwork_set_steps`.

### `patchwork_place_field`

Puts a field on a layout. It copies the look and label of `near`, a field already on the layout, and inserts a row below it: objects underneath move down and the part grows.

| Parameter | Type | Required | Notes |
|---|---|:-:|---|
| `layout` | string | yes | |
| `field` | string | yes | `Occurrence::Field`, such as `Clients::Status`. |
| `near` | string | yes | A field already on the layout. |
| `label` | string | | Default: the field name. |
| `side` | string | | `below` (default) or `right` (next to `near`, if there is room). |

### `patchwork_replace`

Replaces a whole object with edited XML from `patchwork_show`. Destructive.

| Parameter | Type | Required | Notes |
|---|---|:-:|---|
| `kind` | string | yes | `layout`, `theme`, `value-list` or `custom-function`. |
| `name` | string | yes | |
| `xml` | string | yes | The whole object. For a layout, the whole `<Layout>` block: FMUpgradeTool skips a lone layout object. |

### `patchwork_retheme`

Rewrites a theme.

| Parameter | Type | Required | Notes |
|---|---|:-:|---|
| `theme` | string | | Default: the theme most layouts use. |
| `colors` | object | | Old hex to new hex, such as `{"0091CE": "2F5D50"}`. |
| `fonts` | object | | `"WinName,MacName"` to `"WinName,MacName"`. |
| `rename` | string | | New display name. |

### `patchwork_recolor_layouts`

Rewrites the layouts that change: local colors, fonts, or one field swapped for another everywhere. Error `No layout would change.` when nothing matches.

| Parameter | Type | Required | Notes |
|---|---|:-:|---|
| `colors` | object | | Same format as `patchwork_retheme`. |
| `fonts` | object | | Same format as `patchwork_retheme`. |
| `swap_field` | array of 2 strings | | `["Table::Old", "Table::New"]`. |
| `only` | array of string | | Layout names. Default: every layout. |

### `patchwork_push`

Applies a hand-written patch, with the same checks. Prefer the specific tools. Destructive.

| Parameter | Type | Required | Notes |
|---|---|:-:|---|
| `patch_xml` | string | yes | A full patch, root `<FMUpgradeToolPatch>`. |

## Deleting

### `patchwork_delete`

Deletes a script, layout, value list, custom function or field. Refused while other objects reference it: show the list to the user, then retry with `force: true`. Destructive.

| Parameter | Type | Required | Notes |
|---|---|:-:|---|
| `kind` | string | yes | `script`, `layout`, `value-list`, `custom-function` or `field`. |
| `name` | string | yes | `Table::Field` for a field. |
| `force` | boolean | | Delete even if referenced. |

```json
{"name": "patchwork_delete", "arguments": {"kind": "layout", "name": "Dev Invoices"}}
```

```
layout Dev Invoices is referenced by 3 object(s):
  script Delete ALL Records  (1x)
  script Load Dashboard  (1x)
  script Set Dates  (1x)
Not deleted: these would point at nothing. Check them first, then delete with --force (MCP: force=true). `undo` brings it back either way.
```

This comes back with `isError: true`. With `force: true`, the result ends with `Warning, review these: ...`.
