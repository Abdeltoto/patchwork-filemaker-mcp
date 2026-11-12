"""MCP server over stdio (newline-delimited JSON-RPC 2.0), standard library only.

Works with any MCP client: Claude Code, Claude Desktop, Cursor, Codex, VS Code.
    patchwork mcp [--project DIR]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Callable

from patchwork import PatchworkError, __version__, ops, script
from patchwork.workspace import Workspace

PROTOCOL = "2025-06-18"
INSTRUCTIONS = """Patchwork edits FileMaker (.fmp12) files through Claris FMUpgradeTool, on a versioned working copy.
Start with patchwork_open, then read before you write: patchwork_list and patchwork_show give the real XML of any object.
Every edit creates a new version, is re-exported and checked; a change FMUpgradeTool silently skipped is refused.
Scripts read and write as FileMaker text, one step per line: Set Field [ Clients::Status ; "Gold" ].
Read a script with patchwork_show kind=script, edit the text, send it back with patchwork_set_steps.
Use patchwork_undo to step back, patchwork_save to write the result to a new file. The source file is never modified."""

S = {"type": "string"}
EDIT = {"message": {"type": "string", "description": "What this change does, kept in the version log."},
        "dry_run": {"type": "boolean", "description": "Only write the patch, do not apply it."}}
STEPS = {"type": "string", "description": 'One step per line, as FileMaker shows them: Set Variable [ $n ; Value: 1 ], If [ $n > 0 ], '
         'Show Custom Dialog [ "Title" ; "Message" ; Buttons: "OK", "Cancel" ], End If, # comment. Or <Step> XML.'}
KIND_ENUM = ["layout", "script", "value-list", "custom-function", "theme", "field", "step"]


def tool(name: str, description: str, properties: dict, required: list[str], handler: Callable, needs_ws: bool = True,
         read_only: bool = False, destructive: bool = False) -> dict:
    return {"name": name, "description": description, "handler": handler, "needs_ws": needs_ws,
            "inputSchema": {"type": "object", "properties": properties, "required": required},
            "annotations": {"readOnlyHint": read_only, "destructiveHint": destructive, "idempotentHint": read_only}}


TOOLS = [
    tool("patchwork_open", "Open a closed .fmp12 as a new working copy (v000). Never modifies the source. The password comes from PATCHWORK_PASSWORD.",
         {"source": S, "account": S, "no_password": {"type": "boolean"}, "project": {"type": "string", "description": "Folder for the .patchwork workspace. Default: the source file's folder."},
          "force": {"type": "boolean", "description": "Replace an existing workspace."}},
         ["source", "account"], None, needs_ws=False, destructive=True),
    tool("patchwork_status", "Current version, source file and object counts.", {}, [], lambda ws, a: ops.status(ws), read_only=True),
    tool("patchwork_list", "List objects: layouts, scripts, value-lists, custom-functions, themes, tables, table-occurrences, or fields (with table).",
         {"kind": {"type": "string", "enum": list(ops.LISTABLE)}, "table": S}, [],
         lambda ws, a: ops.list_objects(ws, a.get("kind", ""), a.get("table", "")), read_only=True),
    tool("patchwork_show", "Show one object. A script comes as FileMaker text, one step per line (xml=true for its XML). "
         "Other kinds come as Save-as-XML. kind=field takes Table::Field. kind=step shows the XML of a real step by its name, e.g. 'Set Field'.",
         {"kind": {"type": "string", "enum": KIND_ENUM}, "name": S, "xml": {"type": "boolean"}}, ["kind", "name"],
         lambda ws, a: ops.show(ws, a["kind"], a["name"], bool(a.get("xml"))), read_only=True),
    tool("patchwork_add_field", "Add a field to a table. type: Text, Number, Date, Time, Timestamp, Container. With calc it becomes a calculation.",
         {"table": S, "name": S, "type": {"type": "string", "enum": ["Text", "Number", "Date", "Time", "Timestamp", "Container"]},
          "calc": S, "is_global": {"type": "boolean"}, "comment": S, "context": {"type": "string", "description": "Table occurrence the calculation is evaluated from."}, **EDIT},
         ["table", "name"], lambda ws, a: ops.add_field(ws, **pick(a, "table", "name", "type", "calc", "is_global", "comment", "context", "message", "dry_run"))),
    tool("patchwork_add_value_list", "Add a custom value list.", {"name": S, "values": {"type": "array", "items": S}, **EDIT}, ["name", "values"],
         lambda ws, a: ops.add_value_list(ws, **pick(a, "name", "values", "message", "dry_run"))),
    tool("patchwork_add_custom_function", "Add a custom function.", {"name": S, "calc": S, "params": {"type": "array", "items": S}, **EDIT},
         ["name", "calc"], lambda ws, a: ops.add_custom_function(ws, **pick(a, "name", "calc", "params", "message", "dry_run"))),
    tool("patchwork_add_script", "Create a script. steps: FileMaker script text, one step per line, or <Step> XML. "
         f"Text works for: {', '.join(sorted(script.STEP_IDS))}.",
         {"name": S, "steps": STEPS, **EDIT}, ["name"], lambda ws, a: ops.add_script(ws, **pick(a, "name", "steps", "message", "dry_run"))),
    tool("patchwork_set_steps", "Replace all the steps of a script with the text from patchwork_show, edited. "
         "Lines left as they were keep their step exactly, whatever the step.", {"script": S, "steps": STEPS, **EDIT}, ["script", "steps"],
         lambda ws, a: ops.set_steps(ws, a["script"], **pick(a, "steps", "message", "dry_run"))),
    tool("patchwork_append_steps", "Add steps at the end of a script.", {"script": S, "steps": STEPS, **EDIT}, ["script", "steps"],
         lambda ws, a: ops.append_steps(ws, a["script"], **pick(a, "steps", "message", "dry_run"))),
    tool("patchwork_replace", "Replace a whole object with edited XML from patchwork_show. Supported: layout, theme, value-list, custom-function.",
         {"kind": {"type": "string", "enum": ["layout", "theme", "value-list", "custom-function"]}, "name": S, "xml": S, **EDIT},
         ["kind", "name", "xml"], lambda ws, a: ops.replace(ws, **pick(a, "kind", "name", "xml", "message", "dry_run")), destructive=True),
    tool("patchwork_place_field", "Put a field on a layout. Copies the look and label of `near`, a field already on the layout, "
         "and inserts a row below it (objects underneath move down, the part grows). side=right places it next to `near` if there is room.",
         {"layout": S, "field": {"type": "string", "description": "Occurrence::Field, e.g. Clients::Status"}, "near": S,
          "label": {"type": "string", "description": "Label text. Default: the field name."},
          "side": {"type": "string", "enum": ["below", "right"]}, **EDIT},
         ["layout", "field", "near"], lambda ws, a: ops.place_field(ws, **pick(a, "layout", "field", "near", "label", "side", "message", "dry_run"))),
    tool("patchwork_uses", "What uses an object: references (certain) and mentions by name in calculations (possible). "
         "Call it before deleting or renaming. Kinds: layout, script, value-list, custom-function, table, table-occurrence, field (Table::Field).",
         {"kind": {"type": "string", "enum": ["layout", "script", "value-list", "custom-function", "theme", "table", "table-occurrence", "field"]},
          "name": S}, ["kind", "name"], lambda ws, a: ops.uses(ws, **pick(a, "kind", "name"))),
    tool("patchwork_delete", "Delete an object: script, layout, value-list, custom-function, or field (Table::Field). "
         "Refused when other objects reference it: show the list to the user, and only then retry with force=true.",
         {"kind": {"type": "string", "enum": ["script", "layout", "value-list", "custom-function", "field"]}, "name": S,
          "force": {"type": "boolean"}, **EDIT},
         ["kind", "name"], lambda ws, a: ops.delete(ws, **pick(a, "kind", "name", "message", "dry_run", "force")), destructive=True),
    tool("patchwork_retheme", "Rewrite a theme: colors (map of hex to hex), fonts (map 'WinName,MacName' to 'WinName,MacName'), new display name.",
         {"theme": S, "colors": {"type": "object"}, "fonts": {"type": "object"}, "rename": S, **EDIT}, [],
         lambda ws, a: ops.retheme(ws, **pick(a, "theme", "colors", "fonts", "rename", "message", "dry_run"))),
    tool("patchwork_recolor_layouts", "Rewrite the layouts that change: local colors, fonts, or one field swapped for another everywhere.",
         {"colors": {"type": "object"}, "fonts": {"type": "object"}, "swap_field": {"type": "array", "items": S, "minItems": 2, "maxItems": 2},
          "only": {"type": "array", "items": S}, **EDIT}, [],
         lambda ws, a: ops.recolor_layouts(ws, **pick(a, "colors", "fonts", "swap_field", "only", "message", "dry_run"))),
    tool("patchwork_palette", "Colors a theme uses, most frequent first.", {"theme": S}, [], lambda ws, a: ops.palette(ws, a.get("theme", "")), read_only=True),
    tool("patchwork_push", "Apply a hand-written FMUpgradeToolPatch. Prefer the specific tools.", {"patch_xml": S, **EDIT}, ["patch_xml"],
         lambda ws, a: ops.push(ws, **pick(a, "patch_xml", "message", "dry_run")), destructive=True),
    tool("patchwork_log", "Version history with the changes of each version.", {}, [], lambda ws, a: ops.log(ws), read_only=True),
    tool("patchwork_undo", "Drop the last version.", {}, [], lambda ws, a: ops.undo(ws), destructive=True),
    tool("patchwork_save", "Write the current version to a new .fmp12 file (never the source).", {"dest": S, "force": {"type": "boolean"}}, ["dest"],
         lambda ws, a: ops.save(ws, a["dest"], a.get("force", False)), destructive=True),
]
BY_NAME = {t["name"]: t for t in TOOLS}


def pick(args: dict, *names: str) -> dict:
    return {n: args[n] for n in names if n in args and args[n] is not None}


class Server:
    def __init__(self, project: Path | None = None) -> None:
        self.project = project

    def workspace(self) -> Workspace:
        return Workspace.locate(self.project)

    def call(self, name: str, args: dict) -> str:
        spec = BY_NAME.get(name)
        if not spec:
            raise PatchworkError(f"Unknown tool: {name}")
        if name == "patchwork_open":
            source = Path(args["source"]).expanduser()
            project = args.get("project") or (str(self.project) if self.project else str(source.resolve().parent))
            text = ops.open_file(str(source), args["account"], args.get("no_password", False), project, args.get("force", False))
            self.project = Path(project)
            return text
        return spec["handler"](self.workspace(), args)

    def handle(self, message: dict) -> dict | None:
        method, ident = message.get("method"), message.get("id")
        if ident is None:
            return None
        try:
            if method == "initialize":
                requested = (message.get("params") or {}).get("protocolVersion") or PROTOCOL
                result: Any = {"protocolVersion": requested, "capabilities": {"tools": {"listChanged": False}},
                               "serverInfo": {"name": "patchwork", "version": __version__}, "instructions": INSTRUCTIONS}
            elif method == "ping":
                result = {}
            elif method == "tools/list":
                result = {"tools": [{k: t[k] for k in ("name", "description", "inputSchema", "annotations")} for t in TOOLS]}
            elif method == "tools/call":
                params = message.get("params") or {}
                try:
                    text, error = self.call(params.get("name", ""), params.get("arguments") or {}), False
                except PatchworkError as exc:
                    text, error = str(exc), True
                result = {"content": [{"type": "text", "text": text}], "isError": error}
            else:
                return {"jsonrpc": "2.0", "id": ident, "error": {"code": -32601, "message": f"Method not found: {method}"}}
        except Exception as exc:  # never let one call kill the server
            return {"jsonrpc": "2.0", "id": ident, "error": {"code": -32603, "message": f"{type(exc).__name__}: {exc}"}}
        return {"jsonrpc": "2.0", "id": ident, "result": result}


def serve(project: Path | None = None, stdin=None, stdout=None) -> int:
    stdin = stdin or sys.stdin
    stdout = stdout or sys.stdout
    server = Server(project)
    for line in stdin:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            reply = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}}
        else:
            reply = server.handle(message)
        if reply is not None:
            stdout.write(json.dumps(reply, ensure_ascii=False) + "\n")
            stdout.flush()
    return 0
