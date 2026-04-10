from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MissionStormProfile:
    applies: bool
    warning_text: str
    effects_text: str


@dataclass(frozen=True, slots=True)
class MissionOption:
    key: str
    title: str
    summary: str
    storm: MissionStormProfile | None = None


_MISSION_OPTIONS_BY_NPC: dict[str, tuple[MissionOption, ...]] = {
    "agri_lead": (
        MissionOption(
            key="agromonitoring",
            title="Агромониторинг",
            summary="Построй корректную схему покрытия поля.",
            storm=MissionStormProfile(
                applies=True,
                warning_text="Штормовой протокол: погода ухудшит стабильность выполнения задания.",
                effects_text="Во время шторма запас по ошибкам меньше. Безопасный режим даст больше свободы.",
            ),
        ),
    ),
    "warehouse_chief": (
        MissionOption(
            key="warehouse_pressure",
            title="Склад под давлением",
            summary="Доведи платформу до зоны разгрузки без аварий.",
            storm=MissionStormProfile(
                applies=True,
                warning_text="Штормовой протокол: скольжение и помехи усложнят маневрирование на складе.",
                effects_text="Шторм усиливает инерцию. Безопасный режим снижает темп, но делает платформу стабильнее.",
            ),
        ),
    ),
}


def mission_options_for_npc(npc_key: str) -> tuple[MissionOption, ...]:
    return _MISSION_OPTIONS_BY_NPC.get(npc_key, ())


def mission_option_for_key(mission_key: str) -> MissionOption | None:
    for options in _MISSION_OPTIONS_BY_NPC.values():
        for option in options:
            if option.key == mission_key:
                return option
    return None
