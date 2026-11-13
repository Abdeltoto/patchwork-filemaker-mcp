"""The `patchwork` command."""

from __future__ import annotations

import argparse
import os
import platform
import sys
from pathlib import Path

from patchwork import PatchworkError, __version__, ops
from patchwork.build import FIELD_TYPES
from patchwork.project import init_project
from patchwork.rebrand import Brand, rebrand
from patchwork.tools import PASSWORD_ENV, Runner, find_tool, require_copy, require_new, require_root, require_source
from patchwork.workspace import Workspace

EPILOG = f"""typical session:
  patchwork open "Invoice.fmp12" --account Admin      working copy v000 in .patchwork/
  patchwork ls scripts
  patchwork show script "Close Window"
  patchwork add-field Contacts Status
  patchwork add-value-list "Status" Active Archived
  patchwork log
  patchwork undo
  patchwork save "Invoice v2.fmp12"

AI agents: `patchwork mcp` is an MCP server for Claude, Cursor, Codex and Antigravity. See docs/ai-agents.md.
The password is read from {PASSWORD_ENV}. Docs: https://github.com/Abdeltoto/patchwork-filemaker-mcp"""

KINDS_SHOW = ["layout", "script", "value-list", "custom-function", "theme", "field", "step"]


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")
    args = build_parser().parse_args(argv)
    try:
        return args.func(args) or 0
    except PatchworkError as exc:
        print(f"patchwork: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="patchwork",
        description="Edit FileMaker files from code or from an AI agent, with Claris FMUpgradeTool. Always on a copy.",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"patchwork {__version__}")
    parser.add_argument(
        "-C", "--project", type=Path, help="Project folder holding .patchwork/ (default: search upward from here)."
    )
    sub = parser.add_subparsers(dest="command", required=True, metavar="<command>")

    p = sub.add_parser("open", help="Start a working copy of a closed .fmp12 (never modified).")
    p.add_argument("source", type=Path)
    p.add_argument("--account", required=True, help="Full Access account.")
    p.add_argument(
        "--no-password", action="store_true", help=f"The account has no password. Otherwise {PASSWORD_ENV} is read."
    )
    p.add_argument("--force", action="store_true", help="Replace an existing workspace.")
    p.set_defaults(func=cmd_open)

    simple(sub, "status", "Current version and contents.", lambda ws, a: ops.status(ws))
    simple(sub, "log", "Version history.", lambda ws, a: ops.log(ws))
    simple(sub, "undo", "Drop the last version.", lambda ws, a: ops.undo(ws))

    p = sub.add_parser("save", help="Write the current version to a new .fmp12.")
    p.add_argument("dest", type=Path)
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=ws_cmd(lambda ws, a: ops.save(ws, str(a.dest), a.force)))

    p = sub.add_parser("ls", help="List objects: " + ", ".join(ops.LISTABLE) + ".")
    p.add_argument("kind", nargs="?", default="", choices=["", *ops.LISTABLE], metavar="KIND")
    p.add_argument("table", nargs="?", default="", help="For `ls fields TABLE`.")
    p.set_defaults(func=ws_cmd(lambda ws, a: ops.list_objects(ws, a.kind, a.table)))

    p = sub.add_parser(
        "show",
        help="Print an object: a script as FileMaker text, anything else as XML (kind step: an example step by name).",
    )
    p.add_argument("kind", choices=KINDS_SHOW)
    p.add_argument("name", help="Object name; Table::Field for a field.")
    p.add_argument("--xml", action="store_true", help="A script as XML instead of text.")
    p.set_defaults(func=ws_cmd(lambda ws, a: ops.show(ws, a.kind, a.name, a.xml)))

    p = sub.add_parser("uses", help="What references an object, and possible mentions by name in calculations.")
    p.add_argument(
        "kind",
        choices=["layout", "script", "value-list", "custom-function", "theme", "table", "table-occurrence", "field"],
    )
    p.add_argument("name", help="Object name; Table::Field for a field.")
    p.set_defaults(func=ws_cmd(lambda ws, a: ops.uses(ws, a.kind, a.name)))

    p = sub.add_parser("palette", help="Colors a theme uses.")
    p.add_argument("--theme", default="")
    p.set_defaults(func=ws_cmd(lambda ws, a: ops.palette(ws, a.theme)))

    p = edit(sub, "add-field", "Add a field.")
    p.add_argument("table")
    p.add_argument("name")
    p.add_argument("--type", default="Text", choices=list(FIELD_TYPES))
    p.add_argument("--calc", default="", help="Formula: the field becomes a calculation.")
    p.add_argument("--global", dest="is_global", action="store_true")
    p.add_argument("--comment", default="")
    p.add_argument("--context", default="", help="Table occurrence of the calculation.")
    p.add_argument("--image", default="", help="Embed a PNG as a global container calculation.")
    p.add_argument("--image-width", type=int, default=0, help="Resize the PNG first (needs Pillow).")
    p.set_defaults(
        func=ws_cmd(
            lambda ws, a: ops.add_field(
                ws,
                a.table,
                a.name,
                a.type,
                a.calc,
                a.is_global,
                a.comment,
                a.context,
                a.image,
                a.image_width,
                a.message,
                a.dry_run,
            )
        )
    )

    p = edit(sub, "add-value-list", "Add a custom value list.")
    p.add_argument("name")
    p.add_argument("values", nargs="+")
    p.set_defaults(func=ws_cmd(lambda ws, a: ops.add_value_list(ws, a.name, a.values, a.message, a.dry_run)))

    p = edit(sub, "add-custom-function", "Add a custom function.")
    p.add_argument("name")
    p.add_argument("--calc", required=True)
    p.add_argument("--param", dest="params", action="append", default=[])
    p.set_defaults(
        func=ws_cmd(lambda ws, a: ops.add_custom_function(ws, a.name, a.calc, a.params, a.message, a.dry_run))
    )

    p = edit(sub, "add-script", "Create a script from FileMaker script text or <Step> XML (file, or - for stdin).")
    p.add_argument("name")
    p.add_argument("steps", nargs="?", default="")
    p.set_defaults(
        func=ws_cmd(lambda ws, a: ops.add_script(ws, a.name, read(a.steps) if a.steps else "", a.message, a.dry_run))
    )

    p = edit(
        sub, "set-steps", "Replace all steps of a script with text from `show script`, edited (file, or - for stdin)."
    )
    p.add_argument("script")
    p.add_argument("steps")
    p.set_defaults(func=ws_cmd(lambda ws, a: ops.set_steps(ws, a.script, read(a.steps), a.message, a.dry_run)))

    p = edit(sub, "append-steps", "Add steps at the end of a script.")
    p.add_argument("script")
    p.add_argument("steps")
    p.set_defaults(func=ws_cmd(lambda ws, a: ops.append_steps(ws, a.script, read(a.steps), a.message, a.dry_run)))

    p = edit(sub, "place-field", "Put a field on a layout, copying the look and label of a field already there.")
    p.add_argument("layout")
    p.add_argument("field", help="Occurrence::Field, e.g. Clients::Status")
    p.add_argument(
        "--near", required=True, help="A field already on the layout. The new one goes below it (a row is inserted)."
    )
    p.add_argument("--label", default=None, help="Label text. Default: the field name.")
    p.add_argument("--side", choices=["below", "right"], default="below")
    p.set_defaults(
        func=ws_cmd(lambda ws, a: ops.place_field(ws, a.layout, a.field, a.near, a.label, a.side, a.message, a.dry_run))
    )

    p = edit(sub, "add", "Add an object from XML: value-list or custom-function.")
    p.add_argument("kind", choices=["value-list", "custom-function"])
    p.add_argument("xml")
    p.set_defaults(func=ws_cmd(lambda ws, a: ops.add(ws, a.kind, read(a.xml), a.message, a.dry_run)))

    p = edit(sub, "replace", "Replace a whole object with edited XML from `show`.")
    p.add_argument("kind", choices=["layout", "theme", "value-list", "custom-function"])
    p.add_argument("name")
    p.add_argument("xml")
    p.set_defaults(func=ws_cmd(lambda ws, a: ops.replace(ws, a.kind, a.name, read(a.xml), a.message, a.dry_run)))

    p = edit(sub, "delete", "Delete a script, layout, value-list, custom-function or field (Table::Field).")
    p.add_argument("kind", choices=["script", "layout", "value-list", "custom-function", "field"])
    p.add_argument("name")
    p.add_argument("--force", action="store_true", help="Delete even if other objects reference it.")
    p.set_defaults(func=ws_cmd(lambda ws, a: ops.delete(ws, a.kind, a.name, a.message, a.dry_run, a.force)))

    p = edit(sub, "retheme", "Rewrite a theme: colors, fonts, name.")
    p.add_argument("--theme", default="", help="Default: the theme most layouts use.")
    p.add_argument("--colors", help='JSON file or inline map {"0091CE": "2F5D50"}')
    p.add_argument("--fonts", help='JSON file or inline map {"HelveticaNeue,HelveticaNeue": "Georgia,Georgia"}')
    p.add_argument("--rename", default="")
    p.set_defaults(
        func=ws_cmd(
            lambda ws, a: ops.retheme(
                ws, a.theme, ops.load_json(a.colors), ops.load_json(a.fonts), a.rename, a.message, a.dry_run
            )
        )
    )

    p = edit(sub, "recolor-layouts", "Rewrite layouts: local colors, fonts, a field swapped everywhere.")
    p.add_argument("--colors")
    p.add_argument("--fonts")
    p.add_argument("--swap-field", nargs=2, metavar=("Table::Old", "Table::New"))
    p.add_argument("--only", nargs="+", metavar="LAYOUT")
    p.set_defaults(
        func=ws_cmd(
            lambda ws, a: ops.recolor_layouts(
                ws, ops.load_json(a.colors), ops.load_json(a.fonts), a.swap_field, a.only, a.message, a.dry_run
            )
        )
    )

    p = edit(sub, "push", "Apply a hand-written FMUpgradeToolPatch file.")
    p.add_argument("patch")
    p.set_defaults(func=ws_cmd(lambda ws, a: ops.push(ws, read(a.patch), a.message, a.dry_run)))

    p = sub.add_parser("rebrand", help="One-shot: apply a brand.json (colors, fonts, logo, theme name) file to file.")
    p.add_argument("src", type=Path)
    p.add_argument("dest", type=Path)
    p.add_argument("--brand", type=Path, required=True)
    p.add_argument("--account", required=True)
    p.add_argument("--no-password", action="store_true")
    p.add_argument("--force", action="store_true")
    p.add_argument("--keep-work", action="store_true")
    p.set_defaults(func=cmd_rebrand)

    p = sub.add_parser("mcp", help="Run the MCP server (stdio) for Claude, Cursor, Codex, Antigravity.")
    p.set_defaults(func=cmd_mcp)

    p = sub.add_parser(
        "init", help="Wire a folder, new or existing, for Claude Code, Cursor, Codex and Antigravity. Never overwrites."
    )
    p.add_argument("directory", type=Path)
    p.add_argument("--name", default="")
    p.add_argument("--no-skills", action="store_true")
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("doctor", help="Show which tools Patchwork can find.")
    p.set_defaults(func=cmd_doctor)

    tool_parser(sub)
    return parser


