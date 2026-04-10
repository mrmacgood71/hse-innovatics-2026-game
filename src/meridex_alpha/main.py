from __future__ import annotations

import pygame

from meridex_alpha.game import Game


def main() -> None:
    pygame.init()
    pygame.display.set_caption("MERIDEX Alpha")
    try:
        Game().run()
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
