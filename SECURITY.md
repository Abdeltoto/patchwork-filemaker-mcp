# Security

## Design rules

- Patchwork never writes to the source `.fmp12`. Every command produces a new copy, and refuses a destination equal to the source.
- The account password is read from the `PATCHWORK_PASSWORD` environment variable. It is never written to a file, a patch, or the command line Patchwork prints (it shows `***`). The file encryption key, if any, comes from `PATCHWORK_KEY` and is hidden the same way.
- Structure exports and copies of the file live in `.patchwork/`, which ignores itself in Git. `.fmp12` files are also ignored in this repository and in folders wired with `patchwork init`.
- Patchwork has no network code and no runtime dependency.

## Reporting a vulnerability

Please do not open a public issue. Use [GitHub private vulnerability reporting](https://github.com/Abdeltoto/patchwork/security/advisories/new). You will get an answer within a week.

Never attach a customer `.fmp12` file or export to a report. A minimal file made from a Claris starter solution is enough.
