from __future__ import annotations

from collections.abc import MutableMapping

import pygame

from meridex_alpha.constants import ACCENT, BG, ICE, PANEL, TEXT, WARN
from meridex_alpha.hub import HubNpc, HubRuntime, PATH_HALF_HEIGHT, ROAD_Y
from meridex_alpha.states.base import BaseState, StateResult
from meridex_alpha.ui import draw_wrapped_text, load_scaled_sprite, load_sprite


class HubState(BaseState):
    name = "hub"

    def __init__(self, shared_data: MutableMapping[str, object]) -> None:
        self.shared_data = shared_data
        runtime = shared_data.get("hub_runtime")
        self.runtime = runtime if isinstance(runtime, HubRuntime) else HubRuntime()

    def enter(self) -> None:
        runtime = self.shared_data.get("hub_runtime")
        if isinstance(runtime, HubRuntime):
            self.runtime = runtime
        else:
            self.runtime = HubRuntime()
        self.shared_data["hub_runtime"] = self.runtime
        self.runtime.active_keys.clear()

    def handle_event(self, event: pygame.event.Event) -> StateResult | None:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_e:
                nearest_npc = self.runtime.nearest_npc()
                if nearest_npc is not None:
                    self.shared_data["active_npc_key"] = nearest_npc.key
                    return StateResult(next_state="mission_select")
            self.runtime.set_key_state(event.key, True)
        elif event.type == pygame.KEYUP:
            self.runtime.set_key_state(event.key, False)
        return None

    def update(self, dt: float) -> StateResult | None:
        self.runtime.update(dt)
        return None

    def render(self, surface: pygame.Surface) -> None:
        surface.fill(BG)
        width, height = surface.get_size()
        small_font = pygame.font.Font(None, 24)
        body_font = pygame.font.Font(None, 32)

        self._draw_sky(surface)

        trail_center_y = int(height * 0.66)
        trail_half_height = int(height * 0.35)
        trail_rect = pygame.Rect(0, trail_center_y - trail_half_height, width, trail_half_height * 2)
        self._draw_path_scene(surface, trail_rect)

        visible_npcs = [npc for npc in self.runtime.npc_stream if -80 <= self._screen_x(npc.position[0]) <= width + 80]
        nearest_npc = self.runtime.nearest_npc()
        for npc in visible_npcs:
            self._draw_npc(surface, npc, trail_rect, small_font, npc == nearest_npc)

        player_pos = (self._screen_x(self.runtime.player_position[0]), self._screen_y(self.runtime.player_position[1], trail_rect.centery))
        shadow_rect = pygame.Rect(0, 0, 38, 12)
        shadow_rect.center = (player_pos[0], player_pos[1] + 24)
        pygame.draw.ellipse(surface, (8, 10, 12), shadow_rect)
        player_sprite = load_scaled_sprite("player_idle", (42, 42))
        if player_sprite is not None:
            surface.blit(player_sprite, player_sprite.get_rect(center=player_pos))
        else:
            pygame.draw.circle(surface, TEXT, player_pos, 13)
            pygame.draw.circle(surface, PANEL, player_pos, 13, width=2)

        if nearest_npc is not None:
            prompt_rect = pygame.Rect(24, 24, 420, 70)
            pygame.draw.rect(surface, (16, 22, 30), prompt_rect, border_radius=14)
            pygame.draw.rect(surface, ACCENT, prompt_rect, width=2, border_radius=14)
            draw_wrapped_text(
                surface,
                f"E: {nearest_npc.label} — {nearest_npc.role}",
                body_font,
                TEXT,
                pygame.Rect(prompt_rect.left + 16, prompt_rect.top + 16, prompt_rect.width - 32, 38),
            )
        else:
            hint = small_font.render("Иди по тропе, смещайся вверх и вниз и жми E рядом со специалистом.", True, ICE)
            surface.blit(hint, hint.get_rect(topleft=(26, 28)))

    def _screen_x(self, world_x: float) -> int:
        return int(world_x - self.runtime.camera_x + 180)

    def _screen_y(self, world_y: float, road_center_y: int) -> int:
        vertical_offset = int((world_y - ROAD_Y) * 1.4)
        return road_center_y + vertical_offset

    def _draw_path_scene(self, surface: pygame.Surface, trail_rect: pygame.Rect) -> None:
        pygame.draw.rect(surface, (133, 178, 108), (0, trail_rect.top - 48, surface.get_width(), trail_rect.height + 96))
        pygame.draw.rect(surface, (104, 149, 82), (0, trail_rect.top - 16, surface.get_width(), 18))
        pygame.draw.rect(surface, (96, 137, 75), (0, trail_rect.bottom + 4, surface.get_width(), 22))

        sheet = load_sprite("hub_ground")
        dirt_tiles = self._path_tiles(sheet)
        tile_width = 128
        tile_height = max(72, trail_rect.height // 6)
        dirt_tiles = tuple(pygame.transform.scale(tile, (tile_width, tile_height)) for tile in dirt_tiles)
        offset = int(self.runtime.camera_x) % tile_width
        row_count = max(4, trail_rect.height // tile_height)
        for row in range(row_count):
            row_top = trail_rect.top + 12 + row * tile_height
            for left in range(-offset - tile_width, surface.get_width() + tile_width, tile_width):
                tile = dirt_tiles[(row + (left // tile_width)) % len(dirt_tiles)]
                tile_rect = tile.get_rect(topleft=(left, row_top))
                surface.blit(tile, tile_rect)

        top_edge = [(0, trail_rect.top + 10), (surface.get_width(), trail_rect.top + 2), (surface.get_width(), trail_rect.top + 24), (0, trail_rect.top + 34)]
        bottom_edge = [
            (0, trail_rect.bottom - 16),
            (surface.get_width(), trail_rect.bottom - 6),
            (surface.get_width(), trail_rect.bottom + 16),
            (0, trail_rect.bottom + 8),
        ]
        pygame.draw.polygon(surface, (211, 187, 140), top_edge)
        pygame.draw.polygon(surface, (181, 152, 110), bottom_edge)
        pygame.draw.rect(surface, (86, 121, 67), (0, trail_rect.top - 10, surface.get_width(), 8))
        pygame.draw.rect(surface, (77, 110, 58), (0, trail_rect.bottom + 8, surface.get_width(), 10))
        for left in range(-offset - 120, surface.get_width() + 120, 160):
            bush_rect_top = pygame.Rect(left, trail_rect.top - 18, 56, 18)
            bush_rect_bottom = pygame.Rect(left + 64, trail_rect.bottom + 8, 62, 20)
            pygame.draw.ellipse(surface, (63, 98, 54), bush_rect_top)
            pygame.draw.ellipse(surface, (58, 91, 49), bush_rect_bottom)

    def _draw_sky(self, surface: pygame.Surface) -> None:
        width, height = surface.get_size()
        sky_height = int(height * 0.38)
        for index in range(sky_height):
            ratio = index / max(1, sky_height - 1)
            red = int(118 + 44 * ratio)
            green = int(173 + 40 * ratio)
            blue = int(226 + 18 * ratio)
            pygame.draw.line(surface, (red, green, blue), (0, index), (width, index))

        cloud_scroll = int(self.runtime.camera_x * 0.08)
        cloud_data = (
            (120, 72, 148, 42),
            (360, 118, 176, 48),
            (690, 84, 164, 44),
            (980, 136, 188, 52),
        )
        for origin_x, origin_y, cloud_width, cloud_height in cloud_data:
            screen_x = ((origin_x - cloud_scroll) % (width + 280)) - 140
            self._draw_cloud(surface, screen_x, origin_y, cloud_width, cloud_height)

    def _draw_cloud(self, surface: pygame.Surface, x: int, y: int, width: int, height: int) -> None:
        cloud_surface = pygame.Surface((width, height), pygame.SRCALPHA)
        pygame.draw.ellipse(cloud_surface, (255, 255, 255, 160), (0, height // 3, width // 2, height // 2))
        pygame.draw.ellipse(cloud_surface, (250, 252, 255, 180), (width // 5, 0, width // 2, height // 2 + 10))
        pygame.draw.ellipse(cloud_surface, (244, 248, 255, 172), (width // 2, height // 4, width // 2 - 8, height // 2))
        surface.blit(cloud_surface, (x, y))

    def _path_tiles(self, sheet: pygame.Surface | None) -> tuple[pygame.Surface, ...]:
        if sheet is None:
            fallback = pygame.Surface((96, 58))
            fallback.fill((176, 145, 102))
            return (fallback,)
        tile_rects = (
            pygame.Rect(0, 0, 16, 16),
            pygame.Rect(16, 0, 16, 16),
            pygame.Rect(32, 0, 16, 16),
        )
        tiles: list[pygame.Surface] = []
        for rect in tile_rects:
            tile = pygame.Surface(rect.size, pygame.SRCALPHA, 32)
            tile.blit(sheet, (0, 0), rect)
            tiles.append(pygame.transform.scale(tile, (96, 58)))
        return tuple(tiles)

    def _draw_npc(
        self,
        surface: pygame.Surface,
        npc: HubNpc,
        road_rect: pygame.Rect,
        font: pygame.font.Font,
        is_nearest: bool,
    ) -> None:
        screen_x = self._screen_x(npc.position[0])
        screen_y = self._screen_y(npc.position[1], road_rect.centery)
        sprite = load_scaled_sprite(self._npc_asset_key(npc.key), (40, 40))
        marker_color = WARN if is_nearest else ACCENT
        shadow_rect = pygame.Rect(0, 0, 34, 10)
        shadow_rect.center = (screen_x, screen_y + 24)
        pygame.draw.ellipse(surface, (8, 10, 12), shadow_rect)
        if sprite is not None:
            surface.blit(sprite, sprite.get_rect(center=(screen_x, screen_y)))
        else:
            pygame.draw.circle(surface, marker_color, (screen_x, screen_y), 13)
        sign_y = screen_y - 64 if screen_y < road_rect.centery else screen_y + 28
        sign_rect = pygame.Rect(screen_x - 64, sign_y, 128, 44)
        panel_color = (26, 33, 42) if not is_nearest else (36, 44, 52)
        pygame.draw.rect(surface, panel_color, sign_rect, border_radius=12)
        pygame.draw.rect(surface, marker_color, sign_rect, width=2, border_radius=12)
        label = font.render(npc.label, True, TEXT)
        surface.blit(label, label.get_rect(center=sign_rect.center))

    def _npc_asset_key(self, npc_key: str) -> str:
        if npc_key == "agri_lead":
            return "npc_field_lead"
        return "npc_warehouse_chief"
