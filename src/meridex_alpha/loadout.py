from __future__ import annotations

from collections.abc import Iterable

from meridex_alpha.models import ModuleDefinition, RobotProfile, STAT_NAMES

MIN_STAT = 1
MAX_STAT = 10

BASE_PROFILE = RobotProfile(
    endurance=5,
    mobility=5,
    armor=5,
    sensors=5,
    stability=5,
)

MODULE_CATALOG: dict[str, ModuleDefinition] = {
    "battery_pack": ModuleDefinition(
        key="battery_pack",
        name="Battery Pack",
        modifiers={"endurance": 3, "mobility": -1},
    ),
    "winter_traction": ModuleDefinition(
        key="winter_traction",
        name="Winter Traction",
        modifiers={"mobility": 2, "stability": 1},
    ),
    "reinforced_shell": ModuleDefinition(
        key="reinforced_shell",
        name="Reinforced Shell",
        modifiers={"armor": 3, "mobility": -1},
    ),
    "sensor_package": ModuleDefinition(
        key="sensor_package",
        name="Sensor Package",
        modifiers={"sensors": 3, "stability": -1},
    ),
    "stability_module": ModuleDefinition(
        key="stability_module",
        name="Stability Module",
        modifiers={"stability": 3, "mobility": -1},
    ),
}


def _clamp_stat(value: int) -> int:
    if value < MIN_STAT:
        return MIN_STAT
    if value > MAX_STAT:
        return MAX_STAT
    return value


def _validate_module_definition(module: ModuleDefinition) -> None:
    invalid_stat_names = [stat_name for stat_name in module.modifiers if stat_name not in STAT_NAMES]
    if invalid_stat_names:
        invalid_list = ", ".join(sorted(invalid_stat_names))
        raise ValueError(f"Module '{module.key}' has invalid modifiers: {invalid_list}")


def _validate_catalog() -> None:
    for module in MODULE_CATALOG.values():
        _validate_module_definition(module)


def calculate_robot_profile(module_keys: Iterable[str]) -> RobotProfile:
    selected_modules = tuple(module_keys)
    duplicate_keys = [module_key for index, module_key in enumerate(selected_modules) if module_key in selected_modules[:index]]
    if duplicate_keys:
        duplicate_list = ", ".join(dict.fromkeys(duplicate_keys))
        raise ValueError(f"Duplicate module keys: {duplicate_list}")

    unknown_keys = [module_key for module_key in selected_modules if module_key not in MODULE_CATALOG]
    if unknown_keys:
        unknown_list = ", ".join(dict.fromkeys(unknown_keys))
        raise ValueError(f"Unknown module keys: {unknown_list}")

    totals = {name: getattr(BASE_PROFILE, name) for name in STAT_NAMES}

    for module_key in selected_modules:
        module = MODULE_CATALOG[module_key]
        _validate_module_definition(module)
        for stat_name, modifier in module.modifiers.items():
            totals[stat_name] += modifier

    return RobotProfile(
        endurance=_clamp_stat(totals["endurance"]),
        mobility=_clamp_stat(totals["mobility"]),
        armor=_clamp_stat(totals["armor"]),
        sensors=_clamp_stat(totals["sensors"]),
        stability=_clamp_stat(totals["stability"]),
        selected_modules=selected_modules,
    )


_validate_catalog()
