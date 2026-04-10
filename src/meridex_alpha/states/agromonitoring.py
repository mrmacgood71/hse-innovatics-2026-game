from __future__ import annotations

from collections.abc import MutableMapping

import pygame

from meridex_alpha.constants import ACCENT, BG, ICE, PANEL, TEXT, WARN
from meridex_alpha.missions.agromonitoring import AgromonitoringRuntime
from meridex_alpha.states.base import BaseState, StateResult
from meridex_alpha.ui import draw_panel, draw_tiled_background, draw_wrapped_text, load_scaled_sprite


class AgromonitoringState(BaseState):
    name = "agromonitoring"

    def __init__(self, shared_data: MutableMapping[str, object]) -> None:
        self.shared_data = shared_data
        self.runtime = AgromonitoringRuntime()
        self.cursor = (0, 0)
        self.status_text = ""
        self.phase = "planning"

    def enter(self) -> None:
        storm_mode = self.shared_data.get("storm_mode")
        mode = storm_mode if isinstance(storm_mode, str) else "none"
        self.runtime = AgromonitoringRuntime(storm_mode=mode)
        self.cursor = (0, 0)
        self.phase = "planning"
        self.status_text = "Построй маршрут облета. Стрелки двигают курсор, пробел добавляет шаг, Enter запускает облет."

    def handle_event(self, event: pygame.event.Event) -> StateResult | None:
        if event.type != pygame.KEYDOWN:
            return None

        if event.key == pygame.K_ESCAPE:
            return StateResult(next_state="hub")
        if self.phase == "flight":
            return None

        x, y = self.cursor
        if event.key in (pygame.K_LEFT, pygame.K_a):
            self.cursor = ((x - 1) % self.runtime.grid_width, y)
        elif event.key in (pygame.K_RIGHT, pygame.K_d):
            self.cursor = ((x + 1) % self.runtime.grid_width, y)
        elif event.key in (pygame.K_UP, pygame.K_w):
            self.cursor = (x, (y - 1) % self.runtime.grid_height)
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self.cursor = (x, (y + 1) % self.runtime.grid_height)
        elif event.key == pygame.K_SPACE:
            before = len(self.runtime.planned_route)
            self.runtime.add_route_cell(x, y)
            if len(self.runtime.planned_route) == before:
                if (x, y) in self.runtime.blocked_cells:
                    self.status_text = "Эта клетка занята препятствием. Ее нельзя добавить в маршрут."
                else:
                    self.status_text = "Следующий шаг можно добавить только в соседнюю клетку."
            else:
                self.status_text = f"Шаг {len(self.runtime.planned_route)} добавлен в маршрут."
        elif event.key == pygame.K_BACKSPACE:
            self.runtime.remove_last_route_cell()
            self.status_text = "Последний шаг маршрута удален."
        elif event.key == pygame.K_RETURN:
            if not self.runtime.start_flight():
                self.status_text = "Сначала добавь хотя бы одну клетку в маршрут."
                return None
            self.phase = "flight"
            self.status_text = "Маршрут запущен. Дрон выполняет облет поля."

        return None

    def _resolve_mission(self) -> StateResult | None:
        success = self.runtime.is_success()
        self.shared_data["mission_result"] = {
            "mission_key": "agromonitoring",
            "success": success,
            "coverage_ratio": round(self.runtime.coverage_ratio(), 2),
            "actions_used": self.runtime.actions_used,
            "action_budget": self.runtime.action_budget,
            "storm_mode": self.runtime.storm_mode,
            "route_length": len(self.runtime.planned_route),
        }
        self.shared_data["mission_status"] = "completed" if success else "failed"
        return StateResult(next_state="debrief")

    def update(self, dt: float) -> StateResult | None:
        if self.phase == "flight":
            self.runtime.step_flight(dt)
            if self.runtime.flight_complete:
                return self._resolve_mission()
        return None

    def render(self, surface: pygame.Surface) -> None:
        surface.fill(BG)
        width, height = surface.get_size()

        title_font = pygame.font.Font(None, 70)
        body_font = pygame.font.Font(None, 30)
        small_font = pygame.font.Font(None, 24)

        title = title_font.render("Агромониторинг", True, TEXT)
        surface.blit(title, title.get_rect(center=(width // 2, 64)))

        board_rect = pygame.Rect(90, 120, 720, 470)
        draw_panel(surface, board_rect, fill_color=PANEL, border_color=ACCENT)
        inner_rect = board_rect.inflate(-16, -16)
        pygame.draw.rect(surface, (88, 121, 74), inner_rect, border_radius=12)
        tiled = load_scaled_sprite("agro_field_tiles", (72, 72))
        if tiled is not None:
            tile = tiled.copy()
            dim = pygame.Surface(tile.get_size(), pygame.SRCALPHA)
            dim.fill((22, 42, 16, 86))
            tile.blit(dim, (0, 0))
            draw_tiled_background(
                surface,
                tile,
                inner_rect,
                fallback_color=(88, 121, 74),
                tile_size=(72, 72),
            )
        self._draw_field_background(surface, inner_rect)

        self._draw_grid(surface, board_rect)

        info_rect = pygame.Rect(850, 120, 340, 470)
        draw_panel(surface, info_rect, fill_color=PANEL, border_color=ICE)

        draw_wrapped_text(
            surface,
            "Покрой 8 целевых участков за 10 шагов. Преграды блокируют часть поля, поэтому маршрут нужно планировать заранее.",
            body_font,
            TEXT,
            pygame.Rect(info_rect.left + 20, info_rect.top + 24, info_rect.width - 40, 72),
        )

        draw_wrapped_text(
            surface,
            f"Режим шторма: {self.runtime.storm_mode}",
            body_font,
            WARN if self.runtime.storm_mode == "storm" else ICE,
            pygame.Rect(info_rect.left + 20, info_rect.top + 112, info_rect.width - 40, 32),
        )
        draw_wrapped_text(
            surface,
            f"Цели покрыты: {len(self.runtime.covered_cells.intersection(self.runtime.target_cells))}/{len(self.runtime.required_cells())}",
            body_font,
            TEXT,
            pygame.Rect(info_rect.left + 20, info_rect.top + 164, info_rect.width - 40, 32),
        )
        draw_wrapped_text(
            surface,
            f"Шаги маршрута: {self.runtime.actions_used}/{self.runtime.action_budget}",
            body_font,
            WARN if self.runtime.has_exceeded_budget() else TEXT,
            pygame.Rect(info_rect.left + 20, info_rect.top + 208, info_rect.width - 40, 32),
        )
        draw_wrapped_text(
            surface,
            f"Преграды: {len(self.runtime.blocked_cells)}",
            body_font,
            WARN,
            pygame.Rect(info_rect.left + 20, info_rect.top + 248, info_rect.width - 40, 32),
        )
        draw_wrapped_text(
            surface,
            f"Фаза: {'облет' if self.phase == 'flight' else 'планирование'}",
            body_font,
            ACCENT if self.phase == "flight" else ICE,
            pygame.Rect(info_rect.left + 20, info_rect.top + 288, info_rect.width - 40, 32),
        )

        draw_wrapped_text(
            surface,
            self.status_text,
            body_font,
            TEXT,
            pygame.Rect(info_rect.left + 20, info_rect.top + 340, info_rect.width - 40, 96),
        )

        hint = small_font.render("Пробел добавляет шаг в соседнюю клетку. Backspace удаляет. Enter запускает облет.", True, ICE)
        surface.blit(hint, hint.get_rect(center=(width // 2, height - 38)))

    def _draw_field_background(self, surface: pygame.Surface, inner_rect: pygame.Rect) -> None:
        band_height = inner_rect.height // 4
        colors = ((124, 161, 84), (114, 145, 76), (135, 171, 91), (111, 148, 79))
        for index, color in enumerate(colors):
            row_rect = pygame.Rect(inner_rect.left, inner_rect.top + index * band_height, inner_rect.width, band_height)
            pygame.draw.rect(surface, color, row_rect)
        for offset in range(0, inner_rect.width, 60):
            pygame.draw.line(
                surface,
                (156, 191, 116),
                (inner_rect.left + offset, inner_rect.top),
                (inner_rect.left + offset + 16, inner_rect.bottom),
                2,
            )

    def _draw_grid(self, surface: pygame.Surface, board_rect: pygame.Rect) -> None:
        cell_size = min(board_rect.width // self.runtime.grid_width, board_rect.height // self.runtime.grid_height) - 18
        total_width = self.runtime.grid_width * cell_size + (self.runtime.grid_width - 1) * 12
        total_height = self.runtime.grid_height * cell_size + (self.runtime.grid_height - 1) * 12
        origin_x = board_rect.left + (board_rect.width - total_width) // 2
        origin_y = board_rect.top + (board_rect.height - total_height) // 2
        route_positions: dict[tuple[int, int], int] = {}
        for index, cell in enumerate(self.runtime.planned_route, start=1):
            route_positions[cell] = index
        marker_font = pygame.font.Font(None, 28)

        for y in range(self.runtime.grid_height):
            for x in range(self.runtime.grid_width):
                left = origin_x + x * (cell_size + 12)
                top = origin_y + y * (cell_size + 12)
                rect = pygame.Rect(left, top, cell_size, cell_size)
                cell = (x, y)
                fill = (18, 26, 32, 120)
                cell_overlay = pygame.Surface(rect.size, pygame.SRCALPHA)
                cell_overlay.fill(fill)
                surface.blit(cell_overlay, rect)
                if cell in self.runtime.target_cells:
                    target_overlay = pygame.Surface(rect.size, pygame.SRCALPHA)
                    target_overlay.fill((203, 183, 92, 130))
                    surface.blit(target_overlay, rect)
                if cell in self.runtime.blocked_cells:
                    blocked_overlay = pygame.Surface(rect.size, pygame.SRCALPHA)
                    blocked_overlay.fill((120, 52, 42, 168))
                    surface.blit(blocked_overlay, rect)
                if cell in self.runtime.covered_cells:
                    covered_overlay = pygame.Surface(rect.size, pygame.SRCALPHA)
                    covered_overlay.fill((105, 182, 114, 170))
                    surface.blit(covered_overlay, rect)
                if cell in route_positions and cell not in self.runtime.covered_cells:
                    planned_overlay = pygame.Surface(rect.size, pygame.SRCALPHA)
                    planned_overlay.fill((86, 124, 191, 120))
                    surface.blit(planned_overlay, rect)
                current_flight_cell = self.runtime.current_flight_cell
                is_active_flight_cell = self.phase == "flight" and cell == current_flight_cell
                border = ACCENT if is_active_flight_cell else WARN if cell == self.cursor and self.phase == "planning" else TEXT
                pygame.draw.rect(surface, border, rect, width=3 if cell == self.cursor else 1, border_radius=12)
                if cell in self.runtime.blocked_cells:
                    pygame.draw.line(surface, TEXT, rect.topleft, rect.bottomright, 3)
                    pygame.draw.line(surface, TEXT, rect.topright, rect.bottomleft, 3)
                if cell == self.cursor and self.phase == "planning":
                    marker = load_scaled_sprite("agro_drone", (22, 22))
                    if marker is not None:
                        surface.blit(marker, marker.get_rect(center=rect.center))
                route_step = route_positions.get(cell)
                if route_step is not None:
                    text_surface = marker_font.render(str(route_step), True, TEXT)
                    surface.blit(text_surface, text_surface.get_rect(center=rect.center))
                if is_active_flight_cell:
                    marker = load_scaled_sprite("agro_drone", (24, 24))
                    if marker is not None:
                        surface.blit(marker, marker.get_rect(center=(rect.centerx, rect.centery - 2)))

        if self.runtime.storm_mode == "storm":
            overlay = load_scaled_sprite("storm_overlay", (board_rect.width - 16, board_rect.height - 16))
            if overlay is not None:
                muted = overlay.copy()
                fade = pygame.Surface(muted.get_size(), pygame.SRCALPHA)
                fade.fill((40, 60, 78, 90))
                muted.blit(fade, (0, 0))
                surface.blit(muted, (board_rect.left + 8, board_rect.top + 8))
