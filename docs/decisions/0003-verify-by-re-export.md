# 0003. Re-export and compare after every patch

## Context

FMUpgradeTool prints success even when it skips a patch, or when it drops part of it, such as a formula it cannot parse. The field guide lists the cases found so far. An agent that trusts the tool reports changes that never happened.

## Choice

After every patch, `Workspace.apply` exports the new version and compares it with the previous export, once the parts that change on every save are removed (`objects.normalize`). Then `ops.run` checks that the expected line, such as `+ field Clients::Status`, is in the diff, and runs a content check when there is one: the values of a value list, the formula and parameters of a custom function, each step of a script, the field on the layout.

## Consequences

- A skipped or partial patch is refused and no version is recorded. The patch file stays in `.patchwork/` for inspection.
- Each change costs one more `FMDeveloperTool --saveAsXML`. *To be confirmed:* its duration on large files; it was not measured.
- The diff also shows side effects, such as a script that pointed at a deleted layout.
