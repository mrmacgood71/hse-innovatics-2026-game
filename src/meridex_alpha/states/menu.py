from __future__ import annotations

import pygame

from meridex_alpha.constants import ACCENT, BG, PANEL, TEXT, WARN
from meridex_alpha.states.base import BaseState, StateResult


class MenuState(BaseState):
    name = "menu"

    def enter(self) -> None:
        pass

    def handle_event(self, event: pygame.event.Event) -> StateResult | None:
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_SPACE):
            return StateResult(next_state="hub")
        return None

    def update(self, dt: float) -> StateResult | None:
        return None

    def render(self, surface: pygame.Surface) -> None:
        surface.fill(BG)
        width, height = surface.get_size()

        panel_rect = pygame.Rect(120, 140, width - 240, 320)
        pygame.draw.rect(surface, PANEL, panel_rect, border_radius=18)
        pygame.draw.rect(surface, ACCENT, panel_rect, width=2, border_radius=18)

        title_font = pygame.font.Font(None, 96)
        body_font = pygame.font.Font(None, 40)
        hint_font = pygame.font.Font(None, 28)

        title = title_font.render("MERIDEX Альфа", True, TEXT)
        prompt = body_font.render("Нажми Enter или Space, чтобы начать", True, TEXT)
        status = hint_font.render("Следующий экран: хаб миссий", True, WARN)
        footer = hint_font.render("Одиночный 2D-прототип на pygame", True, ACCENT)

        surface.blit(title, title.get_rect(center=(width // 2, 250)))
        surface.blit(prompt, prompt.get_rect(center=(width // 2, 360)))
        surface.blit(status, status.get_rect(center=(width // 2, 420)))
        surface.blit(footer, footer.get_rect(center=(width // 2, height - 90)))
