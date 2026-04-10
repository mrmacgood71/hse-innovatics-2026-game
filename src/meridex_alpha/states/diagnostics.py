from __future__ import annotations

from collections.abc import MutableMapping

import pygame

from meridex_alpha.constants import ACCENT, BG, ICE, PANEL, TEXT, WARN
from meridex_alpha.failure_rules import apply_recovery_action, evaluate_failure, get_failure_issue
from meridex_alpha.mission import MissionRuntime
from meridex_alpha.states.base import BaseState, StateResult
from meridex_alpha.ui import draw_panel, draw_wrapped_text


class DiagnosticsState(BaseState):
    name = "diagnostics"

    def __init__(self, shared_data: MutableMapping[str, object]) -> None:
        self.shared_data = shared_data
        self.runtime: MissionRuntime | None = None
        self.status_text = "Diagnostics idle."
        self.issue = None

    def enter(self) -> None:
        runtime = self.shared_data.get("mission_runtime")
        self.runtime = runtime if isinstance(runtime, MissionRuntime) else None
        issue = self.shared_data.get("mission_failure")
        self.issue = issue if issue is not None else evaluate_failure(self.runtime) if self.runtime is not None else None
        if self.issue is not None and self.runtime is not None:
            self.runtime.active_failure_key = self.issue.key
            self.shared_data["mission_failure"] = self.issue
            self.status_text = f"{self.issue.title} detected. Choose a field repair and resume the mission."
        else:
            issue_key = self.runtime.active_failure_key if self.runtime is not None else None
            self.issue = get_failure_issue(issue_key)
            self.status_text = "No active fault is available. Press Enter to return to mission."

    def _action_focus_text(self, action_key: str) -> str:
        if action_key == "recalibrate_sensors":
            return "Sensor clarity"
        if action_key == "route_reserve_power":
            return "Power headroom"
        if action_key == "deploy_stabilizers":
            return "Drift control"
        return "General recovery"

    def handle_event(self, event: pygame.event.Event) -> StateResult | None:
        if event.type != pygame.KEYDOWN:
            return None

        if event.key in (pygame.K_RETURN, pygame.K_ESCAPE):
            self.shared_data["mission_status"] = "active"
            return StateResult(next_state="mission")

        if self.runtime is None or self.issue is None:
            return None

        action_index = self._action_index_for_key(event.key)
        if action_index is None or action_index >= len(self.issue.recovery_actions):
            return None

        action = self.issue.recovery_actions[action_index]
        self.shared_data["diagnostics_last_action"] = apply_recovery_action(self.runtime, action.key)
        self.shared_data["mission_failure"] = None
        self.shared_data["mission_status"] = "active"
        self.issue = None
        self.status_text = "Repair applied. Returning to mission."
        return StateResult(next_state="mission")

    def update(self, dt: float) -> StateResult | None:
        return None

    def render(self, surface: pygame.Surface) -> None:
        surface.fill(BG)
        width, height = surface.get_size()

        title_font = pygame.font.Font(None, 72)
        body_font = pygame.font.Font(None, 30)
        small_font = pygame.font.Font(None, 24)

        title = title_font.render("Diagnostics", True, TEXT)
        surface.blit(title, title.get_rect(center=(width // 2, 70)))

        panel_rect = pygame.Rect(80, 130, width - 160, 400)
        draw_panel(surface, panel_rect, fill_color=PANEL, border_color=ACCENT)

        issue_title = "No active issue" if self.issue is None else self.issue.title
        issue_summary = "Mission telemetry is stable enough to continue." if self.issue is None else self.issue.summary
        draw_wrapped_text(surface, issue_title, body_font, WARN, pygame.Rect(panel_rect.left + 24, panel_rect.top + 24, panel_rect.width - 48, 32))
        draw_wrapped_text(surface, issue_summary, body_font, TEXT, pygame.Rect(panel_rect.left + 24, panel_rect.top + 68, panel_rect.width - 48, 56))

        actions = () if self.issue is None else self.issue.recovery_actions
        action_top = panel_rect.top + 140
        for index, action in enumerate(actions, start=1):
            action_rect = pygame.Rect(panel_rect.left + 20, action_top + (index - 1) * 84, panel_rect.width - 40, 76)
            draw_panel(surface, action_rect, fill_color=BG, border_color=ICE)
            label = small_font.render(f"{index}. {action.label}", True, TEXT)
            surface.blit(label, (action_rect.left + 16, action_rect.top + 10))
            focus_text = small_font.render(f"Focus: {self._action_focus_text(action.key)}", True, ACCENT)
            surface.blit(focus_text, (action_rect.left + 16, action_rect.top + 30))
            draw_wrapped_text(
                surface,
                action.summary,
                small_font,
                WARN,
                pygame.Rect(action_rect.left + 16, action_rect.top + 52, action_rect.width - 32, 18),
            )

        footer_rect = pygame.Rect(80, height - 130, width - 160, 70)
        draw_panel(surface, footer_rect, fill_color=PANEL, border_color=ICE)
        footer_text = self.status_text if self.issue is not None else "Press Enter to return to mission."
        draw_wrapped_text(surface, footer_text, small_font, TEXT, pygame.Rect(footer_rect.left + 18, footer_rect.top + 18, footer_rect.width - 36, 30))

    def _action_index_for_key(self, key: int) -> int | None:
        if key == pygame.K_1:
            return 0
        if key == pygame.K_2:
            return 1
        if key == pygame.K_3:
            return 2
        return None
