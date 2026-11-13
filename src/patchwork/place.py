"""Put a field on a layout by copying one that is already there, with its label.

FMUpgradeTool skips a lone LayoutObject add or replace, so the whole layout is replaced.
Bounds in a Save-as-XML export are absolute (from the top of the layout), and a field
points at its label with <Accessibility><Label>ID</Label>.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from patchwork import PatchworkError, objects
from patchwork.export import Export, escape, unescape

OBJECT = re.compile(r"(?m)^(\t*)<LayoutObject [^>]*>[\s\S]*?^\1</LayoutObject>")
BOUNDS = re.compile(r'<Bounds top="(-?[\d.]+)" left="(-?[\d.]+)" bottom="(-?[\d.]+)" right="(-?[\d.]+)"></Bounds>')
GAP = 10
SLACK = 4


@dataclass
class Box:
    top: float
    left: float
    bottom: float
    right: float

    def moved(self, dy: float, dx: float) -> Box:
        return Box(self.top + dy, self.left + dx, self.bottom + dy, self.right + dx)

    def grown(self, dy: float) -> Box:
        return Box(self.top, self.left, self.bottom + dy, self.right)

    def union(self, other: Box) -> Box:
        return Box(
            min(self.top, other.top),
            min(self.left, other.left),
            max(self.bottom, other.bottom),
            max(self.right, other.right),
        )

    def overlaps(self, other: Box) -> bool:
        return (
            self.top < other.bottom and other.top < self.bottom and self.left < other.right and other.left < self.right
        )

    def tag(self) -> str:
        return f'<Bounds top="{num(self.top)}" left="{num(self.left)}" bottom="{num(self.bottom)}" right="{num(self.right)}"></Bounds>'


@dataclass
class Obj:
    start: int
    end: int
    xml: str
    id: str
    box: Box


def num(value: float) -> str:
    return str(int(value)) if value == int(value) else f"{value:g}"


def own_bounds(xml: str) -> Box:
    found = BOUNDS.search(xml)
    if not found:
        raise PatchworkError("Layout object without bounds.")
    return Box(*(float(v) for v in found.groups()))


def top_level(part: str, offset: int) -> list[Obj]:
    """Objects directly in a part (not inside button bars, portals or groups)."""
    found = []
    depth = None
    for match in OBJECT.finditer(part):
        indent = len(match.group(1))
        depth = indent if depth is None else min(depth, indent)
    for match in OBJECT.finditer(part):
        if len(match.group(1)) == depth:
            xml = match.group(0)
            ident = re.search(r'\sid="(\d+)"', xml[: xml.index(">")])
            found.append(
                Obj(offset + match.start(), offset + match.end(), xml, ident.group(1) if ident else "", own_bounds(xml))
            )
    return found


def field_target(export: Export, field: str) -> tuple[str, str, str, str]:
    """(field id, field name, field UUID, TableOccurrenceReference) for TO::Field."""
    occurrence, name = objects.split_field(field)
    to = objects.find(export, "table-occurrence", occurrence)
    base = re.search(r'<BaseTableReference [^>]*\bname="([^"]*)"', to.xml)
    if not base:
        raise PatchworkError(f"Table occurrence {occurrence} has no base table in the export.")
    field_id, field_uuid = export.field(unescape(base.group(1)), name)
    return field_id, name, field_uuid, export.table_occurrence(occurrence)


def place_field(
    export: Export, layout: str, field: str, near: str, label: str | None = None, side: str = "below"
) -> tuple[str, str]:
    """(whole new layout XML, field UUID). `near` is a field already on the layout, as Name or TO::Name."""
    block = export.layout(layout)
    xml = block.xml
    field_id, field_name, field_uuid, to_ref = field_target(export, field)
    near_name = near.split("::", 1)[-1]

    parts = list(re.finditer(r"<Part type=\"([^\"]*)\"[\s\S]*?</Part>", xml))
    for part in parts:
        objs = top_level(part.group(0), part.start())
        anchor = next(
            (
                o
                for o in objs
                if re.search(rf'<FieldReference [^>]*\bname="{re.escape(escape(near_name))}"', o.xml)
                and (near_name == near or f'name="{escape(near.split("::")[0])}"' in o.xml)
            ),
            None,
        )
        if anchor:
            break
    else:
        raise PatchworkError(
            f"No field {near!r} directly on layout {layout!r}. Name a field that is on it, e.g. one from `patchwork show layout`."
        )
    if re.search(rf'<FieldReference [^>]*\bUUID="{field_uuid}"', part.group(0)):
        raise PatchworkError(f"{field} is already on {layout!r}.")

    label_id = re.search(r"<Accessibility>\s*<Label>(\d+)</Label>", anchor.xml)
    caption = next((o for o in objs if label_id and o.id == label_id.group(1) and 'type="Text"' in o.xml[:200]), None)
    group = anchor.box.union(caption.box) if caption else anchor.box
    if side == "below":
        line = group.bottom - SLACK
        under = [
            o.box.top - group.bottom
            for o in objs
            if o.box.top >= line and o.box.left < group.right and group.left < o.box.right
        ]
        gap = min(under) if under and 0 <= min(under) <= 40 else GAP
        dy, dx = group.bottom - group.top + gap, 0.0
    elif side == "right":
        line, dy, dx = None, 0.0, group.right - group.left + GAP
    else:
        raise PatchworkError("side is below or right.")

    placed = group.moved(dy, dx)
    width = float(re.search(r'<Layout [^>]*\bwidth="([\d.]+)"', xml).group(1))
    if placed.right > width:
        raise PatchworkError(f"No room right of {near!r}: it would go past the edge of the layout. Use side=below.")
    staying = [o for o in objs if line is None or o.box.top < line]
    blocking = [o for o in staying if o.box.overlaps(placed) and not stretches(o)]
    if blocking:
        names = [re.search(r'<FieldReference [^>]*\bname="([^"]*)"', o.xml) for o in blocking]
        what = ", ".join(
            f"field {n.group(1)}" if n else f"object {o.id}" for n, o in zip(names, blocking, strict=False)
        )
        raise PatchworkError(
            f"No room {side} {near!r}: it would cover {what}. "
            f"Try side={'right' if side == 'below' else 'below'} or another field."
        )

    next_id = (
        max(
            (int(i) for i in re.findall(r'<LayoutObject [^>]*?\bid="(\d+)"', export.section("LayoutCatalog"))),
            default=0,
        )
        + 1
    )
    new_field = copy(anchor.xml, str(next_id), dy, dx)
    new_field = re.sub(
        r"<FieldReference [^>]*>[\s\S]*?</FieldReference>",
        f'<FieldReference id="{field_id}" name="{escape(field_name)}" repetition="1" UUID="{field_uuid}">'
        f"\n{indent_of(anchor.xml, 'TableOccurrenceReference')}{to_ref}\n{indent_of(anchor.xml, 'FieldReference')}</FieldReference>",
        new_field,
        count=1,
    )
    new_field = re.sub(r"\s*<TabOrder [\s\S]*?</TabOrder>", "", new_field)
    added = [new_field]
    if caption:
        text = escape_cdata(label if label is not None else field_name)
        new_caption = copy(caption.xml, str(next_id + 1), dy, dx)
        new_caption = re.sub(
            r"<Data><!\[CDATA\[[\s\S]*?\]\]></Data>", lambda _: f"<Data><![CDATA[{text}]]></Data>", new_caption, count=1
        )
        new_field = new_field.replace(f"<Label>{caption.id}</Label>", f"<Label>{next_id + 1}</Label>")
        added = [new_caption, new_field]

    edits = [(anchor.end, anchor.end, "".join(f"\n{a}" for a in added))]
    if line is not None:
        for o in objs:
            if o.box.top >= line:
                edits.append((o.start, o.end, shift(o.xml, dy)))
            elif o.box.bottom > line and stretches(o):
                edits.append(
                    (
                        o.start,
                        o.end,
                        BOUNDS.sub(lambda m: Box(*(float(v) for v in m.groups())).grown(dy).tag(), o.xml, count=1),
                    )
                )
        definition = re.search(r'<Definition [^>]*\bsize="([\d.]+)"', part.group(0))
        if definition:
            at = part.start() + definition.start(1)
            edits.append((at, at + len(definition.group(1)), num(float(definition.group(1)) + dy)))
        for later in parts[parts.index(part) + 1 :]:
            moved = BOUNDS.sub(lambda m: Box(*(float(v) for v in m.groups())).moved(dy, 0).tag(), later.group(0))
            moved = re.sub(
                r'(<Definition [^>]*\babsolute=")([\d.]+)',
                lambda m: m.group(1) + num(float(m.group(2)) + dy),
                moved,
                count=1,
            )
            edits.append((later.start(), later.end(), moved))
    for start, end, text in sorted(edits, key=lambda e: e[0], reverse=True):
        xml = xml[:start] + text + xml[end:]
    count = re.compile(r'(<ObjectList membercount=")(\d+)(">)')
    first = count.search(xml, part.start())
    xml = xml[: first.start(2)] + str(int(first.group(2)) + len(added)) + xml[first.end(2) :]
    return xml, field_uuid


def stretches(o: Obj) -> bool:
    """Background shapes grow with the row instead of moving."""
    return bool(re.match(r'\t*<LayoutObject [^>]*\btype="(Rectangle|Rounded Rectangle)"', o.xml))


def shift(xml: str, dy: float) -> str:
    return BOUNDS.sub(lambda m: Box(*(float(v) for v in m.groups())).moved(dy, 0).tag(), xml)


def copy(xml: str, new_id: str, dy: float, dx: float) -> str:
    head_end = xml.index(">")
    head = re.sub(r'\shash="[^"]*"', "", xml[:head_end])
    head = re.sub(r'\sid="\d+"', f' id="{new_id}"', head, count=1)
    body = objects.fresh_uuids(xml[head_end:])
    body = BOUNDS.sub(lambda m: Box(*(float(v) for v in m.groups())).moved(dy, dx).tag(), body)
    return head + body


def indent_of(xml: str, tag: str) -> str:
    found = re.search(rf"\n(\t*)<{tag}\b", xml)
    return found.group(1) if found else ""


def escape_cdata(text: str) -> str:
    if "]]>" in text:
        raise PatchworkError("The label cannot contain ']]>'.")
    return text
