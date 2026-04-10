from __future__ import annotations

from collections.abc import MutableMapping

import pygame

from meridex_alpha.constants import ACCENT, BG, ICE, PANEL, TEXT, WARN
from meridex_alpha.states.base import BaseState, StateResult
from meridex_alpha.ui import draw_panel, draw_wrapped_text


class DebriefState(BaseState):
    name = "debrief"

    def __init__(self, shared_data: MutableMapping[str, object]) -> None:
        self.shared_data = shared_data
        self.status_text = "Итоги задания еще не подготовлены."
        self.summary_text = "Сводка задания недоступна."
        self.result_title = "Отчет"
        self.return_state = "hub"

    def enter(self) -> None:
        result = self.shared_data.get("mission_result")
        self.return_state = "hub"
        if not isinstance(result, dict):
            self.status_text = "Сводка задания не была сохранена."
            self.summary_text = "Нажми Enter, чтобы вернуться в хаб."
            self.result_title = "Отчет"
            return

        if self._is_legacy_result(result):
            self._load_legacy_result(result)
            return

        success = bool(result.get("success"))
        mission_key = result.get("mission_key")
        coverage_ratio = result.get("coverage_ratio")
        actions_used = result.get("actions_used")
        action_budget = result.get("action_budget")
        time_remaining = result.get("time_remaining")
        collisions = result.get("collisions")
        storm_mode = result.get("storm_mode")

        mission_label = str(mission_key) if isinstance(mission_key, str) else "неизвестное задание"
        storm_text = str(storm_mode) if isinstance(storm_mode, str) else "нет"

        if success:
            self.result_title = "Задание выполнено"
            self.status_text = "Цель задания достигнута. Возвращайся в хаб за следующим поручением."
        else:
            self.result_title = "Задание провалено"
            self.status_text = "Цель задания не достигнута. Вернись в хаб и попробуй другую конфигурацию или маршрут."

        summary_parts = [f"Задание: {mission_label}.", f"Режим шторма: {storm_text}."]
        if isinstance(coverage_ratio, (int, float)):
            summary_parts.append(f"Покрытие: {coverage_ratio:.0%}.")
        if isinstance(actions_used, int) and isinstance(action_budget, int):
            summary_parts.append(f"Действия: {actions_used}/{action_budget}.")
        if isinstance(time_remaining, (int, float)):
            summary_parts.append(f"Оставшееся время: {time_remaining:.1f} c.")
        if isinstance(collisions, int):
            summary_parts.append(f"Столкновения: {collisions}.")
        self.summary_text = " ".join(summary_parts)

    def handle_event(self, event: pygame.event.Event) -> StateResult | None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
            self.shared_data.pop("active_npc_key", None)
            self.shared_data.pop("selected_mission_key", None)
            self.shared_data.pop("storm_mode", None)
            self.shared_data.pop("mission_status", None)
            return StateResult(next_state=self.return_state)
        return None

    def _is_legacy_result(self, result: dict[object, object]) -> bool:
        return "mission_key" not in result and (
            "battery_remaining" in result or "selected_modules" in result
        )

    def _load_legacy_result(self, result: dict[object, object]) -> None:
        self.return_state = "menu"
        success = bool(result.get("success"))
        battery_remaining = result.get("battery_remaining")
        selected_modules = result.get("selected_modules")
        module_text = ", ".join(selected_modules) if isinstance(selected_modules, tuple) and selected_modules else "нет"
        battery_text = f"{battery_remaining:.1f}" if isinstance(battery_remaining, (int, float)) else "--"

        if success:
            self.result_title = "Задание выполнено"
            self.status_text = "Релейный узел снова в сети. Можно вернуться в меню и начать новую сессию."
        else:
            self.result_title = "Задание провалено"
            self.status_text = "Миссия завершилась без захвата релейного узла."

        self.summary_text = f"Остаток батареи: {battery_text}. Выбранные модули: {module_text}."

    def update(self, dt: float) -> StateResult | None:
        return None

    def render(self, surface: pygame.Surface) -> None:
        surface.fill(BG)
        width, height = surface.get_size()

        title_font = pygame.font.Font(None, 80)
        body_font = pygame.font.Font(None, 34)
        small_font = pygame.font.Font(None, 28)

        title = title_font.render("Итоги задания", True, TEXT)
        surface.blit(title, title.get_rect(center=(width // 2, 74)))

        panel_rect = pygame.Rect(120, 150, width - 240, 360)
        draw_panel(surface, panel_rect, fill_color=PANEL, border_color=ACCENT, radius=18)

        result_surface = body_font.render(self.result_title, True, WARN)
        surface.blit(result_surface, result_surface.get_rect(center=(width // 2, 220)))

        text_rect = pygame.Rect(panel_rect.left + 36, 270, panel_rect.width - 72, 150)
        draw_wrapped_text(surface, self.status_text, body_font, TEXT, text_rect)
        draw_wrapped_text(surface, self.summary_text, small_font, ICE, pygame.Rect(panel_rect.left + 36, 390, panel_rect.width - 72, 60))

        destination = "меню" if self.return_state == "menu" else "хаб"
        hint = small_font.render(f"Нажми Enter, чтобы вернуться в {destination}.", True, WARN)
        surface.blit(hint, hint.get_rect(center=(width // 2, height - 92)))
