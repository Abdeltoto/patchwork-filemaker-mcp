"""Build FMUpgradeTool patches (root element FMUpgradeToolPatch) from an Export.

Rules learned on real files, all enforced here:
- Replace a whole layout or a whole theme. A lone LayoutObject replace, a ReplaceAction
  around a LayoutCatalog and an AddAction of a new theme are skipped by FMUpgradeTool.
- An added field needs membercount="1", a <TagList> after the catalog UUID, and id = max + 1.
- A FieldReference in a layout may carry repetition="1"; it must be kept.
"""

from __future__ import annotations

import base64
import io
import re
import uuid
from pathlib import Path

from patchwork import PatchworkError
from patchwork.export import Export, escape

PATCH_VERSION = "2.3.0.0"
CALC_MAX_CHARS = 28000
RGBA = re.compile(r"rgba\(([\d.]+)%,([\d.]+)%,([\d.]+)%,([\d.]+)\)")
FIELD_TYPES = {
    "Text": "Text",
    "Number": "Number",
    "Date": "Date",
    "Time": "Time",
    "Timestamp": "TimeStamp",
    "Container": "Binary",
}


def recolor(css: str, colors: dict[str, str]) -> str:
    """Swap hex colors inside FileMaker rgba(r%,g%,b%,a) values. Alpha is kept."""
    table = {normalize_hex(k): normalize_hex(v) for k, v in colors.items()}
    if not table:
        return css

    def repl(match: re.Match) -> str:
        rgb = "".join(f"{round(float(match.group(i)) * 2.55):02X}" for i in (1, 2, 3))
        new = table.get(rgb)
        if not new:
            return match.group(0)
        parts = [int(new[i : i + 2], 16) / 255 * 100 for i in (0, 2, 4)]
        values = ",".join(f"{p:.4f}".rstrip("0").rstrip(".") + "%" for p in parts)
        return f"rgba({values},{match.group(4)})"

    return RGBA.sub(repl, css)


def palette(css: str) -> list[tuple[str, int]]:
    """Hex colors used in a block of FileMaker CSS, most frequent first."""
    found = ["".join(f"{round(float(m.group(i)) * 2.55):02X}" for i in (1, 2, 3)) for m in RGBA.finditer(css)]
    counts: dict[str, int] = {}
    for color in found:
        counts[color] = counts.get(color, 0) + 1
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))


def palette(css: str) -> list[tuple[str, int]]:
    """Hex colors used in a block of FileMaker CSS, most frequent first."""
    found = ["".join(f"{round(float(m.group(i)) * 2.55):02X}" for i in (1, 2, 3)) for m in RGBA.finditer(css)]
    counts: dict[str, int] = {}
    for color in found:
        counts[color] = counts.get(color, 0) + 1
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))


def normalize_hex(value: str) -> str:
    value = value.strip().lstrip("#").upper()
    if not re.fullmatch(r"[0-9A-F]{6}", value):
        raise PatchworkError(f"Color must be a 6-digit hex value like 2F5D50: {value}")
    return value


def remap_fonts(css: str, fonts: dict[str, str]) -> str:
    """Fonts are written -fm-font-family(WindowsName,MacPostScriptName)."""
    for old, new in fonts.items():
        css = css.replace(f"-fm-font-family({old})", f"-fm-font-family({new})")
    return css


def wrap(*actions: str, version: str = PATCH_VERSION) -> str:
    """The patch version must equal the FMSaveAsXML version of the export it was built from."""
    body = "".join(a for a in actions if a)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<FMUpgradeToolPatch version="{version}">\n\t<Structure>\n'
        f"{body}\t</Structure>\n</FMUpgradeToolPatch>\n"
    )


def replace_action(blocks: list[tuple[str, str, str]]) -> str:
    """blocks: (type, UUID, XML) for each Replace."""
    if not blocks:
        return ""
    inner = "".join(
        f'\t\t\t<Replace type="{kind}" UUID="{uid}">\n{xml}\n\t\t\t</Replace>\n' for kind, uid, xml in blocks
    )
    return f"\t\t<ReplaceAction>\n{inner}\t\t</ReplaceAction>\n"


def field_xml(
    export: Export,
    table: str,
    name: str,
    kind: str = "Text",
    comment: str = "",
    is_global: bool = False,
    calc: str | None = None,
    context: str | None = None,
) -> str:
    if kind not in FIELD_TYPES:
        raise PatchworkError(f"Unknown field type: {kind}. Choose from {', '.join(FIELD_TYPES)}.")
    if export.has_field(table, name):
        raise PatchworkError(f"{table}::{name} already exists.")
    field_id = export.next_field_id(table)
    head = (
        f'<Field id="{field_id}" name="{escape(name)}" fieldtype="{"Calculated" if calc else "Normal"}" '
        f'datatype="{FIELD_TYPES[kind]}" comment="{escape(comment)}">\n'
        f"\t<UUID>{new_uuid()}</UUID>\n"
    )
    language = '\t\t<LanguageReference name="English" id="21"></LanguageReference>\n'
    flag = "True" if is_global else "False"
    if calc:
        if len(calc) > CALC_MAX_CHARS:
            raise PatchworkError(
                f"Calculation too long ({len(calc)} characters, max {CALC_MAX_CHARS}). "
                "For an image, pass a smaller width."
            )
        occurrence = export.table_occurrence(context or table)
        body = (
            '\t<AutoEnter alwaysEvaluate="False"></AutoEnter>\n'
            f'\t<Storage storeCalculationResults="True" global="{flag}" maxRepetitions="1">\n{language}\t</Storage>\n'
            f"\t<Calculation>\n\t\t{occurrence}\n\t\t<Text><![CDATA[{calc}]]></Text>\n\t</Calculation>\n"
        )
    else:
        storage = (
            f'\t<Storage global="{flag}" maxRepetitions="1"></Storage>\n'
            if kind == "Container"
            else f'\t<Storage autoIndex="True" index="None" global="{flag}" maxRepetitions="1">\n{language}\t</Storage>\n'
        )
        body = (
            '\t<AutoEnter type="" prohibitModification="False"></AutoEnter>\n'
            '\t<Validation alwaysValidate="False" type="OnlyDuringDataEntry" allowOverride="True" '
            'notEmpty="False" unique="False" existing="False"></Validation>\n'
            f"{storage}"
        )
    return (
        head
        + body
        + '\t<TagList></TagList>\n\t<Annotation></Annotation>\n\t<DisplayNames enable="False"></DisplayNames>\n</Field>\n'
    )