def simple(sub, name: str, help_text: str, handler) -> None:
    p = sub.add_parser(name, help=help_text)
    p.set_defaults(func=ws_cmd(handler))


def edit(sub, name: str, help_text: str) -> argparse.ArgumentParser:
    p = sub.add_parser(name, help=help_text)
    p.add_argument("-m", "--message", default="", help="Note for the version log.")
    p.add_argument("--dry-run", action="store_true", help="Write the patch to .patchwork/ without applying it.")
    return p


def ws_cmd(handler):
    def run(args: argparse.Namespace) -> int:
        print(handler(Workspace.locate(args.project), args))
        return 0

    return run


def read(source: str) -> str:
    if source == "-":
        return sys.stdin.read()
    path = Path(source)
    if not path.is_file():
        raise PatchworkError(f"File not found: {source}")
    return path.read_text(encoding="utf-8-sig")


def cmd_open(args: argparse.Namespace) -> int:
    print(
        ops.open_file(
            str(args.source), args.account, args.no_password, str(args.project) if args.project else None, args.force
        )
    )
    return 0


def cmd_rebrand(args: argparse.Namespace) -> int:
    brand = Brand.load(args.brand)
    report = rebrand(
        args.src, args.dest, brand, Runner(args.account, args.no_password, quiet=True), args.force, args.keep_work
    )
    print(f"\nDone: {args.dest.resolve()}")
    print(f"  theme      {report.theme}")
    print(f"  layouts    {len(report.layouts)} rewritten")
    if report.logo_refs is not None:
        print(f"  logo       on {report.logo_refs} layout object(s)")
    if args.keep_work:
        print(f"  work files {report.work}")
    return 0


