"""Every workspace operation, shared by the CLI and the MCP server. Each returns plain text."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Callable

from patchwork import PatchworkError, objects, place, script
from patchwork.build import (
    FIELD_TYPES,
    add_field_action,
    field_xml,
    image_calc,
    layouts_patch,
    palette as theme_palette,
    theme_replace,
)
from patchwork.export import Export, unescape
from patchwork.uses import find_uses
from patchwork.workspace import Result, Workspace

LISTABLE = ("layouts", "scripts", "value-lists", "custom-functions", "themes", "tables", "table-occurrences", "fields")


def open_file(
    source: str, account: str, no_password: bool = False, project: str | None = None, force: bool = False
) -> str:
    ws = Workspace.create(Path(source), account, no_password, Path(project) if project else None, force)
    return f"Opened {Path(source).name} as v000 in {ws.root}\n" + status(ws)


def status(ws: Workspace) -> str:
    export = ws.export
    counts = ", ".join(
        f"{len(objects.items(export, k))} {k}" for k in ("layouts", "scripts", "value-lists", "custom-functions")
    )
    tables = objects.items(export, "tables")
    last = ws.log()[-1]
    return (
        f"source   {ws.state['source']}\n"
        f"version  v{ws.version:03d}  ({last['message']}, {last['time']})\n"
        f"account  {ws.state['account']}\n"
        f"contents {len(tables)} tables, {counts}"
    )


def list_objects(ws: Workspace, kind: str = "", table: str = "") -> str:
    export = ws.export
    if kind in ("", "all"):
        return (
            "\n".join(f"{k}: {len(objects.items(export, k))}" for k in LISTABLE if k != "fields")
            + "\nfields: use `ls fields TABLE`"
        )
    if kind in ("fields", "field"):
        if not table:
            raise PatchworkError("Name the table: ls fields TABLE")
        _, _, catalog = export.field_catalog(table)
        rows = re.findall(r'<Field id="\d+" name="([^"]*)" fieldtype="([^"]*)" datatype="([^"]*)"', catalog)
        label = {"Binary": "Container", "TimeStamp": "Timestamp"}
        return "\n".join(
            f"{unescape(name)}\t{label.get(datatype, datatype)}{' (calc)' if ftype == 'Calculated' else ''}"
            for name, ftype, datatype in rows
        )
    return "\n".join(item.name for item in objects.items(export, kind))


def show(ws: Workspace, kind: str, name: str, xml: bool = False) -> str:
    if kind == "script" and not xml:
        return script.to_text(objects.script_steps(ws.export, name)[1]) or f"{name} has no steps."
    return objects.show(ws.export, kind, name)


def describe(result: Result) -> str:
    lines = [f"v{result.version:03d}  {result.message}"] + [f"  {c}" for c in result.changes[:40]]
    if len(result.changes) > 40:
        lines.append(f"  ... and {len(result.changes) - 40} more")
    return "\n".join(lines)


def run(
    ws: Workspace,
    actions,
    message: str,
    dry_run: bool,
    expect: str | None = None,
    check: Callable[[Export], str | None] | None = None,
) -> str:
    result = ws.apply(actions, message, dry_run=dry_run)
    if dry_run:
        return f"Dry run: patch written to {result.patch}"
    if expect and not any(c.startswith(expect) for c in result.changes):
        ws.undo()
        raise PatchworkError(
            f"FMUpgradeTool reported success but `{expect}` is missing from the result. Version dropped."
        )
    problem = check(ws.export) if check else None
    if problem:
        ws.undo()
        raise PatchworkError(f"FMUpgradeTool applied the patch but {problem}. Version dropped.")
    return describe(result)


def lines(text: str) -> list[str]:
    return re.split(r"\r\n|\r|\n", text)


def check_value_list(name: str, values: list[str]) -> Callable[[Export], str | None]:
    def check(export: Export) -> str | None:
        found = re.search(
            r"<CustomValues>\s*<Text><!\[CDATA\[([\s\S]*?)\]\]>", objects.find(export, "value-list", name).xml
        )
        stored = lines(found.group(1)) if found else []
        return None if stored == values else f"the value list holds {stored} instead of {values}"

    return check


def check_custom_function(name: str, calc: str, params: list[str]) -> Callable[[Export], str | None]:
    def check(export: Export) -> str | None:
        xml = objects.find(export, "custom-function", name).xml
        found = re.search(r"<Calculation>\s*<Text><!\[CDATA\[([\s\S]*?)\]\]>", xml)
        if not found or lines(found.group(1)) != lines(calc):
            return "the formula is missing from the result (FileMaker rejected the calculation)"
        stored = [unescape(p) for p in re.findall(r'<Parameter name="([^"]*)"', xml)]
        return None if stored == params else f"the parameters are {stored} instead of {params}"

    return check


def add_field(
    ws: Workspace,
    table: str,
    name: str,
    type: str = "Text",
    calc: str = "",
    is_global: bool = False,
    comment: str = "",
    context: str = "",
    image: str = "",
    image_width: int = 0,
    message: str = "",
    dry_run: bool = False,
) -> str:
    if type not in FIELD_TYPES:
        raise PatchworkError(f"Unknown field type: {type}. Choose from {', '.join(FIELD_TYPES)}.")
    if image:
        calc, type, is_global = image_calc(Path(image), image_width or None), "Container", True
    xml = field_xml(ws.export, table, name, type, comment, is_global, calc or None, context or None)
    return run(
        ws,
        add_field_action(ws.export, table, xml),
        message or f"add field {table}::{name}",
        dry_run,
        f"+ field {table}::{name}",
    )


def add_value_list(ws: Workspace, name: str, values: list[str], message: str = "", dry_run: bool = False) -> str:
    action = objects.add_object(ws.export, "value-list", objects.value_list_xml(name, values))
    return run(
        ws, action, message or f"add value list {name}", dry_run, f"+ value-list {name}", check_value_list(name, values)
    )


def add_custom_function(
    ws: Workspace, name: str, calc: str, params: list[str] | None = None, message: str = "", dry_run: bool = False
) -> str:
    action = objects.add_object(ws.export, "custom-function", objects.custom_function_xml(name, params or [], calc))
    return run(
        ws,
        action,
        message or f"add custom function {name}",
        dry_run,
        f"+ custom-function {name}",
        check_custom_function(name, calc, params or []),
    )


def steps_xml(export: Export, steps: str, existing: str = "") -> str:
    """<Step> XML from FileMaker script text, or the XML itself."""
    return steps if script.is_xml(steps) else script.build(export, steps, existing)


def check_steps(name: str, want: list[str]) -> Callable[[Export], str | None]:
    def check(export: Export) -> str | None:
        got = script.normalized(objects.script_steps(export, name)[1])
        for i, (w, g) in enumerate(zip(want, got), 1):
            if w != g:
                return f"step {i} came back as `{g}` instead of `{w}` (FileMaker dropped or changed a parameter)"
        if len(want) != len(got):
            return f"the script has {len(got)} steps instead of {len(want)}"
        return None

    return check


def add_script(ws: Workspace, name: str, steps: str = "", message: str = "", dry_run: bool = False) -> str:
    xml = steps_xml(ws.export, steps) if steps.strip() else ""
    return run(
        ws,
        objects.add_script(ws.export, name, xml),
        message or f"add script {name}",
        dry_run,
        f"+ script {name}",
        check_steps(name, script.normalized(xml)),
    )


def add(ws: Workspace, kind: str, xml: str, message: str = "", dry_run: bool = False) -> str:
    action = objects.add_object(ws.export, kind, xml)
    name = re.search(r'\sname="([^"]*)"', xml)
    return run(ws, action, message or f"add {kind} {name.group(1) if name else ''}".strip(), dry_run)


def set_steps(ws: Workspace, name: str, steps: str, message: str = "", dry_run: bool = False) -> str:
    _, existing = objects.script_steps(ws.export, name)
    xml = steps_xml(ws.export, steps, existing)
    return run(
        ws,
        objects.set_steps(ws.export, name, xml),
        message or f"rewrite steps of {name}",
        dry_run,
        f"~ script {name}",
        check_steps(name, script.normalized(xml)),
    )


def append_steps(ws: Workspace, name: str, steps: str, message: str = "", dry_run: bool = False) -> str:
    _, existing = objects.script_steps(ws.export, name)
    xml = steps_xml(ws.export, steps)
    return run(
        ws,
        objects.append_steps(ws.export, name, xml),
        message or f"append steps to {name}",
        dry_run,
        f"~ script {name}",
        check_steps(name, script.normalized(existing) + script.normalized(xml)),
    )


def replace(ws: Workspace, kind: str, name: str, xml: str, message: str = "", dry_run: bool = False) -> str:
    return run(ws, objects.replace_object(ws.export, kind, name, xml), message or f"edit {kind} {name}", dry_run)


def place_field(
    ws: Workspace,
    layout: str,
    field: str,
    near: str,
    label: str | None = None,
    side: str = "below",
    message: str = "",
    dry_run: bool = False,
) -> str:
    xml, field_uuid = place.place_field(ws.export, layout, field, near, label, side)

    def check(export: Export) -> str | None:
        found = re.search(rf'<FieldReference [^>]*\bUUID="{field_uuid}"', export.layout(layout).xml)
        return None if found else f"{field} is not on {layout!r} in the result"

    return run(
        ws,
        objects.replace_object(ws.export, "layout", layout, xml),
        message or f"place {field} on {layout}",
        dry_run,
        f"~ layout {layout}",
        check,
    )


def uses(ws: Workspace, kind: str, name: str) -> str:
    return find_uses(ws.export, kind, name).report()


def delete(ws: Workspace, kind: str, name: str, message: str = "", dry_run: bool = False, force: bool = False) -> str:
    found = find_uses(ws.export, kind, name)
    if found.references and not force:
        raise PatchworkError(
            f"{found.report()}\nNot deleted: these would point at nothing. Check them first, "
            "then delete with --force (MCP: force=true). `undo` brings it back either way."
        )
    result = run(
        ws,
        objects.delete_object(ws.export, kind, name),
        message or f"delete {kind} {name}",
        dry_run,
        f"- {kind} {name}",
    )
    if found.references or found.mentions:
        result += f"\nWarning, review these: {found.report()}"
    return result


def retheme(
    ws: Workspace,
    theme: str = "",
    colors: dict | None = None,
    fonts: dict | None = None,
    rename: str = "",
    message: str = "",
    dry_run: bool = False,
) -> str:
    export = ws.export
    label = theme or export.main_theme()
    action = theme_replace(export, label, rename or None, colors or {}, fonts or {})
    return run(ws, action, message or f"edit theme {export.theme(label).name}", dry_run)


def recolor_layouts(
    ws: Workspace,
    colors: dict | None = None,
    fonts: dict | None = None,
    swap_field: list[str] | None = None,
    only: list[str] | None = None,
    message: str = "",
    dry_run: bool = False,
) -> str:
    patch, names = layouts_patch(
        ws.export, only or None, colors or {}, fonts or {}, tuple(swap_field) if swap_field else None
    )
    if not names:
        raise PatchworkError("No layout would change.")
    return run(ws, patch, message or f"edit {len(names)} layout(s)", dry_run)


def push(ws: Workspace, patch_xml: str, message: str = "", dry_run: bool = False) -> str:
    if "<FMUpgradeToolPatch" not in patch_xml:
        raise PatchworkError("Expected a full patch (root <FMUpgradeToolPatch>).")
    return run(ws, patch_xml, message or "push patch", dry_run)


def palette(ws: Workspace, theme: str = "") -> str:
    block = ws.export.theme(theme or ws.export.main_theme())
    return f"{block.name}\n" + "\n".join(f"{color}  {count}x" for color, count in theme_palette(block.xml))


def undo(ws: Workspace) -> str:
    return f"Back to v{ws.undo():03d}"


def log(ws: Workspace) -> str:
    lines = []
    for entry in ws.log():
        lines.append(f"v{entry['n']:03d}  {entry['time']}  {entry['message']}")
        lines += [f"        {c}" for c in entry.get("changes", [])[:10]]
    return "\n".join(lines)


def save(ws: Workspace, dest: str, force: bool = False) -> str:
    return f"Saved v{ws.version:03d} to {ws.save(Path(dest), force)}"


def load_json(value: str | dict | None) -> dict:
    if not value:
        return {}
    if isinstance(value, dict):
        return value
    path = Path(value)
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return json.loads(value)
