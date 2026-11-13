# 0002. Work on a versioned copy, never on the source

## Context

A `.fmp12` holds a whole application. FMUpgradeTool writes its result to a new file, and an agent can make mistakes. The user must be able to go back at any time, and the original must stay safe.

## Choice

`patchwork open` creates `.patchwork/` with `v000.fmp12`, a copy of the source with UUIDs. Each change writes `vNNN.fmp12`, its export `vNNN.xml` and the patch `pNNN.xml`. `state.json` lists the versions. `save` writes a new file and `tools.require_copy` refuses the source as destination.

## Consequences

- `undo` deletes the last version's files: no reverse patch is needed.
- Every version is a full copy of the file, so `.patchwork/` grows with the file size times the number of versions.
- `.patchwork/` holds a `.gitignore` with `*`, so exports and copies of a customer file never get committed.
- Patchwork works on closed files on disk, not on hosted ones.
