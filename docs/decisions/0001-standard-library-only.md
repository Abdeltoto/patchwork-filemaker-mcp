# 0001. Standard library only at runtime

## Context

Patchwork runs on the machine of a FileMaker developer, often on Windows, and is started by AI agents through `uvx` or a plain `pip install`. Every dependency is one more thing to install, to audit and to break.

## Choice

`dependencies = []` in `pyproject.toml`. The MCP server, the XML handling and the CLI use only the standard library. Pillow is the optional `image` extra, imported inside `build.image_calc` only when an image must be resized.

## Consequences

- `pip install filemaker-patchwork` installs nothing else.
- The MCP server is written by hand in `mcp.py` (JSON-RPC over stdio), without an MCP SDK. Its schemas are not validated: a missing required argument gives a JSON-RPC error `-32603`.
- The export XML is read with regular expressions, not an XML parser. *To be confirmed:* whether this was chosen to keep the exact text of each block (useful to build replace patches) or only to avoid a dependency.
- Development tools (ruff, mypy, coverage, import-linter, pip-audit, bandit) are installed in CI only, with pinned versions.
- CONTRIBUTING.md keeps the rule: "Standard library only at runtime. Pillow stays optional."
