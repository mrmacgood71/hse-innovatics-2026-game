import os
from pathlib import Path

SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60


def _resolve_asset_root() -> Path:
    override = os.environ.get("MERIDEX_ASSET_ROOT")
    if override:
        return Path(override).expanduser().resolve()

    package_dir = Path(__file__).resolve().parent
    candidates = (
        package_dir / "asset_data",
        package_dir.parents[1] / "assets",
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[-1]


ASSET_ROOT = _resolve_asset_root()

BG = (14, 18, 28)
PANEL = (27, 35, 51)
TEXT = (228, 233, 240)
ACCENT = (111, 196, 169)
WARN = (217, 126, 92)
ICE = (125, 173, 209)
ROUGH = (136, 119, 92)
