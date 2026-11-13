# 0009. Layer rules checked by import-linter

## Context

The modules already fell into layers: interfaces, application, working copy, Claris tools, and the FileMaker logic that does no I/O. Nothing kept it that way. One lazy import from `script` to `place` had crept in.

## Choice

Three import-linter contracts in `pyproject.toml`, run by `lint-imports` in the CI `lint` job. `field_target` moved from `place` to `objects` so that `script` no longer needs `place` (`41a8f79`). See [ARCHITECTURE.md](../../ARCHITECTURE.md).

## Consequences

- A forbidden import fails CI. Each contract was checked by adding a forbidden import.
- import-linter is a CI tool only, pinned to 2.16, not a package dependency.
- A new module must be placed in a contract, or it is not checked.
