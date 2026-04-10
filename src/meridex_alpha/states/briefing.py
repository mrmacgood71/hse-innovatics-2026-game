from __future__ import annotations

import pygame

from meridex_alpha.constants import ACCENT, BG, PANEL, TEXT, WARN
from meridex_alpha.states.base import BaseState, StateResult
from meridex_alpha.ui import draw_panel, draw_wrapped_text


class BriefingState(BaseState):
    name = "briefing"

    def enter(self) -> None:
        pass

    def handle_event(self, event: pygame.event.Event) -> StateResult | None:
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_SPACE):
            return StateResult(next_state="loadout")
        return None

    def update(self, dt: float) -> StateResult | None:
        return None

    def render(self, surface: pygame.Surface) -> None:
        surface.fill(BG)
        width, height = surface.get_size()

        title_font = pygame.font.Font(None, 88)
        body_font = pygame.font.Font(None, 34)
        hint_font = pygame.font.Font(None, 28)

        title = title_font.render("Cold Relay Briefing", True, TEXT)
        subtitle = body_font.render("Mission window open. Systems remain offline.", True, ACCENT)

        panel_rect = pygame.Rect(120, 150, width - 240, 360)
        draw_panel(surface, panel_rect, fill_color=PANEL, border_color=ACCENT, radius=18)

        surface.blit(title, title.get_rect(center=(width // 2, 210)))
        surface.blit(subtitle, subtitle.get_rect(center=(width // 2, 275)))

        text_rect = pygame.Rect(panel_rect.left + 36, 320, panel_rect.width - 72, 140)
        briefing_text = (
            "A cold relay has gone quiet beyond the ridge. "
            "Your robot is being prepped for a short survey run to restore signal and confirm the line is still alive. "
            "Move to loadout, choose the modules you want, and lock the profile before departure."
        )
        draw_wrapped_text(surface, briefing_text, body_font, TEXT, text_rect)

        hint = hint_font.render("Press Enter to continue to loadout.", True, WARN)
        surface.blit(hint, hint.get_rect(center=(width // 2, height - 94)))
