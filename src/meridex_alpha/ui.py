from __future__ import annotations

from collections.abc import Mapping, Sequence
from functools import lru_cache

import pygame

from meridex_alpha.assets import asset_path
from meridex_alpha.constants import ACCENT, ICE, PANEL, TEXT, WARN


def draw_panel(
    surface: pygame.Surface,
    rect: pygame.Rect,
    *,
    fill_color: tuple[int, int, int] = PANEL,
    border_color: tuple[int, int, int] = ACCENT,
    border_width: int = 2,
    radius: int = 16,
) -> None:
    pygame.draw.rect(surface, fill_color, rect, border_radius=radius)
    pygame.draw.rect(surface, border_color, rect, width=border_width, border_radius=radius)


def draw_wrapped_text(
    surface: pygame.Surface,
    text: str,
    font: pygame.font.Font,
    color: tuple[int, int, int],
    rect: pygame.Rect,
    *,
    line_spacing: int = 4,
) -> int:
    words = text.split()
    if not words:
        return rect.top

    x = rect.left
    y = rect.top
    max_width = rect.width
    line_words: list[str] = []

    def flush_line(current_y: int, current_words: Sequence[str]) -> int:
        if not current_words:
            return current_y
        rendered = font.render(" ".join(current_words), True, color)
        surface.blit(rendered, (x, current_y))
        return current_y + rendered.get_height() + line_spacing

    for word in words:
        candidate_words = [*line_words, word]
        candidate_width = font.size(" ".join(candidate_words))[0]
        if candidate_width > max_width and line_words:
            y = flush_line(y, line_words)
            line_words = [word]
        else:
            line_words = candidate_words

    y = flush_line(y, line_words)
    return y


def draw_stat_list(
    surface: pygame.Surface,
    stats: Mapping[str, int],
    font: pygame.font.Font,
    rect: pygame.Rect,
    *,
    label_color: tuple[int, int, int] = TEXT,
    value_color: tuple[int, int, int] = ACCENT,
    row_spacing: int = 10,
) -> None:
    y = rect.top
    for label, value in stats.items():
        label_surface = font.render(label, True, label_color)
        value_surface = font.render(str(value), True, value_color)
        surface.blit(label_surface, (rect.left, y))
        surface.blit(value_surface, (rect.right - value_surface.get_width(), y))
        y += max(label_surface.get_height(), value_surface.get_height()) + row_spacing


def draw_label_value_block(
    surface: pygame.Surface,
    label: str,
    value: str,
    font: pygame.font.Font,
    rect: pygame.Rect,
    *,
    label_color: tuple[int, int, int] = TEXT,
    value_color: tuple[int, int, int] = ACCENT,
    line_spacing: int = 2,
) -> None:
    label_surface = font.render(label, True, label_color)
    value_surface = font.render(value, True, value_color)
    surface.blit(label_surface, (rect.left, rect.top))
    surface.blit(value_surface, (rect.left, rect.top + label_surface.get_height() + line_spacing))


def draw_meter(
    surface: pygame.Surface,
    label: str,
    value_text: str,
    ratio: float,
    font: pygame.font.Font,
    rect: pygame.Rect,
    *,
    fill_color: tuple[int, int, int] = ACCENT,
    track_color: tuple[int, int, int] = (18, 24, 36),
    border_color: tuple[int, int, int] = ICE,
    label_color: tuple[int, int, int] = TEXT,
    value_color: tuple[int, int, int] = TEXT,
) -> None:
    label_surface = font.render(label, True, label_color)
    value_surface = font.render(value_text, True, value_color)
    surface.blit(label_surface, (rect.left, rect.top))
    surface.blit(value_surface, (rect.right - value_surface.get_width(), rect.top))

    bar_top = rect.top + label_surface.get_height() + 5
    bar_height = max(8, min(12, rect.height - label_surface.get_height() - 5))
    bar_rect = pygame.Rect(rect.left, bar_top, rect.width, bar_height)
    pygame.draw.rect(surface, track_color, bar_rect, border_radius=bar_height // 2)
    filled_width = int(bar_rect.width * max(0.0, min(1.0, ratio)))
    if filled_width > 0:
        pygame.draw.rect(
            surface,
            fill_color,
            pygame.Rect(bar_rect.left, bar_rect.top, filled_width, bar_rect.height),
            border_radius=bar_height // 2,
        )
    pygame.draw.rect(surface, border_color, bar_rect, width=1, border_radius=bar_height // 2)


def draw_hint_row(
    surface: pygame.Surface,
    text: str,
    font: pygame.font.Font,
    rect: pygame.Rect,
    *,
    color: tuple[int, int, int] = WARN,
) -> None:
    rendered = font.render(text, True, color)
    surface.blit(rendered, rendered.get_rect(midleft=rect.midleft))


@lru_cache(maxsize=64)
def load_sprite(key: str) -> pygame.Surface | None:
    try:
        path = asset_path(key)
    except KeyError:
        return None
    if not path.exists():
        return None
    try:
        return _normalize_surface(pygame.image.load(str(path)))
    except pygame.error:
        return None


def load_scaled_sprite(key: str, size: tuple[int, int]) -> pygame.Surface | None:
    return _load_scaled_sprite_cached(key, size)


@lru_cache(maxsize=256)
def _load_scaled_sprite_cached(key: str, size: tuple[int, int]) -> pygame.Surface | None:
    sprite = load_sprite(key)
    if sprite is None:
        return None
    return pygame.transform.smoothscale(sprite, size)


def draw_tiled_background(
    surface: pygame.Surface,
    sprite: pygame.Surface | None,
    rect: pygame.Rect,
    *,
    fallback_color: tuple[int, int, int],
    tile_size: tuple[int, int] = (64, 64),
) -> None:
    if sprite is None:
        pygame.draw.rect(surface, fallback_color, rect, border_radius=12)
        return

    tile = sprite
    for top in range(rect.top, rect.bottom, tile.get_height()):
        for left in range(rect.left, rect.right, tile.get_width()):
            surface.blit(tile, (left, top))


def _normalize_surface(surface: pygame.Surface) -> pygame.Surface:
    if surface.get_bitsize() in (24, 32):
        return surface
    normalized = pygame.Surface(surface.get_size(), pygame.SRCALPHA, 32)
    normalized.blit(surface, (0, 0))
    return normalized
