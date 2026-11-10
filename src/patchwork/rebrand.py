"""Rebrand a whole FileMaker solution from one brand.json file.

Pipeline, every step on a new copy:
  guids -> export -> [logo field + theme] patch -> export -> layouts patch -> export -> verify
"""

from __future__ import annotations

import json
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from patchwork import PatchworkError
from patchwork.build import add_field_action, field_xml, image_calc, layouts_patch, normalize_hex, split_field, theme_replace, wrap
from patchwork.export import Export
from patchwork.tools import Runner, require_copy, require_source


@dataclass
class Logo:
    image: Path
    replace: str
    field: str = "Brand Logo"
    width: int | None = None


@dataclass
class Brand:
    name: str
    colors: dict[str, str] = field(default_factory=dict)
    fonts: dict[str, str] = field(default_factory=dict)
    theme: str | None = None
    logo: Logo | None = None

    @classmethod
    def load(cls, path: Path) -> "Brand":
        if not path.is_file():
            raise PatchworkError(f"Brand file not found: {path}")
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise PatchworkError(f"{path.name} is not valid JSON: {exc}") from exc
        return cls.from_dict(data, path.parent)

    @classmethod
    def from_dict(cls, data: dict, base: Path) -> "Brand":
        unknown = set(data) - {"$schema", "name", "colors", "fonts", "theme", "logo"}
        if unknown:
            raise PatchworkError(f"Unknown key(s) in brand file: {', '.join(sorted(unknown))}")
        if not data.get("name"):
            raise PatchworkError('The brand file needs a "name": it becomes the theme name.')
        colors = {normalize_hex(k): normalize_hex(v) for k, v in data.get("colors", {}).items()}
        logo = None
        if data.get("logo"):
            spec = data["logo"]
            if not spec.get("image") or not spec.get("replace"):
                raise PatchworkError('"logo" needs "image" (a PNG) and "replace" (Table::Field shown on layouts).')
            split_field(spec["replace"])
            logo = Logo(
                image=(base / spec["image"]).resolve(),
                replace=spec["replace"],
                field=spec.get("field", "Brand Logo"),
                width=spec.get("width"),
            )
            if not logo.image.is_file():
                raise PatchworkError(f"Logo image not found: {logo.image}")
        return cls(data["name"], colors, data.get("fonts", {}), data.get("theme"), logo)


@dataclass
class Report:
    theme: str
    layouts: list[str]
    logo_refs: int | None
    work: Path


def rebrand(
    src: Path,
    dest: Path,
    brand: Brand,
    runner: Runner,
    force: bool = False,
    keep_work: bool = False,
    say=print,
) -> Report:
    src = require_source(src)
    dest = require_copy(src, dest, force)
    work = Path(tempfile.mkdtemp(prefix="patchwork-"))
    try:
        say(f"1/5  Giving every object a UUID          ({src.name})")
        current = work / "0-guids.fmp12"
        runner.generate_guids(src, current)
        export = export_of(runner, current, work / "0.xml")

        theme = brand.theme or export.main_theme()
        theme_block = export.theme(theme)
        say(f"2/5  Rewriting theme {theme_block.name!r} as {brand.name!r}" + (" + adding the logo field" if brand.logo else ""))
        actions = []
        if brand.logo:
            table, _ = split_field(brand.logo.replace)
            export.field(*split_field(brand.logo.replace))
            calc = image_calc(brand.logo.image, brand.logo.width)
            fxml = field_xml(export, table, brand.logo.field, "Container", f"{brand.name} logo, added by Patchwork", True, calc)
            actions.append(add_field_action(export, table, fxml))
        actions.append(theme_replace(export, theme, brand.name, brand.colors, brand.fonts))
        current = step(runner, current, wrap(*actions, version=export.version), work / "1-theme")
        export = export_of(runner, current, work / "1.xml")

        say("3/5  Rewriting the layouts that change")
        remap = None
        if brand.logo:
            table, _ = split_field(brand.logo.replace)
            remap = (brand.logo.replace, f"{table}::{brand.logo.field}")
        patch, names = layouts_patch(export, None, brand.colors, brand.fonts, remap)
        if names:
            current = step(runner, current, patch, work / "2-layouts")
        say(f"     {len(names)} layout(s) rewritten")

        say("4/5  Checking the result")
        export = export_of(runner, current, work / "final.xml")
        displays = [display for display, _, _ in export.themes()]
        if brand.name not in displays:
            raise PatchworkError(f"FMUpgradeTool reported success but theme {brand.name!r} is missing. Work kept in {work}")
        logo_refs = None
        if brand.logo:
            table, _ = split_field(brand.logo.replace)
            _, logo_uuid = export.field(table, brand.logo.field)
            logo_refs = export.field_references(logo_uuid)

        say(f"5/5  Writing {dest.name}")
        if dest.exists():
            dest.unlink()
        shutil.copy2(current, dest)
        return Report(brand.name, names, logo_refs, work)
    finally:
        if not keep_work:
            shutil.rmtree(work, ignore_errors=True)


def export_of(runner: Runner, fmp12: Path, xml: Path) -> Export:
    runner.export_xml(fmp12, xml, force=True)
    return Export.load(xml)


def step(runner: Runner, current: Path, patch: str, stem: Path) -> Path:
    patch_file = stem.with_suffix(".xml")
    patch_file.write_text(patch, encoding="utf-8")
    result = stem.with_suffix(".fmp12")
    runner.apply(current, patch_file, result)
    return result
