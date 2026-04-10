from __future__ import annotations

import pygame

from meridex_alpha.constants import FPS, PANEL, SCREEN_HEIGHT, SCREEN_WIDTH, TEXT, WARN
from meridex_alpha.states.base import BaseState, StateResult
from meridex_alpha.states.briefing import BriefingState
from meridex_alpha.states.diagnostics import DiagnosticsState
from meridex_alpha.states.debrief import DebriefState
from meridex_alpha.states.agromonitoring import AgromonitoringState
from meridex_alpha.states.hub import HubState
from meridex_alpha.states.loadout import LoadoutState
from meridex_alpha.states.mission import MissionState
from meridex_alpha.states.mission_select import MissionSelectState
from meridex_alpha.states.menu import MenuState
from meridex_alpha.states.storm_prompt import StormPromptState
from meridex_alpha.states.warehouse import WarehouseState


class Game:
    def __init__(self) -> None:
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.running = True
        self.status_message = "Ready."
        self.status_font = pygame.font.Font(None, 28)
        self.shared_data: dict[str, object] = {}
        self.states: dict[str, BaseState] = {
            "menu": MenuState(),
            "briefing": BriefingState(),
            "hub": HubState(self.shared_data),
            "agromonitoring": AgromonitoringState(self.shared_data),
            "loadout": LoadoutState(self.shared_data, next_state="mission"),
            "mission": MissionState(self.shared_data),
            "mission_select": MissionSelectState(self.shared_data),
            "storm_prompt": StormPromptState(self.shared_data),
            "warehouse_pressure": WarehouseState(self.shared_data),
            "diagnostics": DiagnosticsState(self.shared_data),
            "debrief": DebriefState(self.shared_data),
        }
        self.current_state_name = "menu"
        self.current_state = self.states[self.current_state_name]
        self.current_state.enter()

    def _apply_result(self, result: StateResult | None) -> None:
        if result is None or result.next_state is None:
            return
        self.switch_state(result.next_state)

    def _reset_run_state(self) -> None:
        for key in (
            "mission_runtime",
            "mission_failure",
            "mission_complete",
            "mission_result",
            "mission_status",
            "diagnostics_last_action",
            "hub_runtime",
            "active_npc_key",
            "selected_mission_key",
            "storm_mode",
        ):
            self.shared_data.pop(key, None)

        loadout_state = self.states.get("loadout")
        if isinstance(loadout_state, LoadoutState):
            loadout_state.cursor = 0
            loadout_state.selected_modules.clear()
            loadout_state.locked_profile = None
            loadout_state.status_text = loadout_state.editing_status_text

    def switch_state(self, state_name: str) -> None:
        if state_name == "menu":
            self._reset_run_state()

        next_state = self.states.get(state_name)
        if next_state is None:
            self.status_message = f"State '{state_name}' is not available yet."
            return

        self.current_state_name = state_name
        self.current_state = next_state
        self.status_message = f"Entered {state_name}."
        self.current_state.enter()

    def _draw_status_bar(self) -> None:
        if self.current_state_name == "hub":
            return
        width, height = self.screen.get_size()
        bar_rect = pygame.Rect(24, height - 60, width - 48, 36)
        pygame.draw.rect(self.screen, PANEL, bar_rect, border_radius=10)
        pygame.draw.rect(self.screen, WARN, bar_rect, width=1, border_radius=10)
        message = self.status_font.render(self.status_message, True, TEXT)
        self.screen.blit(message, message.get_rect(midleft=(40, height - 42)))

    def run(self) -> None:
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    continue
                result = self.current_state.handle_event(event)
                self._apply_result(result)

            result = self.current_state.update(dt)
            self._apply_result(result)

            self.current_state.render(self.screen)
            self._draw_status_bar()
            pygame.display.flip()
