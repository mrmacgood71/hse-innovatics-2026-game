from __future__ import annotations

from collections.abc import MutableMapping

import pygame

from meridex_alpha.constants import ACCENT, BG, ICE, PANEL, TEXT, WARN
from meridex_alpha.loadout import BASE_PROFILE
from meridex_alpha.missions.warehouse import WarehouseRuntime
from meridex_alpha.models import RobotProfile
from meridex_alpha.states.base import BaseState, StateResult
from meridex_alpha.ui import draw_panel, draw_tiled_background, draw_wrapped_text, load_scaled_sprite


class WarehouseState(BaseState):
    name = "warehouse_pressure"

    def __init__(self, shared_data: MutableMapping[str, object]) -> None:
        self.shared_data = shared_data
        self.runtime = WarehouseRuntime()
        self.active_keys: set[int] = set()
        self.status_text = ""
        self.is_resolved = False

    def enter(self) -> None:
        storm_mode = self.shared_data.get("storm_mode")
        mode = storm_mode if isinstance(storm_mode, str) else "none"
        robot_profile = self.shared_data.get("robot_profile")
        profile = robot_profile if isinstance(robot_profile, RobotProfile) else BASE_PROFILE
        self.runtime = WarehouseRuntime(storm_mode=mode, robot_profile=profile)
        self.active_keys.clear()
        self.is_resolved = False
        self.status_text = "Веди платформу по коридору, не задевай стеллажи и полностью остановись в зоне разгрузки."

    def handle_event(self, event: pygame.event.Event) -> StateResult | None:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return StateResult(next_state="hub")
            self.active_keys.add(event.key)
        elif event.type == pygame.KEYUP:
            self.active_keys.discard(event.key)
        return None

    def update(self, dt: float) -> StateResult | None:
        if self.is_resolved:
            return None

        input_x, input_y = self._active_input()
        self.runtime.step(input_x, input_y, dt)

        if self.runtime.is_success():
            self.shared_data["mission_result"] = {
                "mission_key": "warehouse_pressure",
                "success": True,
                "time_remaining": round(self.runtime.time_remaining, 2),
                "collisions": self.runtime.collisions,
                "storm_mode": self.runtime.storm_mode,
            }
            self.shared_data["mission_status"] = "completed"
            return StateResult(next_state="debrief")
        elif self.runtime.is_failed():
            self.shared_data["mission_result"] = {
                "mission_key": "warehouse_pressure",
                "success": False,
                "time_remaining": round(self.runtime.time_remaining, 2),
                "collisions": self.runtime.collisions,
                "storm_mode": self.runtime.storm_mode,
            }
            self.shared_data["mission_status"] = "failed"
            return StateResult(next_state="debrief")
        return None

    def render(self, surface: pygame.Surface) -> None:
        surface.fill(BG)
        width, height = surface.get_size()

        title_font = pygame.font.Font(None, 70)
        body_font = pygame.font.Font(None, 30)
        small_font = pygame.font.Font(None, 24)

        title = title_font.render("Склад под давлением", True, TEXT)
        surface.blit(title, title.get_rect(center=(width // 2, 64)))

        map_rect = pygame.Rect(70, 120, 780, 520)
        draw_panel(surface, map_rect, fill_color=PANEL, border_color=ACCENT)
        self._draw_map(surface, map_rect)

        info_rect = pygame.Rect(890, 120, 320, 520)
        draw_panel(surface, info_rect, fill_color=PANEL, border_color=ICE)

        draw_wrapped_text(
            surface,
            "Доведи платформу до выделенной зоны. Слишком ранняя остановка и удары о препятствия считаются ошибкой.",
            body_font,
            TEXT,
            pygame.Rect(info_rect.left + 20, info_rect.top + 24, info_rect.width - 40, 120),
        )
        draw_wrapped_text(
            surface,
            f"Режим шторма: {self.runtime.storm_mode}",
            body_font,
            WARN if self.runtime.storm_mode == "storm" else ICE,
            pygame.Rect(info_rect.left + 20, info_rect.top + 160, info_rect.width - 40, 30),
        )
        draw_wrapped_text(
            surface,
            f"Время: {self.runtime.time_remaining:.1f} c",
            body_font,
            TEXT,
            pygame.Rect(info_rect.left + 20, info_rect.top + 210, info_rect.width - 40, 30),
        )
        draw_wrapped_text(
            surface,
            f"Столкновения: {self.runtime.collisions}/{self.runtime.collision_limit}",
            body_font,
            WARN if self.runtime.collisions else TEXT,
            pygame.Rect(info_rect.left + 20, info_rect.top + 250, info_rect.width - 40, 30),
        )
        draw_wrapped_text(
            surface,
            f"Скорость: {abs(self.runtime.velocity_x):.1f}, {abs(self.runtime.velocity_y):.1f}",
            body_font,
            TEXT,
            pygame.Rect(info_rect.left + 20, info_rect.top + 290, info_rect.width - 40, 30),
        )
        draw_wrapped_text(
            surface,
            f"Профиль: мобильность {self.runtime.robot_profile.mobility}, устойчивость {self.runtime.robot_profile.stability}",
            body_font,
            TEXT,
            pygame.Rect(info_rect.left + 20, info_rect.top + 330, info_rect.width - 40, 48),
        )
        draw_wrapped_text(
            surface,
            self.status_text,
            body_font,
            TEXT,
            pygame.Rect(info_rect.left + 20, info_rect.top + 390, info_rect.width - 40, 100),
        )

        hint = small_font.render("WASD или стрелки двигают платформу. Esc возвращает в хаб.", True, ICE)
        surface.blit(hint, hint.get_rect(center=(width // 2, height - 38)))

    def _active_input(self) -> tuple[float, float]:
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

    def _draw_map(self, surface: pygame.Surface, map_rect: pygame.Rect) -> None:
        left, top, width, height = map_rect
        arena_rect = map_rect.inflate(-24, -24)
        pygame.draw.rect(surface, (38, 46, 58), arena_rect, border_radius=18)
        tiled = load_scaled_sprite("warehouse_tiles", (56, 56))
        if tiled is not None:
            floor_tile = tiled.copy()
            dim = pygame.Surface(floor_tile.get_size(), pygame.SRCALPHA)
            dim.fill((18, 22, 26, 170))
            floor_tile.blit(dim, (0, 0))
            draw_tiled_background(
                surface,
                floor_tile,
                arena_rect,
                fallback_color=(38, 46, 58),
                tile_size=(56, 56),
            )

        for obstacle in self.runtime.obstacles:
            obstacle_rect = self._world_rect_to_screen(obstacle, map_rect)
            scaled_height = min(obstacle_rect.height, 42)
            obstacle_sprite = load_scaled_sprite("warehouse_obstacle", (34, scaled_height))
            if obstacle_sprite is not None:
                for top in range(obstacle_rect.top, obstacle_rect.bottom, scaled_height + 8):
                    sprite_rect = obstacle_sprite.get_rect(midtop=(obstacle_rect.centerx, top))
                    surface.blit(obstacle_sprite, sprite_rect)
            else:
                pygame.draw.rect(surface, (92, 86, 74), obstacle_rect, border_radius=12)
            pygame.draw.rect(surface, (156, 122, 88), obstacle_rect, width=2, border_radius=12)

        goal_rect = self._world_rect_to_screen(self.runtime.goal_rect, map_rect)
        pygame.draw.rect(surface, (76, 130, 110), goal_rect, border_radius=12)
        pygame.draw.rect(surface, ACCENT, goal_rect, width=3, border_radius=12)

        robot_pos = self._world_point_to_screen(self.runtime.position, map_rect)
        robot_sprite = load_scaled_sprite("warehouse_robot", (36, 34))
        if robot_sprite is not None:
            surface.blit(robot_sprite, robot_sprite.get_rect(center=robot_pos))
        else:
            pygame.draw.circle(surface, ICE, robot_pos, 16)
            pygame.draw.circle(surface, TEXT, robot_pos, 16, width=2)

        if self.runtime.storm_mode == "storm":
            overlay = load_scaled_sprite("storm_overlay", (arena_rect.width, arena_rect.height))
            if overlay is not None:
                muted = overlay.copy()
                fade = pygame.Surface(muted.get_size(), pygame.SRCALPHA)
                fade.fill((34, 52, 66, 80))
                muted.blit(fade, (0, 0))
                surface.blit(muted, arena_rect)

    def _world_rect_to_screen(
        self,
        rect: tuple[float, float, float, float],
        map_rect: pygame.Rect,
    ) -> pygame.Rect:
        left, top, width, height = rect
        start = self._world_point_to_screen((left, top), map_rect)
        end = self._world_point_to_screen((left + width, top + height), map_rect)
        return pygame.Rect(start, (end[0] - start[0], end[1] - start[1]))

    def _world_point_to_screen(self, point: tuple[float, float], map_rect: pygame.Rect) -> tuple[int, int]:
        x_scale = map_rect.width / 1280.0
        y_scale = map_rect.height / 720.0
        return (
            int(map_rect.left + point[0] * x_scale),
            int(map_rect.top + point[1] * y_scale),
        )
