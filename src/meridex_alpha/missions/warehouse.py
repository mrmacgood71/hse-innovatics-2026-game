from __future__ import annotations

from dataclasses import dataclass, field

from meridex_alpha.loadout import BASE_PROFILE
from meridex_alpha.models import RobotProfile


@dataclass(slots=True)
class WarehouseRuntime:
    position: tuple[float, float] = (100.0, 360.0)
    velocity_x: float = 0.0
    velocity_y: float = 0.0
    goal_rect: tuple[float, float, float, float] = (1040.0, 300.0, 110.0, 120.0)
    storm_mode: str = "none"
    time_remaining: float = 45.0
    collision_limit: int = 3
    collisions: int = 0
    robot_profile: RobotProfile = BASE_PROFILE
    has_moved: bool = False
    last_step_collided: bool = False
    peak_speed: float = 0.0
    obstacles: tuple[tuple[float, float, float, float], ...] = field(
        default_factory=lambda: (
            (320.0, 110.0, 70.0, 420.0),
            (560.0, 0.0, 70.0, 260.0),
            (560.0, 430.0, 70.0, 290.0),
            (800.0, 110.0, 70.0, 420.0),
        )
    )

    def step(self, input_x: float, input_y: float, dt: float) -> None:
        previous_position = self.position
        self.last_step_collided = False
        profile_mobility = self.robot_profile.mobility
        profile_stability = self.robot_profile.stability

        traction = 0.88 + max(0, 8 - profile_stability) * 0.01
        if self.storm_mode == "storm":
            traction += 0.03
        elif self.storm_mode == "safe":
            traction -= 0.02
        traction = min(0.96, max(0.76, traction))

        accel = 85.0 + profile_mobility * 7.0
        if self.storm_mode == "storm":
            accel += 8.0
        elif self.storm_mode == "safe":
            accel -= 12.0
        self.velocity_x = self.velocity_x * traction + input_x * accel * dt
        self.velocity_y = self.velocity_y * traction + input_y * accel * dt
        self.peak_speed = max(self.peak_speed, abs(self.velocity_x), abs(self.velocity_y))
        next_position = (
            self.position[0] + self.velocity_x * dt,
            self.position[1] + self.velocity_y * dt,
        )
        self.time_remaining = max(0.0, self.time_remaining - dt)
        self.position = self._clamp_to_bounds(next_position)
        if self.position != previous_position:
            self.has_moved = True
        self._resolve_collisions()

    def _clamp_to_bounds(self, position: tuple[float, float]) -> tuple[float, float]:
        x = min(1180.0, max(60.0, position[0]))
        y = min(660.0, max(60.0, position[1]))
        return (x, y)

    def _resolve_collisions(self) -> None:
        colliding_rect = next((rect for rect in self.obstacles if self._point_in_rect(self.position, rect)), None)
        if colliding_rect is None:
            return
        self.collisions += 1
        self.last_step_collided = True
        self.position = self._eject_from_rect(self.position, colliding_rect)
        self.velocity_x *= -0.35
        self.velocity_y *= -0.35
        self.position = self._clamp_to_bounds(self.position)

    def _point_in_rect(self, point: tuple[float, float], rect: tuple[float, float, float, float]) -> bool:
        x, y = point
        left, top, width, height = rect
        return left <= x <= left + width and top <= y <= top + height

    def _eject_from_rect(
        self,
        point: tuple[float, float],
        rect: tuple[float, float, float, float],
    ) -> tuple[float, float]:
        x, y = point
        left, top, width, height = rect
        right = left + width
        bottom = top + height
        margin = 4.0

        if abs(self.velocity_x) >= abs(self.velocity_y) and self.velocity_x != 0.0:
            if self.velocity_x > 0.0:
                return (left - margin, y)
            return (right + margin, y)
        if abs(self.velocity_y) > 0.0:
            if self.velocity_y > 0.0:
                return (x, top - margin)
            return (x, bottom + margin)

        distances = {
            (left - margin, y): abs(x - left),
            (right + margin, y): abs(right - x),
            (x, top - margin): abs(y - top),
            (x, bottom + margin): abs(bottom - y),
        }
        return min(distances, key=distances.get)

    def is_success(self) -> bool:
        x, y = self.position
        left, top, width, height = self.goal_rect
        in_goal = left <= x <= left + width and top <= y <= top + height
        nearly_stopped = abs(self.velocity_x) < 5.0 and abs(self.velocity_y) < 5.0
        return in_goal and nearly_stopped

    def is_bad_stop(self) -> bool:
        if not self.has_moved or self.last_step_collided:
            return False
        if self.peak_speed < 18.0:
            return False
        nearly_stopped = abs(self.velocity_x) < 5.0 and abs(self.velocity_y) < 5.0
        return nearly_stopped and not self.is_success()

    def is_failed(self) -> bool:
        return self.time_remaining <= 0.0 or self.collisions >= self.collision_limit or self.is_bad_stop()
