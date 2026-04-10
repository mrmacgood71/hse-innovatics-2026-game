from __future__ import annotations

from collections.abc import MutableMapping
import random

import pygame

from meridex_alpha.constants import ACCENT, BG, ICE, PANEL, TEXT, WARN
from meridex_alpha.mission_catalog import MissionOption
from meridex_alpha.mission_catalog import mission_options_for_npc
from meridex_alpha.states.base import BaseState, StateResult
from meridex_alpha.ui import draw_panel, draw_wrapped_text


class MissionSelectState(BaseState):
    name = "mission_select"

    def __init__(self, shared_data: MutableMapping[str, object]) -> None:
        self.shared_data = shared_data
        self.active_npc_key: str | None = None
        self.mission_options: tuple[MissionOption, ...] = ()
        self.cursor_index = 0
        self.selected_mission_key: str | None = None

    def enter(self) -> None:
        npc_key = self.shared_data.get("active_npc_key")
        self.active_npc_key = npc_key if isinstance(npc_key, str) else None
        self.mission_options = mission_options_for_npc(self.active_npc_key or "")
        self.cursor_index = 0
        self.selected_mission_key = None

    def _move_cursor(self, delta: int) -> None:
        if not self.mission_options:
            return
        self.cursor_index = (self.cursor_index + delta) % len(self.mission_options)

    def _select_current_mission(self) -> StateResult | None:
        if not self.mission_options:
            return None
        selected = self.mission_options[self.cursor_index]
        self.selected_mission_key = selected.key
        self.shared_data["selected_mission_key"] = selected.key
        if selected.storm is not None and selected.storm.applies and random.random() < 0.5:
            self.shared_data["storm_mode"] = "storm"
        else:
            self.shared_data["storm_mode"] = "none"
        return StateResult(next_state="loadout")

    def handle_event(self, event: pygame.event.Event) -> StateResult | None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            return StateResult(next_state="hub")
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_UP, pygame.K_w):
            self._move_cursor(-1)
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_DOWN, pygame.K_s):
            self._move_cursor(1)
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_SPACE):
            return self._select_current_mission()
        return None

    def update(self, dt: float) -> StateResult | None:
        return None

    def render(self, surface: pygame.Surface) -> None:
        surface.fill(BG)
        width, height = surface.get_size()

        title_font = pygame.font.Font(None, 80)
        body_font = pygame.font.Font(None, 32)
        small_font = pygame.font.Font(None, 26)

        title = title_font.render("Выбор задания", True, TEXT)
        surface.blit(title, title.get_rect(center=(width // 2, 76)))

        panel_rect = pygame.Rect(120, 150, width - 240, 320)
        draw_panel(surface, panel_rect, fill_color=PANEL, border_color=ACCENT, radius=18)

        active_text = self.active_npc_key or "нет"
        draw_wrapped_text(
            surface,
            f"Источник задания: {active_text}.",
            body_font,
            TEXT,
            pygame.Rect(panel_rect.left + 32, panel_rect.top + 34, panel_rect.width - 64, 60),
        )
        draw_wrapped_text(
            surface,
            "Доступные задания:",
            body_font,
            ICE,
            pygame.Rect(panel_rect.left + 32, panel_rect.top + 100, panel_rect.width - 64, 36),
        )
        option_top = panel_rect.top + 148
        if self.mission_options:
            for index, option in enumerate(self.mission_options):
                prefix = ">" if index == self.cursor_index else " "
                option_text = f"{prefix} {option.title}: {option.summary}"
                option_color = ACCENT if index == self.cursor_index else TEXT
                draw_wrapped_text(
                    surface,
                    option_text,
                    body_font,
                    option_color,
                    pygame.Rect(panel_rect.left + 32, option_top, panel_rect.width - 64, 56),
                )
                option_top += 56
        else:
            draw_wrapped_text(
                surface,
                "Для этого персонажа сейчас нет доступных заданий.",
                body_font,
                WARN,
                pygame.Rect(panel_rect.left + 32, option_top, panel_rect.width - 64, 56),
            )
        draw_wrapped_text(
            surface,
            "Стрелки вверх/вниз выбирают задание. Enter подтверждает. Esc возвращает в хаб.",
            small_font,
            WARN,
            pygame.Rect(panel_rect.left + 32, panel_rect.bottom - 70, panel_rect.width - 64, 30),
        )
