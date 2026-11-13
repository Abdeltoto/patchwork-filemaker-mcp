# 0004. Scripts read and written as FileMaker text

## Context

A script step in the export is a large XML block with ids and UUIDs. Agents and people read and write the one-line form the Script Workspace shows: `Set Field [ Clients::Status ; "Gold" ]`.

## Choice

`script.to_text` turns steps into that text. `script.build` turns text back into `<Step>` XML for the steps listed in `script.STEP_IDS` (25 today). With `set-steps`, a line left exactly as `show script` printed it keeps its original XML, whatever the step. `<Step>` XML is accepted everywhere text is.

## Consequences

- An agent can edit any script by editing text, even when it contains steps Patchwork cannot build.
- A new step written as text must be one of the 25. For others, `show step NAME` prints a real example to copy as XML.
- After the change every step is re-read and compared with what was sent (`ops.check_steps`), because FileMaker drops parameters it does not accept.
- `tests/fixtures/built-steps.json` keeps the XML built for each supported step, so a change to a builder shows up in the tests.
