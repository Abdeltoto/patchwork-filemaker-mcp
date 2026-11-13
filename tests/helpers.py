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


class FakeTool:
    """Stands in for FMUpgradeTool + FMDeveloperTool. `effect(patch, text)` returns the export after each patch."""

    def __init__(self, effect=None):
        self.text = (FIXTURES / "mini-export.xml").read_text(encoding="utf-8")
        self.effect = effect or (lambda patch, text: text)
        self.patches = []

    def generate_guids(self, src, dest, force=False):
        shutil.copyfile(src, dest)

    def export_xml(self, src, out, force=False):
        out.write_text(self.text, encoding="utf-8")

    def apply(self, src, patch, dest, force=False):
        xml = patch.read_text(encoding="utf-8")
        self.patches.append(xml)
        self.text = self.effect(xml, self.text)
        shutil.copyfile(src, dest)
