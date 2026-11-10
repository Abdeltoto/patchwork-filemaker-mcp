"""Who uses an object: references by UUID (certain) and mentions in calculation text (possible).

FileMaker exports point at layouts, scripts, fields, value lists and tables with
`<…Reference … UUID="…">` elements. Custom functions, and fields used in calculations,
only appear as text, so those are reported as possible mentions.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

from patchwork import PatchworkError, objects
from patchwork.export import Export, unescape

CDATA = re.compile(r"<!\[CDATA\[([\s\S]*?)\]\]>")
STRING = re.compile(r'"(?:[^"\\]|\\.)*"')


@dataclass
class Uses:
    target: str
    references: Counter = field(default_factory=Counter)
    mentions: Counter = field(default_factory=Counter)

    def report(self) -> str:
        if not self.references and not self.mentions:
            return f"Nothing in the file uses {self.target}."
        lines = []
        if self.references:
            lines.append(f"{self.target} is referenced by {len(self.references)} object(s):")
            lines += [f"  {owner}  ({count}x)" for owner, count in sorted(self.references.items())]
        if self.mentions:
            lines.append(f"Possible mentions by name in calculations ({len(self.mentions)}):")
            lines += [f"  {owner}  ({count}x)" for owner, count in sorted(self.mentions.items())]
        return "\n".join(lines)


def owners(export: Export) -> list[tuple[int, int, str]]:
    """(start, end, label) of every object that can hold a reference, plus each catalog as a fallback."""
    text = export.text
    spans: list[tuple[int, int, str]] = []

    def section(tag: str) -> tuple[int, int] | None:
        start = text.find(f"<{tag}")
        end = text.find(f"</{tag}>", start)
        return (start, end) if start >= 0 and end >= 0 else None

    def scan(tag: str, pattern: str, label) -> None:
        bounds = section(tag)
        if bounds:
            for match in re.compile(pattern).finditer(text, *bounds):
                spans.append((match.start(), match.end(), label(match)))

    for catalog in set(re.findall(r"<(\w+Catalog)[ >]", text)) - {"FieldCatalog"}:
        bounds = section(catalog)
        if bounds:
            words = re.sub(r"(?<!^)(?=[A-Z])", " ", catalog[: -len("Catalog")]).lower()
            spans.append((*bounds, f"{words} catalog"))
    scan("StepsForScripts", r'<Script>\s*<ScriptReference [^>]*\bname="([^"]*)"[\s\S]*?</Script>',
         lambda m: f"script {unescape(m.group(1))}")
    scan("LayoutCatalog", r'<Layout [^>]*\bname="([^"]*)"[^>]*>[\s\S]*?</Layout>', lambda m: f"layout {unescape(m.group(1))}")
    scan("CustomFunctionsCatalog", r'<CustomFunction [^>]*\bname="([^"]*)"[\s\S]*?</CustomFunction>',
         lambda m: f"custom-function {unescape(m.group(1))}")
    scan("TableOccurrenceCatalog", r'<TableOccurrence [^>]*\bname="([^"]*)"[\s\S]*?</TableOccurrence>',
         lambda m: f"table-occurrence {unescape(m.group(1))}")
    scan("ValueListCatalog", r'<ValueList [^>]*\bname="([^"]*)"[\s\S]*?</ValueList>', lambda m: f"value-list {unescape(m.group(1))}")
    bounds = section("FieldsForTables")
    if bounds:
        for catalog in re.compile(r"<FieldCatalog>[\s\S]*?</FieldCatalog>").finditer(text, *bounds):
            table = re.search(r'<BaseTableReference [^>]*\bname="([^"]*)"', catalog.group(0))
            prefix = unescape(table.group(1)) if table else "?"
            spans.append((catalog.start(), catalog.end(), f"table {prefix}"))
            for match in re.compile(r'<Field id="\d+" name="([^"]*)"[\s\S]*?</Field>').finditer(text, catalog.start(), catalog.end()):
                spans.append((match.start(), match.end(), f"field {prefix}::{unescape(match.group(1))}"))
    return spans


def owner_at(spans: list[tuple[int, int, str]], position: int) -> str:
    inside = [(end - start, label) for start, end, label in spans if start <= position < end]
    return min(inside)[1] if inside else "file"


def resolve(export: Export, kind: str, name: str) -> tuple[str, str, list[re.Pattern], str | None]:
    """(label, UUID, mention patterns, table whose own field calculations may use the bare name)."""
    if kind == "field":
        table, field_name = objects.split_field(name)
        _, uuid = export.field(table, field_name)
        occurrences = [o.name for o in objects.items(export, "table-occurrences")
                       if re.search(rf'<BaseTableReference [^>]*\bname="{re.escape(table)}"', o.xml)]
        patterns = [re.compile(rf"(?<![\w:]){re.escape(o)}::{re.escape(field_name)}(?![\w])") for o in occurrences or [table]]
        return f"field {table}::{field_name}", uuid, patterns, table
    item = objects.find(export, kind, name)
    patterns = [re.compile(rf"(?<![\w.]){re.escape(item.name)}(?![\w])")] if kind == "custom-function" else []
    return f"{kind} {item.name}", item.uuid, patterns, None


def find_uses(export: Export, kind: str, name: str) -> Uses:
    if kind != "field":
        kind = objects.kind(kind).name
    label, uuid, patterns, table = resolve(export, kind, name)
    spans = owners(export)
    result = Uses(label)
    if uuid:
        for match in re.finditer(rf'<\w+Reference [^>]*\bUUID="{re.escape(uuid)}"', export.text):
            owner = owner_at(spans, match.start())
            if owner != label:
                result.references[owner] += 1
    bare = re.compile(rf"(?<![\w:]){re.escape(name.split('::', 1)[1])}(?![\w:])") if table else None
    for match in CDATA.finditer(export.text):
        calc = STRING.sub('""', match.group(1))
        owner = None
        hits = sum(len(p.findall(calc)) for p in patterns)
        if bare:
            owner = owner_at(spans, match.start())
            if owner.startswith(f"field {table}::"):
                hits += len(bare.findall(calc))
        if hits:
            owner = owner or owner_at(spans, match.start())
            if owner != label and owner not in result.references:
                result.mentions[owner] += hits
    return result
