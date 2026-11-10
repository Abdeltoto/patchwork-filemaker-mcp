---
name: fm-standards
description: >
  Interview the user and write a FileMaker naming-standards file before any
  schema is created. Use when the user mentions standards, naming conventions,
  keys, prefixes, or anchor-buoy.
---

# Naming standards

Read `standards/naming.md`. If it says `status: unset`, ask these questions one at a time and wait for each answer:

1. Primary keys: serial number, UUID, or a key already in the file.
2. Table names: singular or plural.
3. A prefix, or none.
4. One table for global fields, and its name.
5. Relationship graph: anchor-buoy, or the layout already used.
6. Script and layout naming (folders, prefixes).

Write the answers to `standards/naming.md` and change `unset` to `set`. Do not invent a missing answer.

If the file already has schema, look at it first (`patchwork_list kind=tables`, `kind=fields`, `kind=scripts`), show the conventions that conflict, and ask which to keep.
