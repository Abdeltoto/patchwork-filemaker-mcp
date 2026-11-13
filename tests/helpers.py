import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
sys.path.insert(0, str(ROOT / "src"))

from patchwork.export import Export  # noqa: E402

TEAL = "rgba(0%,27.8431%,35.2941%,1)"


def mini_export() -> Export:
    return Export.load(FIXTURES / "mini-export.xml")


def filemaker_effect(patch: str, text: str) -> str:
    """What FMUpgradeTool does with the patches Patchwork writes, for the shapes they take."""
    patch = patch.replace("\r\n", "\n")
    for ref in re.findall(r'<ItemReference UUID="([^"]*)" type="ScriptStepReference">', patch):
        text = re.sub(rf"\s*<Step [^>]*>\s*<UUID>{ref}</UUID>[\s\S]*?</Step>", "", text, count=1)
    for kind, uuid, body in re.findall(r'<Replace type="(\w+)" UUID="([^"]*)">\s*([\s\S]*?)\s*</Replace>', patch):
        own = re.compile(rf"<{kind} [^>]*>(?:(?!</{kind}>)[\s\S])*?<UUID>{uuid}</UUID>[\s\S]*?</{kind}>")
        text = own.sub(lambda _, body=body: body, text, count=1)
    add = re.search(r"<AddAction>([\s\S]*?)</AddAction>", patch)
    if not add:
        return text
    add_text = add.group(1)
    fields = re.search(r"<FieldsForTables[\s\S]*?<ObjectList[^>]*>([\s\S]*?)</ObjectList>", add_text)
    if fields:
        table = re.search(r'<BaseTableReference [^>]*UUID="([^"]*)"', add_text).group(1)
        start = text.index(f'UUID="{table}"', text.index("<FieldsForTables"))
        end = text.index("</ObjectList>", start)
        text = text[:end] + fields.group(1) + text[end:]
    for catalog, item in (
        ("ScriptCatalog", "Script"),
        ("ValueListCatalog", "ValueList"),
        ("CustomFunctionsCatalog", "CustomFunction"),
    ):
        block = re.search(rf"<{catalog}[^>]*>([\s\S]*?)</{catalog}>", add_text)
        if block:
            items = "".join(re.findall(rf"<{item} [\s\S]*?</{item}>", block.group(1)))
            end = (
                text.index(f"</{catalog}>")
                if catalog != "CustomFunctionsCatalog"
                else text.index("</ObjectList>", text.index(f"<{catalog}"))
            )
            text = text[:end] + items + text[end:]
    for reference, script_ref, steps in re.findall(
        r'<Script>\s*(<ScriptReference [^>]*UUID="([^"]*)"></ScriptReference>)\s*<ObjectList[^>]*>([\s\S]*?)</ObjectList>',
        add_text,
    ):
        owner = re.search(
            rf'<Script>\s*<ScriptReference [^>]*UUID="{script_ref}"></ScriptReference>\s*<ObjectList[^>]*>[\s\S]*?(</ObjectList>)',
            text,
        )
        if owner:
            text = text[: owner.start(1)] + steps + text[owner.start(1) :]
        else:
            block = f'<Script>{reference}<ObjectList membercount="1">{steps}</ObjectList></Script>'
            end = text.index("</StepsForScripts>")
            text = text[:end] + block + text[end:]
    return text


class FakeTool:
    """Stands in for FMUpgradeTool + FMDeveloperTool. `effect(patch, text)` returns the export after each patch.

    Like the real tools, each .fmp12 keeps its own content: a patch applies to the export of its source file.
    """

    def __init__(self, effect=None):
        self.text = (FIXTURES / "mini-export.xml").read_text(encoding="utf-8")
        self.effect = effect or (lambda patch, text: text)
        self.patches = []
        self.files: dict[Path, str] = {}

    def content(self, path):
        return self.files.get(Path(path).resolve(), self.text)

    def generate_guids(self, src, dest, force=False):
        shutil.copyfile(src, dest)
        self.files[Path(dest).resolve()] = self.content(src)

    def export_xml(self, src, out, force=False):
        out.write_text(self.content(src), encoding="utf-8")

    def apply(self, src, patch, dest, force=False):
        xml = patch.read_text(encoding="utf-8")
        self.patches.append(xml)
        self.text = self.effect(xml, self.content(src))
        self.files[Path(dest).resolve()] = self.text
        shutil.copyfile(src, dest)
