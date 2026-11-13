# 0008. Stop a Claris tool that does not answer

## Context

A Claris tool can wait forever, for example on a dialog or a locked file. Through MCP, the agent and the server then wait too, with no message.

## Choice

`tools.Runner.run` passes a timeout to `subprocess.run`: `PATCHWORK_TOOL_TIMEOUT` seconds, default 1800. A value that is not a number above 0 is refused. When the time is up, the tool is stopped and the error says which tool, how long, and which variable to raise.

## Consequences

- No call blocks for more than the limit.
- *To be confirmed:* the default of 1800 seconds was chosen to leave room for large files; no real file was measured close to it. The 11 end-to-end tests on the Invoice solution finish well below it.
- Not in release 0.1.0.
