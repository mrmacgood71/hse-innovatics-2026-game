from __future__ import annotations

from collections.abc import MutableMapping

import pygame

from meridex_alpha.constants import ACCENT, BG, ICE, PANEL, TEXT, WARN
from meridex_alpha.mission_catalog import MissionOption
from meridex_alpha.mission_catalog import mission_option_for_key
from meridex_alpha.states.base import BaseState, StateResult
from meridex_alpha.ui import draw_panel, draw_wrapped_text


class StormPromptState(BaseState):
    name = "storm_prompt"

    def __init__(self, shared_data: MutableMapping[str, object]) -> None:
        self.shared_data = shared_data
        self.mission_option: MissionOption | None = None
        self._pending_route: str | None = None

    def enter(self) -> None:
        selected_mission_key = self.shared_data.get("selected_mission_key")
        mission_key = selected_mission_key if isinstance(selected_mission_key, str) else ""
        self.mission_option = mission_option_for_key(mission_key)
        self._pending_route = None
        if self.mission_option is None or self.mission_option.storm is None or not self.mission_option.storm.applies:
            self.shared_data.pop("storm_mode", None)
            self._pending_route = "loadout"

    def _set_storm_mode(self, storm_mode: str) -> StateResult:
        self.shared_data["storm_mode"] = storm_mode
        return StateResult(next_state="loadout")

    def _cancel(self) -> StateResult:
        self.shared_data.pop("active_npc_key", None)
        self.shared_data.pop("selected_mission_key", None)
        self.shared_data.pop("storm_mode", None)
        return StateResult(next_state="hub")

    def handle_event(self, event: pygame.event.Event) -> StateResult | None:
        if self._pending_route is not None:
            return None
        if event.type != pygame.KEYDOWN:
            return None
        if event.key == pygame.K_1:
            return self._set_storm_mode("storm")
        if event.key == pygame.K_2:
            return self._set_storm_mode("safe")
        if event.key in (pygame.K_3, pygame.K_ESCAPE):
            return self._cancel()
        return None

    def update(self, dt: float) -> StateResult | None:
        if self._pending_route is None:
            return None
        next_state = self._pending_route
        self._pending_route = None
        return StateResult(next_state=next_state)

    def render(self, surface: pygame.Surface) -> None:
        surface.fill(BG)
        width, height = surface.get_size()

        title_font = pygame.font.Font(None, 80)
        body_font = pygame.font.Font(None, 32)
        small_font = pygame.font.Font(None, 26)

        title = title_font.render("Штормовой протокол", True, TEXT)
        surface.blit(title, title.get_rect(center=(width // 2, 76)))

        panel_rect = pygame.Rect(96, 146, width - 192, 356)
        draw_panel(surface, panel_rect, fill_color=PANEL, border_color=ACCENT, radius=18)

        if self.mission_option is None:
            heading = "Задание не выбрано."
            warning_text = "Сначала вернись в хаб и возьми миссию."
            effects_text = "Без выбранного задания штормовой режим не применяется."
        else:
            heading = f"Выбрано задание: {self.mission_option.title}"
            storm = self.mission_option.storm
            if storm is None:
                warning_text = "Для этого задания штормовой модификатор не используется."
                effects_text = "Игра сразу перейдет к следующему шагу."
            else:
                warning_text = storm.warning_text
                effects_text = storm.effects_text

        draw_wrapped_text(
            surface,
            heading,
            body_font,
            TEXT,
            pygame.Rect(panel_rect.left + 28, panel_rect.top + 24, panel_rect.width - 56, 50),
        )
        draw_wrapped_text(
            surface,
            warning_text,
            body_font,
            WARN,
            pygame.Rect(panel_rect.left + 28, panel_rect.top + 92, panel_rect.width - 56, 88),
        )
        draw_wrapped_text(
            surface,
            effects_text,
            body_font,
            TEXT,
            pygame.Rect(panel_rect.left + 28, panel_rect.top + 182, panel_rect.width - 56, 88),
        )

        option_y = panel_rect.top + 286
        options = (
            ("1", "Продолжить в шторм", ACCENT),
            ("2", "Запустить безопасный режим", ICE),
            ("3", "Отменить и вернуться в хаб", WARN),
        )
        for key_label, label, color in options:
            option_text = f"[{key_label}] {label}"
            option_surface = body_font.render(option_text, True, color)
            surface.blit(option_surface, (panel_rect.left + 32, option_y))
            option_y += 36

        footer_text = "Нажми 1, 2 или 3. Esc тоже отменяет запуск."
        footer = small_font.render(footer_text, True, ICE)
        surface.blit(footer, footer.get_rect(center=(width // 2, height - 74)))
