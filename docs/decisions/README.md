# Decisions

One short note per important technical choice: context, choice, consequences. "In place since" gives the commit where the choice can first be seen in the code. The reasoning at the time was not written down for the oldest ones: what is said about it comes from the code and the docs, and anything else is marked *to be confirmed*.

| # | Decision | In place since |
|---|---|---|
| [0001](0001-standard-library-only.md) | Standard library only at runtime | `e6f7c03` |
| [0002](0002-versioned-working-copy.md) | Work on a versioned copy, never on the source | `e6f7c03` |
| [0003](0003-verify-by-re-export.md) | Re-export and compare after every patch | `e6f7c03` |
| [0004](0004-scripts-as-text.md) | Scripts read and written as FileMaker text | `e6f7c03` |
| [0005](0005-password-from-environment.md) | Password from an environment variable only | `e6f7c03` |
| [0006](0006-claris-tool-lookup.md) | Never run a Claris tool found in the current folder | `e0c7247` |
| [0007](0007-mcp-guard-rails.md) | MCP: errors as results, destructive hints, project folder limit | `e6f7c03`, `a55ad94`, `705c7a0` |
| [0008](0008-tool-timeout.md) | Stop a Claris tool that does not answer | `727826c` |
| [0009](0009-layer-contracts.md) | Layer rules checked by import-linter | `13beab7` |

To add one: copy the shape of an existing note, take the next number, and add a line here.
