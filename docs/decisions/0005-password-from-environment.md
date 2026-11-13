# 0005. Password from an environment variable only

## Context

The Claris tools need a Full Access account and its password. An agent reads every file in the project, and MCP configuration files are often committed.

## Choice

`tools.password` reads `PATCHWORK_PASSWORD` only, or nothing with `--no-password`. There is no option to pass it on the command line or in a file. The encryption key comes from `PATCHWORK_KEY`. What Patchwork prints shows `***` instead of either.

## Consequences

- The MCP configurations written by `init` pass the variable through from the shell (`${env:PATCHWORK_PASSWORD}`, `env_vars = [...]`) and never contain it.
- The Claris tools accept the password only as a command-line argument, so it is visible in the process list while a tool runs. SECURITY.md documents this limit and recommends a dedicated account.
- The account name is stored in `state.json`, the password never is.
