import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
sys.path.insert(0, str(ROOT / "src"))

from patchwork.export import Export  # noqa: E402

TEAL = "rgba(0%,27.8431%,35.2941%,1)"


def mini_export() -> Export:
    return Export.load(FIXTURES / "mini-export.xml")
