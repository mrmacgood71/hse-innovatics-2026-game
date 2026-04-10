from __future__ import annotations

from dataclasses import dataclass, field


DEFAULT_TARGET_CELLS = frozenset(
    {
        (0, 0),
        (1, 0),
        (2, 0),
        (1, 1),
        (1, 2),
        (4, 2),
        (2, 2),
        (3, 2),
    }
)
DEFAULT_BLOCKED_CELLS = frozenset({(3, 0), (2, 1), (0, 2), (4, 3)})


@dataclass(slots=True)
class AgromonitoringRuntime:
    grid_width: int = 6
    grid_height: int = 4
    storm_mode: str = "none"
    target_cells: set[tuple[int, int]] = field(default_factory=lambda: set(DEFAULT_TARGET_CELLS))
    blocked_cells: set[tuple[int, int]] = field(default_factory=lambda: set(DEFAULT_BLOCKED_CELLS))
    action_limit: int = 10
    planned_route: list[tuple[int, int]] = field(default_factory=list)
    covered_cells: set[tuple[int, int]] = field(default_factory=set)
    flight_active: bool = False
    flight_complete: bool = False
    flight_index: int = -1
    flight_step_duration: float = 0.18
    flight_timer: float = 0.0

    def add_route_cell(self, x: int, y: int) -> None:
        if not (0 <= x < self.grid_width and 0 <= y < self.grid_height):
            return
        if (x, y) in self.blocked_cells:
            return
        if self.planned_route:
            last_x, last_y = self.planned_route[-1]
            if abs(last_x - x) + abs(last_y - y) != 1:
                return

        self.planned_route.append((x, y))

    def remove_last_route_cell(self) -> None:
        if self.planned_route:
            self.planned_route.pop()

    def start_flight(self) -> bool:
        if not self.planned_route:
            return False
        self.covered_cells.clear()
        self.flight_active = True
        self.flight_complete = False
        self.flight_timer = 0.0
        self.flight_index = 0
        self.covered_cells.add(self.planned_route[0])
        return True

    def step_flight(self, dt: float) -> None:
        if not self.flight_active:
            return
        self.flight_timer += dt
        while self.flight_timer >= self.flight_step_duration and self.flight_active:
            self.flight_timer -= self.flight_step_duration
            if self.flight_index + 1 < len(self.planned_route):
                self.flight_index += 1
                self.covered_cells.add(self.planned_route[self.flight_index])
                continue
            self.flight_active = False
            self.flight_complete = True

    @property
    def actions_used(self) -> int:
        return len(self.planned_route)

    @property
    def current_flight_cell(self) -> tuple[int, int] | None:
        if self.flight_index < 0 or self.flight_index >= len(self.planned_route):
            return None
        return self.planned_route[self.flight_index]

    @property
    def action_budget(self) -> int:
        if self.storm_mode == "storm":
            return max(6, self.action_limit - 1)
        if self.storm_mode == "safe":
            return self.action_limit + 1
        return self.action_limit

    def has_exceeded_budget(self) -> bool:
        return self.actions_used > self.action_budget

    def required_cells(self) -> set[tuple[int, int]]:
        return set(self.target_cells)

    def coverage_ratio(self) -> float:
        required = self.required_cells()
        if not required:
            return 1.0
        covered_required = len(required.intersection(self.covered_cells))
        return covered_required / len(required)

    def is_success(self) -> bool:
        return not self.has_exceeded_budget() and self.required_cells().issubset(self.covered_cells)
