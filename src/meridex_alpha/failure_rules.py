from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from meridex_alpha.mission import MissionRuntime


@dataclass(frozen=True, slots=True)
class RecoveryAction:
    key: str
    label: str
    summary: str


@dataclass(frozen=True, slots=True)
class FailureIssue:
    key: str
    title: str
    summary: str
    recovery_actions: tuple[RecoveryAction, ...]


SENSOR_WHITEOUT = FailureIssue(
    key="sensor_whiteout",
    title="Sensor Whiteout",
    summary="Icing and signal distortion are overwhelming the robot's current calibration.",
    recovery_actions=(
        RecoveryAction("recalibrate_sensors", "Recalibrate Sensors", "Refocus the sensor stack for low-visibility navigation."),
        RecoveryAction("route_reserve_power", "Route Reserve Power", "Push reserve power into the control bus to steady telemetry."),
        RecoveryAction("deploy_stabilizers", "Deploy Stabilizers", "Reduce drift by widening the chassis stability envelope."),
    ),
)

FAILURES_BY_KEY = {
    SENSOR_WHITEOUT.key: SENSOR_WHITEOUT,
}


def get_failure_issue(issue_key: str | None) -> FailureIssue | None:
    if issue_key is None:
        return None
    return FAILURES_BY_KEY.get(issue_key)


def evaluate_failure(runtime: MissionRuntime) -> FailureIssue | None:
    harsh_environment = runtime.last_environment_multiplier <= 0.72
    unstable_build = runtime.effective_sensors <= 5 and runtime.effective_stability <= 5
    unstable_control = runtime.last_control_quality < 0.6
    prolonged_exposure = runtime.hazard_exposure >= 3.0

    if harsh_environment and unstable_build and unstable_control and prolonged_exposure:
        return SENSOR_WHITEOUT
    return None


def apply_recovery_action(runtime: MissionRuntime, action_key: str) -> str:
    if action_key == "recalibrate_sensors":
        runtime.sensor_calibration_bonus += 2
        runtime.hazard_exposure = max(0.0, runtime.hazard_exposure - 1.8)
        runtime.active_failure_key = None
        runtime.refresh_status()
        return "Sensors recalibrated for low-visibility travel."

    if action_key == "route_reserve_power":
        runtime.reserve_power_routed = True
        runtime.battery_level = min(runtime.battery_capacity, runtime.battery_level + 6.0)
        runtime.hazard_exposure = max(0.0, runtime.hazard_exposure - 1.0)
        runtime.active_failure_key = None
        runtime.refresh_status()
        return "Reserve power routed into the control bus."

    if action_key == "deploy_stabilizers":
        runtime.stability_bonus += 2
        runtime.hazard_exposure = max(0.0, runtime.hazard_exposure - 1.4)
        runtime.active_failure_key = None
        runtime.refresh_status()
        return "Stabilizers deployed to contain drift."

    raise ValueError(f"Unknown recovery action: {action_key}")
