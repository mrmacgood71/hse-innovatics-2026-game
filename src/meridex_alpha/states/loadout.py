from __future__ import annotations

from collections.abc import MutableMapping

import pygame

from meridex_alpha.constants import ACCENT, BG, ICE, PANEL, ROUGH, TEXT, WARN
from meridex_alpha.loadout import MAX_STAT, MODULE_CATALOG, calculate_robot_profile
from meridex_alpha.models import RobotProfile
from meridex_alpha.states.base import BaseState, StateResult
from meridex_alpha.ui import draw_meter, draw_panel, draw_wrapped_text


class LoadoutState(BaseState):
    name = "loadout"
    editing_status_text = (
        "Собери конфигурацию платформы и нажми Enter для запуска задания."
    )

    def __init__(self, shared_data: MutableMapping[str, object], next_state: str | None = "mission") -> None:
        self.shared_data = shared_data
        self.next_state = next_state
        self.module_keys = list(MODULE_CATALOG)
        self.cursor = 0
        self.selected_modules: list[str] = []
        self.locked_profile: RobotProfile | None = None
        self.status_text = self.editing_status_text

    def enter(self) -> None:
        if self.locked_profile is None:
            self.status_text = self.editing_status_text

    def handle_event(self, event: pygame.event.Event) -> StateResult | None:
        if event.type != pygame.KEYDOWN:
            return None

        if event.key == pygame.K_UP:
            self.cursor = (self.cursor - 1) % len(self.module_keys)
        elif event.key == pygame.K_DOWN:
            self.cursor = (self.cursor + 1) % len(self.module_keys)
        elif event.key == pygame.K_SPACE:
            self._toggle_selected(self.module_keys[self.cursor])
        elif event.key == pygame.K_RETURN:
            profile = self._current_profile()
            self.shared_data["robot_profile"] = profile
            self.locked_profile = profile
            resolved_next_state = self._resolved_next_state()
            if resolved_next_state is None:
                self.status_text = "Профиль сохранен. Этот экран остается открытым."
                return None
            self.status_text = "Профиль сохранен. Переход к выбранному заданию."
            return StateResult(next_state=resolved_next_state)
        return None

    def update(self, dt: float) -> StateResult | None:
        return None

    def _toggle_selected(self, module_key: str) -> None:
        self.locked_profile = None
        self.status_text = self.editing_status_text
        if module_key in self.selected_modules:
            self.selected_modules.remove(module_key)
            return
        self.selected_modules.append(module_key)

    def _current_profile(self) -> RobotProfile:
        return calculate_robot_profile(self.selected_modules)

    def _display_profile(self) -> RobotProfile:
        if self.locked_profile is not None:
            return self.locked_profile
        return self._current_profile()

    def _resolved_next_state(self) -> str | None:
        selected_mission_key = self.shared_data.get("selected_mission_key")
        if isinstance(selected_mission_key, str) and selected_mission_key:
            return selected_mission_key
        return self.next_state

    def _module_tradeoff_text(self, module_key: str) -> str:
        module = MODULE_CATALOG[module_key]
        parts: list[str] = []
        for stat_name in ("endurance", "mobility", "armor", "sensors", "stability"):
            modifier = module.modifiers.get(stat_name)
            if modifier is None:
                continue
            sign = "+" if modifier > 0 else ""
            parts.append(f"{stat_name.capitalize()} {sign}{modifier}")
        return "  ".join(parts)

    def render(self, surface: pygame.Surface) -> None:
        surface.fill(BG)
        width, height = surface.get_size()

        title_font = pygame.font.Font(None, 72)
        body_font = pygame.font.Font(None, 30)
        small_font = pygame.font.Font(None, 24)

        title = title_font.render("Конфигурация", True, TEXT)
        surface.blit(title, title.get_rect(center=(width // 2, 70)))

        left_panel = pygame.Rect(70, 120, 470, 500)
        right_panel = pygame.Rect(570, 120, width - 640, 500)
        draw_panel(surface, left_panel, fill_color=PANEL, border_color=ACCENT)
        draw_panel(surface, right_panel, fill_color=PANEL, border_color=ICE)

        left_title = body_font.render("Модули", True, TEXT)
        surface.blit(left_title, (left_panel.left + 24, left_panel.top + 18))

        row_y = left_panel.top + 66
        row_height = 54
        for index, module_key in enumerate(self.module_keys):
            module = MODULE_CATALOG[module_key]
            row_rect = pygame.Rect(left_panel.left + 18, row_y + index * row_height, left_panel.width - 36, 46)
            is_cursor = index == self.cursor
            is_selected = module_key in self.selected_modules

            if is_cursor:
                pygame.draw.rect(surface, ROUGH, row_rect, border_radius=8)
            if is_selected:
                pygame.draw.rect(surface, ACCENT, row_rect, width=2, border_radius=8)

            name_surface = body_font.render(module.name, True, TEXT)
            tradeoff_surface = small_font.render(self._module_tradeoff_text(module_key), True, ICE)
            surface.blit(name_surface, (row_rect.left + 10, row_rect.top + 4))
            surface.blit(tradeoff_surface, (row_rect.left + 10, row_rect.top + 24))

        selection_title = body_font.render("Текущий профиль", True, TEXT)
        surface.blit(selection_title, (right_panel.left + 24, right_panel.top + 18))

        profile = self._display_profile()
        stat_rect = pygame.Rect(right_panel.left + 24, right_panel.top + 58, right_panel.width - 48, 184)
        stat_rows = (
            ("Endurance", profile.endurance),
            ("Mobility", profile.mobility),
            ("Armor", profile.armor),
            ("Sensors", profile.sensors),
            ("Stability", profile.stability),
        )
        stat_row_height = 34
        for index, (label, value) in enumerate(stat_rows):
            row_rect = pygame.Rect(stat_rect.left, stat_rect.top + index * stat_row_height, stat_rect.width, 28)
            draw_meter(
                surface,
                label,
                str(value),
                value / MAX_STAT,
                small_font,
                row_rect,
            )

        details_rect = pygame.Rect(right_panel.left + 24, right_panel.top + 270, right_panel.width - 48, 150)
        draw_wrapped_text(
            surface,
            "Выбранные модули: " + (", ".join(profile.selected_modules) if profile.selected_modules else "нет"),
            small_font,
            TEXT,
            details_rect,
        )
        draw_wrapped_text(
            surface,
            self.status_text,
            small_font,
            WARN,
            pygame.Rect(right_panel.left + 24, right_panel.bottom - 90, right_panel.width - 48, 40),
        )

        footer_text = "Enter сохраняет профиль платформы."
        next_state = self._resolved_next_state()
        if next_state is not None:
            footer_text += " После этого начнется выбранное задание."
        else:
            footer_text += " В этой сборке экран не сменится."
        footer = small_font.render(footer_text, True, ICE)
        surface.blit(footer, footer.get_rect(center=(width // 2, height - 38)))
