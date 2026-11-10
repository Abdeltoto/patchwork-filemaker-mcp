# {{NAME}}

This is a FileMaker project. You edit the FileMaker file with [Patchwork](https://github.com/Abdeltoto/patchwork-filemaker-mcp), through its MCP tools (`patchwork_*`) or the `patchwork` command. Never drive the FileMaker window to change schema.

## How to work

1. `patchwork_open` (or `patchwork open file.fmp12 --account NAME`) once. It makes a working copy in `.patchwork/`; the original file is never modified.
2. **Read before you write.** `patchwork_list` and `patchwork_show` show any object. Scripts come as FileMaker text, one step per line (`Set Field [ Clients::Status ; "Gold" ]`): edit the text and send it back with `patchwork_set_steps`. Everything else comes as XML.
3. Make one change per call, with a clear `message`. Each change becomes a version, is re-exported and checked. If Patchwork says the change was skipped, read the message and try another way: do not repeat the same call.
4. `patchwork_log` shows what changed, `patchwork_undo` steps back.
5. When the user is happy, `patchwork_save` writes the result to a **new** file. Tell the user to open it in FileMaker to check the screens.

## What you can change

| Object | Add | Edit | Delete |
|---|---|---|---|
| Field | `add_field` (text, number, date, container, calculation, global) | | `delete kind=field` |
| Script | `add_script` with steps as text | `set_steps`, `append_steps` | `delete` |
| Value list | `add_value_list` | `replace` | `delete` |
| Custom function | `add_custom_function` | `replace` | `delete` |
| Layout | `place_field` puts a field on it | `replace` (whole layout), `recolor_layouts` | `delete` |
| Theme | | `retheme`, `replace` | |

## Rules

- Never ask for the password and never write it anywhere. It lives in the `PATCHWORK_PASSWORD` environment variable.
- Before deleting or renaming anything, run `patchwork_uses`, tell the user what uses it, and wait for their go-ahead. Only then retry a refused delete with `force=true`.
- If a call fails with error 803, the file is open in FileMaker: ask the user to close it.
- Read `standards/naming.md` before creating schema. If it says `status: unset`, ask for the standards first.
- Never paste record data from the file into the conversation.