def cmd_mcp(args: argparse.Namespace) -> int:
    from patchwork.mcp import serve

    return serve(args.project)


def cmd_init(args: argparse.Namespace) -> int:
    print(init_project(args.directory, args.name, skills=not args.no_skills).report())
    return 0


def cmd_doctor(_args: argparse.Namespace) -> int:
    upgrade, developer = find_tool("FMUpgradeTool"), find_tool("FMDeveloperTool")
    rows = [
        ("patchwork", __version__),
        ("python", platform.python_version()),
        ("FMUpgradeTool", str(upgrade) if upgrade else "missing - see docs/install-fmupgradetool.md"),
        ("FMDeveloperTool", str(developer) if developer else "missing - ships next to FMUpgradeTool"),
        ("Pillow (optional)", "installed" if has_pillow() else "missing - only needed to resize images"),
        (PASSWORD_ENV, "set" if os.environ.get(PASSWORD_ENV) else "not set"),
    ]
    for name, value in rows:
        print(f"{name:18} {value}")
    return 0 if upgrade and developer else 2


def has_pillow() -> bool:
    try:
        import PIL  # noqa: F401
    except ImportError:
        return False
    return True


# ----- plumbing: direct access to the Claris tools -----


def tool_parser(sub) -> None:
    tool = sub.add_parser("tool", help="Run FMUpgradeTool / FMDeveloperTool directly, file to file.")
    tsub = tool.add_subparsers(dest="tool_command", required=True, metavar="<tool command>")

    def creds(p: argparse.ArgumentParser) -> None:
        p.add_argument("--account", required=True)
        p.add_argument("--no-password", action="store_true")
        p.add_argument("--force", action="store_true")

    p = tsub.add_parser("guids", help="FMUpgradeTool --generateGUIDs into a copy.")
    p.add_argument("src", type=Path)
    p.add_argument("dest", type=Path)
    creds(p)
    p.set_defaults(func=lambda a: plumbing(a, "guids"))

    p = tsub.add_parser("export", help="FMDeveloperTool --saveAsXML.")
    p.add_argument("src", type=Path)
    p.add_argument("out", type=Path)
    creds(p)
    p.set_defaults(func=lambda a: plumbing(a, "export"))

    p = tsub.add_parser("validate", help="FMUpgradeTool --validatePatch.")
    p.add_argument("src", type=Path)
    p.add_argument("patch", type=Path)
    creds(p)
    p.set_defaults(func=lambda a: plumbing(a, "validate"))

    p = tsub.add_parser("apply", help="FMUpgradeTool --update into a copy.")
    p.add_argument("src", type=Path)
    p.add_argument("patch", type=Path)
    p.add_argument("dest", type=Path)
    creds(p)
    p.set_defaults(func=lambda a: plumbing(a, "apply"))

    p = tsub.add_parser("new-file", help="FMUpgradeTool --generateDBFile from a complete FMSaveAsXML.")
    p.add_argument("xml", type=Path)
    p.set_defaults(func=lambda a: plumbing(a, "new-file"))


def plumbing(args: argparse.Namespace, what: str) -> int:
    runner = Runner(getattr(args, "account", ""), getattr(args, "no_password", False))
    if what == "new-file":
        require_root(args.xml, "FMSaveAsXML")
        runner.new_file(args.xml.resolve())
        return 0
    src = require_source(args.src)
    if what == "guids":
        runner.generate_guids(src, require_copy(src, args.dest, args.force), args.force)
    elif what == "export":
        out = require_new(args.out, args.force)
        out.parent.mkdir(parents=True, exist_ok=True)
        runner.export_xml(src, out, args.force)
    elif what == "validate":
        require_root(args.patch, "FMUpgradeToolPatch")
        runner.validate(src, args.patch.resolve())
        print("Valid syntax. FMUpgradeTool does not check that the change will apply: use a workspace for that.")
    else:
        require_root(args.patch, "FMUpgradeToolPatch")
        runner.apply(src, args.patch.resolve(), require_copy(src, args.dest, args.force), args.force)
    return 0


if __name__ == "__main__":
    sys.exit(main())
