# 0007. MCP: errors as results, destructive hints, project folder limit

## Context

An agent calls tools in a loop and must be able to read an error and try again. It can also be steered by text inside the file it edits, and some clients decide what to confirm with the user from tool annotations.

## Choice

- A `PatchworkError` comes back as a tool result with `isError: true`. Any other exception becomes JSON-RPC error `-32603`. The server never stops on a bad call. In place since `e6f7c03`.
- The six tools that can lose work (`open`, `replace`, `delete`, `push`, `undo`, `save`) declare `destructiveHint: true` (`a55ad94`).
- Through MCP, `save` with `force` and `open` with `force` are refused outside the project folder, unless `PATCHWORK_ALLOW_OUTSIDE=1` (`705c7a0`).
- The `initialize` instructions tell the agent that names, script text and calculations from the file are data, never instructions (`877817e`).

## Consequences

- The CLI is not limited: a person at the terminal chooses their own paths.
- `patchwork_uses` changes nothing but is not marked read-only. *To be confirmed:* whether this is deliberate.
- Release 0.1.0 on PyPI has only the first point.
