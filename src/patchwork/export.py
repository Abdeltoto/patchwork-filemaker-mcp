"""Read-only view of a FileMaker Save-as-XML export (root element FMSaveAsXML).

Every identifier a patch needs (catalog UUID, base table, table occurrence, layout UUID,
theme UUID, next field id) is read from here, so a patch always matches the file it targets.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from patchwork import PatchworkError

GUIDS_HINT = "Run `patchwork guids` on the file first, then export it again."


@dataclass
class Block:
    name: str
    uuid: str
    xml: str


class Export:
    def __init__(self, text: str) -> None:
        if "<FMSaveAsXML" not in text[:2000]:
            raise PatchworkError("This is not a FileMaker Save-as-XML export (root FMSaveAsXML).")
        self.text = text
        head = re.search(r"<FMSaveAsXML[^>]*>", text[:2000])
        self.version = (attr(head.group(0), "version") if head else None) or "2.3.0.0"

    @classmethod
    def load(cls, path: Path) -> "Export":
        if not path.is_file():
            raise PatchworkError(f"Export not found: {path}")
        raw = path.read_bytes()
        if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
            return cls(raw.decode("utf-16"))
        return cls(raw.decode("utf-8-sig"))

    def section(self, tag: str) -> str:
        start = self.text.find(f"<{tag}")
        end = self.text.find(f"</{tag}>", start)
        if start < 0 or end < 0:
            raise PatchworkError(f"The export has no <{tag}> section.")
        return self.text[start:end]

    def layouts(self) -> list[Block]:
        catalog = self.section("LayoutCatalog")
        found = []
        for match in re.finditer(r'<Layout id="\d+" name="([^"]*)"[^>]*>[\s\S]*?</Layout>', catalog):
            block = match.group(0)
            found.append(Block(unescape(match.group(1)), layout_uuid(block), block))
        return found

    def layout(self, name: str) -> Block:
        for block in self.layouts():
            if block.name == name:
                return block
        raise PatchworkError(f"Layout not found: {name}")

    def themes(self) -> list[tuple[str, str, str]]:
        """(display name, internal name, UUID or empty) for each theme in the file."""
        found = []
        for match in re.finditer(r"<Theme [^>]*>[\s\S]*?</Theme>", self.section("ThemeCatalog")):
            block = match.group(0)
            head = block[: block.index(">") + 1]
            uid = re.search(r"<UUID[^>]*>([^<]*)</UUID>", block)
            found.append((attr(head, "Display") or "", attr(head, "name") or "", uid.group(1).strip() if uid else ""))
        return found

    def theme(self, label: str) -> Block:
        for match in re.finditer(r"<Theme [^>]*>[\s\S]*?</Theme>", self.section("ThemeCatalog")):
            block = match.group(0)
            head = block[: block.index(">") + 1]
            display, internal = attr(head, "Display"), attr(head, "name")
            if label not in (display, internal):
                continue
            found = re.search(r"<UUID[^>]*>([^<]*)</UUID>", block)
            if not found or not found.group(1).strip():
                raise PatchworkError(f"Theme {label} has no UUID. {GUIDS_HINT}")
            return Block(display or internal or label, found.group(1), block)
        raise PatchworkError(f"Theme not found: {label}")

    def main_theme(self) -> str:
        """Internal name of the theme used by the most layouts."""
        names = re.findall(r'<LayoutThemeReference [^>]*name="([^"]*)"', self.section("LayoutCatalog"))
        if not names:
            raise PatchworkError("No layout references a theme. Pass the theme name explicitly.")
        return Counter(names).most_common(1)[0][0]

    def field_catalog(self, table: str) -> tuple[str, str, str]:
        """(catalog UUID, BaseTableReference tag, catalog XML) for a base table."""
        fields = self.section("FieldsForTables")
        ref = re.search(
            rf'<BaseTableReference id="\d+" name="{re.escape(escape(table))}" UUID="[^"]+"></BaseTableReference>',
            fields,
        )
        if not ref:
            raise PatchworkError(f"Base table not found: {table}")
        start = fields.rfind("<FieldCatalog", 0, ref.start())
        end = fields.find("</FieldCatalog>", ref.end())
        catalog = fields[start:end]
        found = re.search(r"<UUID[^>]*>([^<]+)</UUID>", catalog)
        if not found:
            raise PatchworkError(f"The field catalog of {table} has no UUID. {GUIDS_HINT}")
        return found.group(1), ref.group(0), catalog

    def field(self, table: str, name: str) -> tuple[str, str]:
        """(id, UUID) of an existing field."""
        _, _, catalog = self.field_catalog(table)
        found = re.search(
            rf'<Field id="(\d+)" name="{re.escape(escape(name))}"[^>]*>\s*<UUID[^>]*>([^<]+)</UUID>', catalog
        )
        if not found:
            raise PatchworkError(f"Field not found: {table}::{name}")
        return found.group(1), found.group(2)

    def has_field(self, table: str, name: str) -> bool:
        return f'name="{escape(name)}"' in self.field_catalog(table)[2]

    def next_field_id(self, table: str) -> int:
        _, _, catalog = self.field_catalog(table)
        ids = [int(i) for i in re.findall(r'<Field id="(\d+)"', catalog)]
        return max(ids, default=0) + 1

    def table_occurrence(self, name: str) -> str:
        found = re.search(
            rf'<TableOccurrenceReference id="\d+" name="{re.escape(escape(name))}" UUID="[^"]+"></TableOccurrenceReference>',
            self.text,
        )
        if not found:
            raise PatchworkError(f"Table occurrence not found: {name}")
        return found.group(0)

    def field_references(self, field_uuid: str) -> int:
        return len(re.findall(rf'<FieldReference [^>]*UUID="{re.escape(field_uuid)}"', self.section("LayoutCatalog")))


def attr(tag: str, name: str) -> str | None:
    found = re.search(rf'\s{name}="([^"]*)"', tag)
    return unescape(found.group(1)) if found else None


def layout_uuid(block: str) -> str:
    """The layout's own UUID: the direct child of <Layout>, not the first <UUID> (an object's)."""
    indent = re.search(r"\n(\t+)<", block)
    if not indent:
        raise PatchworkError("Layout block without children.")
    found = re.search(rf"\n{indent.group(1)}<UUID[^>]*>([^<]+)</UUID>", block)
    if not found:
        raise PatchworkError(f"Layout UUID not found. {GUIDS_HINT}")
    return found.group(1)


def escape(value: str) -> str:
    return value.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;")


def unescape(value: str) -> str:
    return value.replace("&lt;", "<").replace("&quot;", '"').replace("&amp;", "&")