def add_field_action(export: Export, table: str, field: str) -> str:
    catalog_uuid, base_ref, _ = export.field_catalog(table)
    return (
        "\t\t<AddAction>\n"
        '\t\t\t<FieldsForTables membercount="1">\n'
        f"\t\t\t\t<FieldCatalog>\n\t\t\t\t\t<UUID>{catalog_uuid}</UUID>\n"
        "\t\t\t\t\t<TagList></TagList>\n"
        f"\t\t\t\t\t{base_ref}\n"
        f'\t\t\t\t\t<ObjectList membercount="1">\n{field}\t\t\t\t\t</ObjectList>\n'
        "\t\t\t\t</FieldCatalog>\n\t\t\t</FieldsForTables>\n"
        "\t\t</AddAction>\n"
    )


def add_field_patch(export: Export, table: str, field: str) -> str:
    return wrap(add_field_action(export, table, field), version=export.version)


def image_calc(png: Path, width: int | None = None) -> str:
    """A calculation that turns an embedded PNG into container data."""
    if not png.is_file():
        raise PatchworkError(f"Image not found: {png}")
    data = png.read_bytes()
    if width:
        try:
            from PIL import Image
        except ImportError as exc:
            raise PatchworkError('Resizing an image needs Pillow: pip install "filemaker-patchwork[image]"') from exc
        img = Image.open(png).convert("RGBA")
        img = img.resize((width, round(img.height * width / img.width)), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, "PNG", optimize=True)
        data = buf.getvalue()
    encoded = base64.b64encode(data).decode("ascii")
    return f'Base64Decode ( "{encoded}" ; "{png.stem}.png" )'


def theme_replace(export: Export, label: str, rename: str | None, colors: dict, fonts: dict) -> str:
    theme = export.theme(label)
    xml = recolor(remap_fonts(theme.xml, fonts), colors)
    if rename:
        xml = re.sub(r'Display="[^"]*"', f'Display="{escape(rename)}"', xml, count=1)
    return replace_action([("Theme", theme.uuid, xml)])


def theme_patch(export: Export, label: str, rename: str | None, colors: dict, fonts: dict) -> str:
    return wrap(theme_replace(export, label, rename, colors, fonts), version=export.version)


def layouts_patch(
    export: Export,
    only: list[str] | None = None,
    colors: dict | None = None,
    fonts: dict | None = None,
    remap: tuple[str, str] | None = None,
) -> tuple[str, list[str]]:
    """Rewrite only the layouts that change. Returns (patch, names of changed layouts)."""
    colors, fonts = colors or {}, fonts or {}
    pattern = target = None
    if remap:
        (src_table, src_name), (dst_table, dst_name) = split_field(remap[0]), split_field(remap[1])
        if src_table != dst_table:
            raise PatchworkError("A field can only be swapped for another field of the same table.")
        _, src_uuid = export.field(src_table, src_name)
        dst_id, dst_uuid = export.field(dst_table, dst_name)
        pattern = re.compile(rf'<FieldReference id="\d+" name="[^"]*"( repetition="\d+")? UUID="{src_uuid}">')
        target = rf'<FieldReference id="{dst_id}" name="{escape(dst_name)}"\1 UUID="{dst_uuid}">'
    if only:
        known = {layout.name for layout in export.layouts()}
        missing = [name for name in only if name not in known]
        if missing:
            raise PatchworkError(f"Layout not found: {', '.join(missing)}")
    blocks, names = [], []
    for layout in export.layouts():
        if only and layout.name not in only:
            continue
        xml = recolor(remap_fonts(layout.xml, fonts), colors)
        if pattern:
            xml = pattern.sub(target, xml)
        if xml != layout.xml:
            blocks.append(("Layout", layout.uuid, xml))
            names.append(layout.name)
    return wrap(replace_action(blocks), version=export.version), names


def extract_layout_patch(export: Export, name: str) -> str:
    layout = export.layout(name)
    return wrap(replace_action([("Layout", layout.uuid, layout.xml)]), version=export.version)


def split_field(qualified: str) -> tuple[str, str]:
    if "::" not in qualified:
        raise PatchworkError(f"Expected a field as Table::Field, got: {qualified}")
    table, name = qualified.split("::", 1)
    return table, name


def new_uuid() -> str:
    return str(uuid.uuid4()).upper()
