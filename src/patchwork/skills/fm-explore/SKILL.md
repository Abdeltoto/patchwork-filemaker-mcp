---
name: fm-explore
description: >
  Map and document an existing FileMaker solution: tables, fields, layouts,
  scripts, value lists, relationships. Use when the user asks to explore,
  understand, document, or audit a FileMaker file.
---

# Explore a solution

1. `patchwork_open` the file (or reuse the open workspace), then `patchwork_status` and `patchwork_list` with no kind for the counts.
2. List each kind: `patchwork_list kind=tables`, then `kind=fields table=...` per table, `kind=layouts`, `kind=scripts`, `kind=value-lists`, `kind=custom-functions`.
3. Open what matters with `patchwork_show` before describing it. Read a whole script before saying what it does. Do not claim behavior the XML does not show.
4. The full export is `.patchwork/vNNN.xml` (the highest number is current). For relationships read its `<RelationshipCatalog>`; for privileges `<PrivilegeSetsCatalog>`.

Write the map to `docs/map.md`: tables and key fields, entry-point scripts (startup, buttons, triggers), script-to-layout navigation, value lists, open questions. Never copy record data.
