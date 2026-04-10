from __future__ import annotations

from pathlib import Path

from meridex_alpha.constants import ASSET_ROOT


ASSET_REGISTRY: dict[str, Path] = {
    "hub_ground": ASSET_ROOT / "hub" / "ground.png",
    "hub_backdrop": ASSET_ROOT / "hub" / "backdrop.png",
    "player_idle": ASSET_ROOT / "characters" / "player_idle.png",
    "npc_field_lead": ASSET_ROOT / "characters" / "npc_field_lead.png",
    "npc_warehouse_chief": ASSET_ROOT / "characters" / "npc_warehouse_chief.png",
    "agro_field_tiles": ASSET_ROOT / "missions" / "agromonitoring" / "field_tiles.png",
    "agro_drone": ASSET_ROOT / "imports" / "top-down-tanks" / "tankBlue.png",
    "warehouse_tiles": ASSET_ROOT / "missions" / "warehouse" / "warehouse_tiles.png",
    "warehouse_robot": ASSET_ROOT / "missions" / "warehouse" / "robot.png",
    "warehouse_obstacle": ASSET_ROOT / "missions" / "warehouse" / "obstacle.png",
    "storm_overlay": ASSET_ROOT / "ui" / "storm_overlay.png",
}


def asset_path(key: str) -> Path:
    return ASSET_REGISTRY[key]
