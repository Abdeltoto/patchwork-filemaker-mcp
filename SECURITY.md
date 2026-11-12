# Security

## Design rules

- Patchwork never writes to the source `.fmp12`. Every command produces a new copy, and refuses a destination equal to the source.
- The account password is read from the `PATCHWORK_PASSWORD` environment variable. It is never written to a file, a patch, or the command line Patchwork prints (it shows `***`). The file encryption key, if any, comes from `PATCHWORK_KEY` and is hidden the same way.

## Known limit: the password reaches the Claris tools as an argument

FMUpgradeTool and FMDeveloperTool only accept the password and the encryption key on their command line. While a command runs, for a few seconds, other users of the same machine can read them in the process list (`ps` on macOS and Linux), and process auditing tools (Windows event 4688, Sysmon, EDR) can record them.

- Give Patchwork its own Full Access account, for example `fmupgrade`, with a password used nowhere else, rather than your main account. Disable it or change its password when you are done.
- Run Patchwork on your own workstation, not on a server shared with other users.
- If your security team records process command lines, tell them, or exclude these two tools.
- Structure exports and copies of the file live in `.patchwork/`, which ignores itself in Git. `.fmp12` files are also ignored in this repository and in folders wired with `patchwork init`.
- Patchwork has no network code and no runtime dependency.

## Reporting a vulnerability

Please do not open a public issue. Use [GitHub private vulnerability reporting](https://github.com/Abdeltoto/patchwork-filemaker-mcp/security/advisories/new). You will get an answer within a week.

Never attach a customer `.fmp12` file or export to a report. A minimal file made from a Claris starter solution is enough.
