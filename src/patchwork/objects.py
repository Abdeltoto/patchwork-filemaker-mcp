"""Find, show, add, replace and delete FileMaker objects in a Save-as-XML export.

Every builder returns patch actions. Only the operations below were verified on real files
(FMUpgradeTool 26.0.3): anything else is refused rather than silently skipped.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass

from patchwork import PatchworkError
from patchwork.export import Export, escape, layout_uuid, unescape


@dataclass(frozen=True)
class Kind:
    name: str
    plural: str
    catalog: str
    tag: str
    reference: str
    can_add: bool = False
    can_replace: bool = False
    can_delete: bool = False
    object_list: bool = False


KINDS = {
    k.name: k
    for k in (
        Kind("layout", "layouts", "LayoutCatalog", "Layout", "LayoutReference", can_replace=True, can_delete=True),
        Kind("script", "scripts", "ScriptCatalog", "Script", "ScriptReference", can_add=True, can_delete=True),
        Kind("value-list", "value-lists", "ValueListCatalog", "ValueList", "ValueListReference", can_add=True, can_replace=True, can_delete=True),
        Kind("custom-function", "custom-functions", "CustomFunctionsCatalog", "CustomFunction", "CustomFunctionReference",
             can_add=True, can_replace=True, can_delete=True, object_list=True),
        Kind("theme", "themes", "ThemeCatalog", "Theme", "LayoutThemeReference", can_replace=True),
        Kind("table", "tables", "BaseTableCatalog", "BaseTable", "BaseTableReference"),
        Kind("table-occurrence", "table-occurrences", "TableOccurrenceCatalog", "TableOccurrence", "TableOccurrenceReference"),
    )
}
PLURALS = {k.plural: k for k in KINDS.values()}


@dataclass
class Item:
    kind: str
    id: str
    name: str
    uuid: str
    xml: str


def kind(name: str) -> Kind:
    found = KINDS.get(name) or PLURALS.get(name)
    if not found:
        raise PatchworkError(f"Unknown kind: {name}. Choose from {', '.join(KINDS)}, field.")
    return found


def items(export: Export, kind_name: str) -> list[Item]:
    k = kind(kind_name)
    if k.name == "theme":
        return [Item("theme", "", display or internal, uid, export.theme(internal or display).xml if uid else "")
                for display, internal, uid in export.themes()]
    try:
        section = export.section(k.catalog)
    except PatchworkError:
        return []
    found = []
    for match in re.finditer(rf"<{k.tag} [^>]*>[\s\S]*?</{k.tag}>", section):
        block = match.group(0)
        head = block[: block.index(">")]
        ident, name = re.search(r'\sid="(\d+)"', head), re.search(r'\sname="([^"]*)"', head)
        if not ident or not name or "isFolder=" in head or 'isSeparatorItem="True"' in head:
            continue
        found.append(Item(k.name, ident.group(1), unescape(name.group(1)), own_uuid(block), block))
    return found


def find(export: Export, kind_name: str, name: str) -> Item:
    for item in items(export, kind_name):
        if item.name == name:
            return item
    raise PatchworkError(f"{kind(kind_name).name} not found: {name}")


def own_uuid(block: str) -> str:
    try:
        return layout_uuid(block)
    except PatchworkError:
        found = re.search(r"<UUID[^>]*>([^<]*)</UUID>", block)
        return found.group(1) if found else ""


def catalog_uuid(export: Export, catalog: str) -> str:
    found = re.search(r"<UUID[^>]*>([^<]+)</UUID>", export.section(catalog))
    if not found:
        raise PatchworkError(f"{catalog} has no UUID. Run `patchwork open` again on the original file.")
    return found.group(1)


def next_id(export: Export, k: Kind) -> int:
    try:
        section = export.section(k.catalog)
    except PatchworkError:
        return 1
    return max((int(i) for i in re.findall(rf'<{k.tag} [^>]*?\bid="(\d+)"', section)), default=0) + 1


# ---------- show ----------

def script_steps(export: Export, name: str) -> tuple[str, str]:
    """(ScriptReference tag, steps XML) of a script."""
    script = find(export, "script", name)
    steps = export.section("StepsForScripts")
    match = re.search(
        rf'<Script>\s*(<ScriptReference id="{script.id}" [^>]*></ScriptReference>)\s*(?:<ObjectList[^>]*>([\s\S]*?)</ObjectList>)?\s*</Script>',
        steps,
    )
    if not match:
        reference = f'<ScriptReference id="{script.id}" name="{escape(script.name)}" UUID="{script.uuid}"></ScriptReference>'
        return reference, ""
    return match.group(1), match.group(2) or ""


def show(export: Export, kind_name: str, name: str) -> str:
    if kind_name == "field":
        table, field = split_field(name)
        _, _, catalog = export.field_catalog(table)
        match = re.search(rf'<Field id="\d+" name="{re.escape(escape(field))}"[\s\S]*?</Field>', catalog)
        if not match:
            raise PatchworkError(f"Field not found: {name}")
        return dedent(match.group(0))
    if kind_name == "step":
        match = re.search(rf'<Step [^>]*name="{re.escape(escape(name))}"[\s\S]*?</Step>', export.section("StepsForScripts"))
        if not match:
            raise PatchworkError(f"No script in this file uses the step {name!r}. Look at another file for an example.")
        return dedent(match.group(0))
    item = find(export, kind_name, name)
    if item.kind == "script":
        _, steps = script_steps(export, name)
        return dedent(item.xml) + "\n" + dedent(steps)
    return dedent(item.xml)


def dedent(xml: str) -> str:
    lines = xml.strip("\n").split("\n")
    tabs = [len(line) - len(line.lstrip("\t")) for line in lines[1:] if line.strip()]
    cut = max(min(tabs, default=1) - 1, 0)
    return "\n".join([lines[0]] + [line[cut:] if line[:cut].strip() == "" else line for line in lines[1:]])


# ---------- builders ----------

def new_uuid() -> str:
    return str(uuid.uuid4()).upper()


def fresh_uuids(xml: str) -> str:
    return re.sub(r"<UUID[^>]*>[^<]*</UUID>", lambda _: f"<UUID>{new_uuid()}</UUID>", xml)


def parse_steps(xml: str, start: int = 0) -> list[str]:
    steps = re.findall(r"<Step\b[\s\S]*?</Step>", xml)
    if not steps:
        raise PatchworkError("No <Step> element found. Use `patchwork show script NAME` or `show step NAME` for examples.")
    out = []
    for offset, step in enumerate(steps):
        head_end = step.index(">")
        head = re.sub(r'\s(hash|index)="[^"]*"', "", step[:head_end])
        head = head.replace("<Step", f'<Step index="{start + offset}"', 1)
        body = step[head_end:]
        if not re.search(r"<UUID[^>]*>", body):
            body = body.replace(">", f">\n\t<UUID>{new_uuid()}</UUID>", 1)
        out.append(fresh_uuids(head + body))
    return out


def steps_action(reference: str, steps: list[str]) -> str:
    return (
        '\t\t\t<StepsForScripts membercount="1">\n\t\t\t\t<Script>\n'
        f"\t\t\t\t\t{reference}\n"
        f'\t\t\t\t\t<ObjectList membercount="{len(steps)}">\n' + "\n".join(steps) + "\n\t\t\t\t\t</ObjectList>\n"
        "\t\t\t\t</Script>\n\t\t\t</StepsForScripts>\n"
    )


def add_script(export: Export, name: str, steps_xml: str) -> str:
    k = KINDS["script"]
    if any(item.name == name for item in items(export, "script")):
        raise PatchworkError(f"A script named {name!r} already exists.")
    script_id, script_uuid = next_id(export, k), new_uuid()
    steps = parse_steps(steps_xml) if steps_xml.strip() else []
    reference = f'<ScriptReference id="{script_id}" name="{escape(name)}" UUID="{script_uuid}"></ScriptReference>'
    action = (
        "\t\t<AddAction>\n"
        f'\t\t\t<ScriptCatalog membercount="1">\n\t\t\t\t<UUID>{catalog_uuid(export, k.catalog)}</UUID>\n\t\t\t\t<TagList></TagList>\n'
        f'\t\t\t\t<Script id="{script_id}" name="{escape(name)}">\n\t\t\t\t\t<UUID>{script_uuid}</UUID>\n'
        '\t\t\t\t\t<Options hidden="False" access="ReadWrite" SiriShortcutVisible="False" runwithfullaccess="False" compatibility="0">0</Options>\n'
        "\t\t\t\t\t<TagList></TagList>\n\t\t\t\t</Script>\n\t\t\t</ScriptCatalog>\n"
        + (steps_action(reference, steps) if steps else "")
        + "\t\t</AddAction>\n"
    )
    return action


def append_steps(export: Export, script: str, steps_xml: str) -> str:
    reference, existing = script_steps(export, script)
    count = len(re.findall(r"<Step\b", existing))
    return "\t\t<AddAction>\n" + steps_action(reference, parse_steps(steps_xml, count)) + "\t\t</AddAction>\n"


def set_steps(export: Export, script: str, steps_xml: str) -> str:
    reference, existing = script_steps(export, script)
    old = re.findall(r"<Step [^>]*>\s*<UUID[^>]*>([^<]+)</UUID>", existing)
    deletes = "".join(
        f'\t\t\t<ItemReference UUID="{uid}" type="ScriptStepReference">\n\t\t\t\t{reference}\n\t\t\t</ItemReference>\n' for uid in old
    )
    delete = f"\t\t<DeleteAction>\n{deletes}\t\t</DeleteAction>\n" if old else ""
    return delete + "\t\t<AddAction>\n" + steps_action(reference, parse_steps(steps_xml)) + "\t\t</AddAction>\n"


def add_object(export: Export, kind_name: str, xml: str) -> str:
    k = kind(kind_name)
    if not k.can_add or k.name == "script":
        raise PatchworkError(f"Adding a {k.name} this way is not supported." + (" Use add-script." if k.name == "script" else ""))
    block = re.search(rf"<{k.tag}\b[\s\S]*</{k.tag}>", xml)
    if not block:
        raise PatchworkError(f"Expected a <{k.tag}> element. Use `patchwork show {k.name} NAME` for an example.")
    obj = block.group(0)
    name = re.search(r'\sname="([^"]*)"', obj[: obj.index(">")])
    if not name:
        raise PatchworkError(f"The <{k.tag}> needs a name attribute.")
    if any(item.name == unescape(name.group(1)) for item in items(export, k.name)):
        raise PatchworkError(f"A {k.name} named {unescape(name.group(1))!r} already exists.")
    head_end = obj.index(">")
    head = re.sub(r'\sid="\d*"', "", obj[:head_end]).replace(f"<{k.tag}", f'<{k.tag} id="{next_id(export, k)}"', 1)
    obj = head + obj[head_end:]
    if not re.search(r"<UUID[^>]*>", obj):
        if k.name == "value-list":
            obj = obj.replace(f"</{k.tag}>", f"\t<UUID>{new_uuid()}</UUID>\n\t<TagList></TagList>\n</{k.tag}>")
        else:
            obj = obj.replace(">", f">\n\t<UUID>{new_uuid()}</UUID>\n\t<TagList></TagList>", 1)
    obj = fresh_uuids(obj)
    inner = f'\t\t\t\t<ObjectList membercount="1">\n{obj}\n\t\t\t\t</ObjectList>\n' if k.object_list else f"{obj}\n"
    return (
        "\t\t<AddAction>\n"
        f'\t\t\t<{k.catalog} membercount="1">\n\t\t\t\t<UUID>{catalog_uuid(export, k.catalog)}</UUID>\n\t\t\t\t<TagList></TagList>\n'
        f"{inner}\t\t\t</{k.catalog}>\n\t\t</AddAction>\n"
    )


def value_list_xml(name: str, values: list[str]) -> str:
    text = "\r".join(values)
    if "]]>" in text:
        raise PatchworkError("Values cannot contain ']]>'.")
    return (
        f'<ValueList name="{escape(name)}">\n\t<Source value="Custom"></Source>\n'
        f"\t<CustomValues>\n\t\t<Text><![CDATA[{text}]]></Text>\n\t</CustomValues>\n</ValueList>"
    )


def custom_function_xml(name: str, params: list[str], calc: str) -> str:
    if "]]>" in calc:
        raise PatchworkError("The calculation cannot contain ']]>'.")
    display = f"{name} ( {' ; '.join(params)} )" if params else name
    parameters = ""
    if params:
        parameters = (f'\t<ObjectList membercount="{len(params)}">\n'
                      + "".join(f'\t\t<Parameter name="{escape(p)}"></Parameter>\n' for p in params)
                      + "\t</ObjectList>\n")
    return (
        f'<CustomFunction name="{escape(name)}" access="All">\n'
        f"\t<Calculation>\n\t\t<Text><![CDATA[{calc}]]></Text>\n\t</Calculation>\n"
        f"\t<Display>{escape(display)}</Display>\n{parameters}</CustomFunction>"
    )


def replace_object(export: Export, kind_name: str, name: str, xml: str) -> str:
    k = kind(kind_name)
    if not k.can_replace:
        raise PatchworkError(f"Replacing a {k.name} is not supported. Supported: {', '.join(n for n, v in KINDS.items() if v.can_replace)}.")
    item = find(export, k.name, name)
    block = re.search(rf"<{k.tag}\b[\s\S]*</{k.tag}>", xml)
    if not block:
        raise PatchworkError(f"Expected the whole <{k.tag}> element, as printed by `patchwork show {k.name} {name!r}`.")
    if k.name == "theme" and not item.uuid:
        raise PatchworkError("This theme has no UUID. Run `patchwork open` again on the original file.")
    replace_type = "Layout" if k.name == "layout" else k.tag
    return f'\t\t<ReplaceAction>\n\t\t\t<Replace type="{replace_type}" UUID="{item.uuid}">\n{block.group(0)}\n\t\t\t</Replace>\n\t\t</ReplaceAction>\n'


def delete_object(export: Export, kind_name: str, name: str) -> str:
    if kind_name == "field":
        table, field = split_field(name)
        _, base_ref, _ = export.field_catalog(table)
        _, field_uuid = export.field(table, field)
        inner = f'\t\t\t<ItemReference UUID="{field_uuid}" type="FieldReference">\n\t\t\t\t{base_ref}\n\t\t\t</ItemReference>\n'
    else:
        k = kind(kind_name)
        if not k.can_delete:
            raise PatchworkError(f"Deleting a {k.name} is not supported.")
        item = find(export, k.name, name)
        inner = f'\t\t\t<ItemReference UUID="{item.uuid}" type="{k.reference}"></ItemReference>\n'
    return f"\t\t<DeleteAction>\n{inner}\t\t</DeleteAction>\n"


def split_field(qualified: str) -> tuple[str, str]:
    if "::" not in qualified:
        raise PatchworkError(f"Expected a field as Table::Field, got: {qualified}")
    table, name = qualified.split("::", 1)
    return table, name


# ---------- diff ----------

def normalize(text: str) -> str:
    text = re.sub(r"<FMSaveAsXML[^>]*>", "", text, count=1)
    return re.sub(r"<UUID [^>]*>", "<UUID>", text)


def inventory(export: Export) -> dict[tuple[str, str], str]:
    found: dict[tuple[str, str], str] = {}
    for name in ("layout", "script", "value-list", "custom-function", "theme", "table"):
        for item in items(export, name):
            found[(name, item.name)] = normalize(item.xml)
    try:
        steps = export.section("StepsForScripts")
        for match in re.finditer(r'<Script>\s*<ScriptReference id="\d+" name="([^"]*)"[\s\S]*?</Script>', steps):
            key = ("script", unescape(match.group(1)))
            found[key] = found.get(key, "") + normalize(match.group(0))
    except PatchworkError:
        pass
    try:
        fields = export.section("FieldsForTables")
        for catalog in re.finditer(r"<FieldCatalog>[\s\S]*?</FieldCatalog>", fields):
            table = re.search(r'<BaseTableReference id="\d+" name="([^"]*)"', catalog.group(0))
            for field in re.finditer(r'<Field id="\d+" name="([^"]*)"[\s\S]*?</Field>', catalog.group(0)):
                found[("field", f"{unescape(table.group(1)) if table else '?'}::{unescape(field.group(1))}")] = normalize(field.group(0))
    except PatchworkError:
        pass
    return found


def diff(before: Export, after: Export) -> list[str]:
    old, new = inventory(before), inventory(after)
    changes = [f"+ {k} {n}" for (k, n) in new if (k, n) not in old]
    changes += [f"- {k} {n}" for (k, n) in old if (k, n) not in new]
    changes += [f"~ {k} {n}" for (k, n), v in new.items() if (k, n) in old and old[(k, n)] != v]
    return sorted(changes, key=lambda c: (c[2:], c[0]))
