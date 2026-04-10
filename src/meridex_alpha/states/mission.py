from __future__ import annotations

from collections.abc import MutableMapping

import pygame

from meridex_alpha.constants import ACCENT, BG, ICE, PANEL, TEXT, WARN
from meridex_alpha.failure_rules import evaluate_failure
from meridex_alpha.loadout import BASE_PROFILE
from meridex_alpha.mission import EnvironmentZone, MissionRuntime
from meridex_alpha.models import RobotProfile
from meridex_alpha.states.base import BaseState, StateResult
from meridex_alpha.ui import draw_meter, draw_panel, draw_wrapped_text


class MissionState(BaseState):
    name = "mission"

    def __init__(self, shared_data: MutableMapping[str, object]) -> None:
        self.shared_data = shared_data
        self.runtime: MissionRuntime | None = None
        self.active_keys: set[int] = set()
        self.status_text = "Mission pending."

    def enter(self) -> None:
        existing_runtime = self.shared_data.get("mission_runtime")
        if isinstance(existing_runtime, MissionRuntime):
            self.runtime = existing_runtime
            last_action = self.shared_data.get("diagnostics_last_action")
            if isinstance(last_action, str):
                self.status_text = f"Mission resumed. {last_action}"
            else:
                self.status_text = "Mission active. Move to the relay and hold position to secure it."
            self.shared_data["mission_status"] = "active"
            self.active_keys.clear()
            return

        profile = self.shared_data.get("robot_profile")
        if not isinstance(profile, RobotProfile):
            profile = BASE_PROFILE
            self.status_text = "No stored robot profile was available; using a fallback mission profile."
        else:
            self.status_text = "Mission active. Move to the relay and hold position to secure it."

        self.runtime = MissionRuntime(
            profile=profile,
            environment_zones=(
                EnvironmentZone(250.0, 80.0, 140.0, 110.0, control_multiplier=0.72),
                EnvironmentZone(500.0, 210.0, 120.0, 80.0, control_multiplier=0.62, battery_multiplier=1.08),
            ),
        )
        self.shared_data["mission_runtime"] = self.runtime
        self.shared_data["mission_status"] = "active"
        self.active_keys.clear()

    def _complete_mission(self) -> StateResult:
        assert self.runtime is not None
        self.shared_data["mission_complete"] = True
        self.shared_data["mission_failure"] = None
        self.shared_data["mission_status"] = "debrief"
        self.shared_data["mission_result"] = {
            "success": True,
            "battery_remaining": round(self.runtime.battery_level, 2),
            "selected_modules": self.runtime.profile.selected_modules,
        }
        self.status_text = "Relay secured. Returning to debrief."
        return StateResult(next_state="debrief")

    def handle_event(self, event: pygame.event.Event) -> StateResult | None:
        if event.type == pygame.KEYDOWN:
            self.active_keys.add(event.key)
        elif event.type == pygame.KEYUP:
            self.active_keys.discard(event.key)
        return None

    def update(self, dt: float) -> StateResult | None:
        if self.runtime is None:
            return None

        if self.runtime.objective_complete:
            return self._complete_mission()

        direction = self._active_direction()
        self.runtime.step(direction, dt)

        if self.runtime.objective_complete:
            return self._complete_mission()
        else:
            active_issue = evaluate_failure(self.runtime)
            if active_issue is not None:
                self.runtime.active_failure_key = active_issue.key
                self.shared_data["mission_failure"] = active_issue
                self.shared_data["mission_status"] = "diagnostics"
                self.shared_data["mission_complete"] = False
                self.status_text = f"{active_issue.title} detected. Switching to diagnostics."
                return StateResult(next_state="diagnostics")

            self.shared_data["mission_complete"] = False
            self.shared_data["mission_result"] = {
                "success": False,
                "battery_remaining": round(self.runtime.battery_level, 2),
                "selected_modules": self.runtime.profile.selected_modules,
            }
            self.shared_data["mission_failure"] = None

        return None

    def _active_direction(self) -> tuple[float, float]:
        x = 0.0
        y = 0.0
        if pygame.K_LEFT in self.active_keys or pygame.K_a in self.active_keys:
            x -= 1.0
        if pygame.K_RIGHT in self.active_keys or pygame.K_d in self.active_keys:
            x += 1.0
        if pygame.K_UP in self.active_keys or pygame.K_w in self.active_keys:
            y -= 1.0
        if pygame.K_DOWN in self.active_keys or pygame.K_s in self.active_keys:
            y += 1.0
        return x, y

    def render(self, surface: pygame.Surface) -> None:
        surface.fill(BG)
        width, height = surface.get_size()

        title_font = pygame.font.Font(None, 72)
        body_font = pygame.font.Font(None, 30)
        small_font = pygame.font.Font(None, 24)

        title = title_font.render("Mission", True, TEXT)
        surface.blit(title, title.get_rect(center=(width // 2, 62)))

        map_rect = pygame.Rect(70, 120, width - 140, 360)
        draw_panel(surface, map_rect, fill_color=PANEL, border_color=ACCENT)

        if self.runtime is not None:
            self._draw_environment(surface, map_rect)
            self._draw_relay(surface, map_rect)
            self._draw_robot(surface, map_rect)

        info_rect = pygame.Rect(70, 500, width - 140, 130)
        draw_panel(surface, info_rect, fill_color=PANEL, border_color=ICE)

        if self.runtime is None:
            status = "Mission cannot start without a robot profile."
        else:
            status = self.status_text

        draw_wrapped_text(surface, status, body_font, TEXT, pygame.Rect(info_rect.left + 18, info_rect.top + 10, info_rect.width - 36, 42))

        meter_top = info_rect.top + 56
        meter_width = (info_rect.width - 54) // 2
        if self.runtime is None:
            draw_wrapped_text(
                surface,
                "Loadout data is missing. Mission telemetry is unavailable.",
                small_font,
                WARN,
                pygame.Rect(info_rect.left + 18, meter_top, info_rect.width - 36, 22),
            )
        else:
            draw_meter(
                surface,
                "Battery",
                f"{self.runtime.battery_level:.0f}/{self.runtime.battery_capacity:.0f}",
                self.runtime.battery_level / self.runtime.battery_capacity,
                small_font,
                pygame.Rect(info_rect.left + 18, meter_top, meter_width, 34),
            )
            draw_meter(
                surface,
                "Control",
                f"{self.runtime.last_control_quality:.0%}",
                self.runtime.last_control_quality,
                small_font,
                pygame.Rect(info_rect.left + 36 + meter_width, meter_top, meter_width, 34),
                fill_color=ICE,
            )
            footer_text = f"Exposure: {self.runtime.hazard_exposure:.1f}    Reach the relay and hold position."
            draw_wrapped_text(
                surface,
                footer_text,
                small_font,
                WARN,
                pygame.Rect(info_rect.left + 18, info_rect.top + 100, info_rect.width - 36, 24),
            )

    def _map_to_screen(self, map_rect: pygame.Rect, position: tuple[float, float]) -> tuple[int, int]:
        if self.runtime is None:
            return map_rect.center
        x_scale = map_rect.width / self.runtime.arena_size[0]
        y_scale = map_rect.height / self.runtime.arena_size[1]
        return (
            int(map_rect.left + position[0] * x_scale),
            int(map_rect.top + position[1] * y_scale),
        )

    def _draw_environment(self, surface: pygame.Surface, map_rect: pygame.Rect) -> None:
        assert self.runtime is not None
        for zone in self.runtime.environment_zones:
            top_left = self._map_to_screen(map_rect, (zone.left, zone.top))
            bottom_right = self._map_to_screen(map_rect, (zone.left + zone.width, zone.top + zone.height))
            zone_rect = pygame.Rect(top_left, (bottom_right[0] - top_left[0], bottom_right[1] - top_left[1]))
            pygame.draw.rect(surface, (64, 76, 92), zone_rect, border_radius=10)
            pygame.draw.rect(surface, (120, 135, 160), zone_rect, width=1, border_radius=10)

    def _draw_relay(self, surface: pygame.Surface, map_rect: pygame.Rect) -> None:
        assert self.runtime is not None
        relay_pos = self._map_to_screen(map_rect, self.runtime.relay_position)
        pygame.draw.circle(surface, (160, 230, 190), relay_pos, 15)
        pygame.draw.circle(surface, TEXT, relay_pos, 15, width=2)

    def _draw_robot(self, surface: pygame.Surface, map_rect: pygame.Rect) -> None:
        assert self.runtime is not None
        robot_pos = self._map_to_screen(map_rect, self.runtime.robot_position)
        radius = 12
        pygame.draw.circle(surface, ACCENT, robot_pos, radius)
        pygame.draw.circle(surface, TEXT, robot_pos, radius, width=2)
