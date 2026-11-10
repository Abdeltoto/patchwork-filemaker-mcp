---
name: patchwork
description: >
  Edit a FileMaker (.fmp12) file directly: add or change fields, scripts and
  script steps, value lists, custom functions, layouts and themes, through
  Patchwork and Claris FMUpgradeTool, on a versioned working copy. Use when the
  user asks to change, build, fix or explore a FileMaker solution.
---

# Edit FileMaker with Patchwork

Use the `patchwork_*` MCP tools when they are available, otherwise the `patchwork` command (same names: `patchwork_add_field` is `patchwork add-field`). Never drive the FileMaker window to change schema.

## The loop

1. **Open once.** `patchwork_open source=... account=...` (CLI: `patchwork open app.fmp12 --account Admin`). This creates a working copy, v000. The source file is never written.
2. **Read.** `patchwork_list kind=scripts`, `patchwork_show kind=script name="..."`. Read the object you are about to change, and one similar to what you are about to create.
3. **Change, one thing at a time,** with a `message`. Each call creates a version, re-exports the file, and lists what changed (`+` added, `~` modified, `-` deleted).
4. **Check** the change list. If it is not what you meant, `patchwork_undo`.
5. **Save** with `patchwork_save dest=...` to a new file, and ask the user to open it in FileMaker.

## Writing scripts

Scripts are text, one step per line, as the Script Workspace shows them. Indentation is optional.

```
# Mark the client as Gold
Set Variable [ $count ; Value: Get ( FoundCount ) ]
If [ $count = 0 ]
    Show Custom Dialog [ "Nothing to do" ; "No client found." ; Buttons: "OK" ]
    Exit Script [ Text Result: False ]
End If
Set Field [ Clients::Status ; "Gold" ]
Commit Records/Requests [ With dialog: Off ]
Perform Script [ "Sort Clients" ; Parameter: "gold" ]
```

- **To edit a script:** `patchwork_show kind=script name=...`, change the lines you need, send the whole text to `patchwork_set_steps`. Lines you did not touch keep their exact step, whatever the step.
- **New lines** work for: `# comment`, Set Field, Set Variable, If, Else If, Else, End If, Loop, Exit Loop If, End Loop, Go to Layout, Perform Script, Show Custom Dialog, Exit Script, Commit Records/Requests, Delete Record/Request, Set Error Capture, Allow User Abort, Refresh Window, Close Window, Freeze Window, New Record/Request, Show All Records, Halt Script, Beep.
- Fields are `Occurrence::Field`, scripts and layouts are quoted names. Start a line with `//` to disable the step. In a comment, `¶` is a new line.
- **Another step** (Perform Find, Sort Records, New Window…): copy a line for it from another script of the file if one exists. Otherwise use XML: `patchwork_show kind=step name="Sort Records"` prints a real one, and the steps parameter also takes `<Step>` elements.

After every script change, Patchwork re-reads each step. If FileMaker dropped a parameter, the version is refused and the message names the step.

## Putting a field on a layout

`patchwork_place_field layout="Clients Details" field="Clients::Status" near="Contact Email"` copies the look and the label of the `near` field and inserts a row below it: what is underneath moves down and the part grows. `side=right` puts it next to `near` instead, if there is room. Add the field first with `patchwork_add_field` if it does not exist.

## Editing a layout

For anything else, `patchwork_show kind=layout name=...` gives the whole layout. Edit it (bounds, text, styles, objects), then `patchwork_replace kind=layout` with the **whole** `<Layout>` element. FMUpgradeTool skips a lone layout-object replace. `<Bounds>` are absolute, from the top of the layout. Anchoring is in each object's `<Options>`.

## Deleting or renaming

1. `patchwork_uses kind=... name=...` first. References are certain. Mentions are a name found in calculation text, so check them.
2. Tell the user what uses the object, and ask before going on.
3. `patchwork_delete` refuses while references exist. Retry with `force=true` only after the user agreed. Then fix or report each script, layout or calculation from the list.

## When a change is refused

- "the file did not change: this patch was skipped": FMUpgradeTool ignored it. Do not retry the same call. Check the XML against a real object from `patchwork_show`, or choose another way (for example replace the whole layout).
- "Not deleted: these would point at nothing": other objects use it. See "Deleting or renaming".
- Error 803: the file is open in FileMaker. Ask the user to close it.
- A password error: `PATCHWORK_PASSWORD` is missing or wrong. Ask the user to set it in their environment. Never ask for the password in the chat.

Full list of verified behaviors: https://github.com/Abdeltoto/patchwork-filemaker-mcp/blob/main/docs/fmupgradetool-field-guide.md
