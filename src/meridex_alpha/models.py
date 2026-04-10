from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

STAT_NAMES = ("endurance", "mobility", "armor", "sensors", "stability")


@dataclass(frozen=True, slots=True)
class ModuleDefinition:
    key: str
    name: str
    modifiers: Mapping[str, int]


@dataclass(frozen=True, slots=True)
class RobotProfile:
    endurance: int
    mobility: int
    armor: int
    sensors: int
    stability: int
    selected_modules: tuple[str, ...] = ()
