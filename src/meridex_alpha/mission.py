from __future__ import annotations

from dataclasses import dataclass, field
from math import hypot
from typing import TYPE_CHECKING

from meridex_alpha.models import RobotProfile

if TYPE_CHECKING:
    from meridex_alpha.failure_rules import FailureIssue

Position = tuple[float, float]


def _clamp(value: float, lower: float, upper: float) -> float:
    if value < lower:
        return lower
    if value > upper:
        return upper
    return value


def _distance(start: Position, end: Position) -> float:
    return hypot(end[0] - start[0], end[1] - start[1])


def _distance_to_segment(point: Position, start: Position, end: Position) -> float:
    segment_dx = end[0] - start[0]
    segment_dy = end[1] - start[1]
    segment_length_squared = segment_dx * segment_dx + segment_dy * segment_dy
    if segment_length_squared == 0.0:
        return _distance(point, start)

    projection = ((point[0] - start[0]) * segment_dx + (point[1] - start[1]) * segment_dy) / segment_length_squared
    projection = _clamp(projection, 0.0, 1.0)
    closest_point = (start[0] + segment_dx * projection, start[1] + segment_dy * projection)
    return _distance(point, closest_point)


@dataclass(frozen=True, slots=True)
class EnvironmentZone:
    left: float
    top: float
    width: float
    height: float
    control_multiplier: float = 0.8
    battery_multiplier: float = 1.0

    def contains(self, position: Position) -> bool:
        x, y = position
        return self.left <= x <= self.left + self.width and self.top <= y <= self.top + self.height


@dataclass(slots=True)
class MissionRuntime:
    profile: RobotProfile
    robot_position: Position = (96.0, 192.0)
    relay_position: Position = (684.0, 192.0)
    environment_zones: tuple[EnvironmentZone, ...] = ()
    arena_size: Position = (780.0, 360.0)
    relay_radius: float = 18.0
    battery_capacity: float = field(init=False)
    battery_level: float = field(init=False)
    last_control_quality: float = field(init=False)
    last_environment_multiplier: float = field(init=False)
    last_battery_multiplier: float = field(init=False)
    hazard_exposure: float = 0.0
    sensor_calibration_bonus: int = 0
    stability_bonus: int = 0
    reserve_power_routed: bool = False
    active_failure_key: str | None = None
    objective_complete: bool = False
    mission_success: bool = False

    def __post_init__(self) -> None:
        self.battery_capacity = 40.0 + self.profile.endurance * 8.0
        self.battery_level = self.battery_capacity
        self.refresh_status()
        self._sync_objective_state()

    @property
    def module_load(self) -> int:
        return len(self.profile.selected_modules)

    @property
    def effective_sensors(self) -> int:
        return self.profile.sensors + self.sensor_calibration_bonus

    @property
    def effective_stability(self) -> int:
        return self.profile.stability + self.stability_bonus

    @property
    def control_support_bonus(self) -> float:
        return 0.05 if self.reserve_power_routed else 0.0

    def refresh_status(self) -> None:
        self.last_environment_multiplier = self.environment_multiplier_at(self.robot_position)
        self.last_battery_multiplier = self.battery_multiplier_at(self.robot_position)
        self.last_control_quality = self.control_quality_at(self.robot_position)

    def environment_multiplier_at(self, position: Position) -> float:
        multiplier = 1.0
        for zone in self.environment_zones:
            if zone.contains(position):
                multiplier = min(multiplier, zone.control_multiplier)
        return multiplier

    def battery_multiplier_at(self, position: Position) -> float:
        multiplier = 1.0
        for zone in self.environment_zones:
            if zone.contains(position):
                if zone.battery_multiplier < 1.0:
                    multiplier = min(multiplier, zone.battery_multiplier)
                elif zone.battery_multiplier > 1.0:
                    multiplier = max(multiplier, zone.battery_multiplier)
        return multiplier

    def control_quality_at(self, position: Position) -> float:
        stat_total = self.profile.mobility + self.effective_sensors + self.effective_stability
        base_quality = 0.45 + (stat_total / 30.0) * 0.4
        armor_buffer = 1.0 + min(0.12, self.profile.armor * 0.01)
        module_load_penalty = min(0.18, self.module_load * 0.03)
        quality = base_quality * armor_buffer * self.environment_multiplier_at(position) - module_load_penalty + self.control_support_bonus
        return _clamp(quality, 0.25, 1.0)

    def battery_drain_rate(self, control_quality: float, battery_multiplier: float = 1.0) -> float:
        base_drain = 0.55 + self.module_load * 0.08
        unstable_penalty = (1.0 - control_quality) * 0.8
        resilience_discount = min(0.45, (self.profile.endurance + self.profile.stability + self.profile.armor) * 0.015)
        return max(0.12, base_drain + unstable_penalty - resilience_discount) * battery_multiplier

    def battery_drain_amount(self, movement_distance: float, dt: float, control_quality: float, battery_multiplier: float = 1.0) -> float:
        movement_cost = movement_distance * 0.018 * battery_multiplier
        return self.battery_drain_rate(control_quality, battery_multiplier) * dt + movement_cost

    def step(self, input_vector: Position, dt: float) -> None:
        if dt <= 0.0:
            return

        previous_position = self.robot_position
        current_quality = self.control_quality_at(self.robot_position)
        self.refresh_status()

        if self.objective_complete:
            self.battery_level = max(0.0, self.battery_level - self.battery_drain_rate(current_quality, self.last_battery_multiplier) * dt * 0.5)
            return

        dx, dy = input_vector
        magnitude = hypot(dx, dy)
        if magnitude > 0.0:
            dx /= magnitude
            dy /= magnitude

        speed = (48.0 + self.profile.mobility * 6.0) * current_quality
        movement_distance = speed * dt
        next_x = _clamp(self.robot_position[0] + dx * movement_distance, 0.0, self.arena_size[0])
        next_y = _clamp(self.robot_position[1] + dy * movement_distance, 0.0, self.arena_size[1])
        self.robot_position = (next_x, next_y)
        self.refresh_status()
        actual_distance = _distance(previous_position, self.robot_position)
        self.battery_level = max(
            0.0,
            self.battery_level - self.battery_drain_amount(actual_distance, dt, self.last_control_quality, self.last_battery_multiplier),
        )
        self._update_hazard_exposure(actual_distance, dt)
        self._sync_objective_state(previous_position)

    def _sync_objective_state(self, previous_position: Position | None = None) -> None:
        if _distance(self.robot_position, self.relay_position) <= self.relay_radius:
            self.objective_complete = True
            self.mission_success = True
        elif previous_position is not None and _distance_to_segment(self.relay_position, previous_position, self.robot_position) <= self.relay_radius:
            self.objective_complete = True
            self.mission_success = True
        else:
            self.objective_complete = False
            self.mission_success = False

    def _update_hazard_exposure(self, movement_distance: float, dt: float) -> None:
        in_hazard = self.last_environment_multiplier <= 0.72
        if in_hazard and movement_distance > 0.0:
            exposure_gain = dt
            if self.last_control_quality < 0.58:
                exposure_gain += dt * 0.5
            self.hazard_exposure = min(8.0, self.hazard_exposure + exposure_gain)
            return

        exposure_decay = dt * (1.0 if movement_distance <= 0.0 else 0.5)
        self.hazard_exposure = max(0.0, self.hazard_exposure - exposure_decay)
