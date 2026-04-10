from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from math import hypot
import random

import pygame


ROAD_Y = 286.0
PATH_HALF_HEIGHT = 92.0


@dataclass(frozen=True, slots=True)
class HubNpc:
    key: str
    label: str
    role: str
    position: tuple[float, float]


NPC_ARCHETYPES = (
    ("agri_lead", "Агроном", "Агромониторинг"),
    ("warehouse_chief", "Логист", "Склад"),
)

HUB_NPCS = (
    HubNpc("agri_lead", "Агроном", "Агромониторинг", (360.0, ROAD_Y - 34.0)),
    HubNpc("warehouse_chief", "Логист", "Склад", (620.0, ROAD_Y + 38.0)),
)


@dataclass(slots=True)
class HubRuntime:
    player_position: tuple[float, float] = (140.0, ROAD_Y)
    interaction_radius: float = 72.0
    movement_speed: float = 220.0
    world_size: tuple[float, float] = (1000000.0, 360.0)
    active_keys: set[int] = field(default_factory=set)
    npc_stream: list[HubNpc] = field(default_factory=list)
    road_y: float = ROAD_Y
    path_half_height: float = PATH_HALF_HEIGHT
    spawn_spacing: float = 260.0
    spawn_variance: float = 42.0
    camera_margin: float = 180.0
    next_spawn_x: float = 360.0
    camera_x: float = 0.0
    rng_seed: int = 7
    _rng: random.Random = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._rng = random.Random(self.rng_seed)
        if not self.npc_stream:
            self.npc_stream = list(HUB_NPCS)
            if self.npc_stream:
                self.next_spawn_x = self.npc_stream[-1].position[0] + self.spawn_spacing
        self._refresh_camera()
        self.ensure_npcs_ahead()

    def nearest_npc(self) -> HubNpc | None:
        closest: HubNpc | None = None
        closest_distance = self.interaction_radius
        for npc in self.npc_stream:
            distance = hypot(
                npc.position[0] - self.player_position[0],
                npc.position[1] - self.player_position[1],
            )
            if distance <= closest_distance:
                closest = npc
                closest_distance = distance
        return closest

    def can_interact(self) -> bool:
        return self.nearest_npc() is not None

    def set_key_state(self, key: int, pressed: bool) -> None:
        movement_keys = {
            pygame.K_LEFT,
            pygame.K_RIGHT,
            pygame.K_UP,
            pygame.K_DOWN,
            pygame.K_a,
            pygame.K_d,
            pygame.K_w,
            pygame.K_s,
        }
        if key not in movement_keys:
            return
        if pressed:
            self.active_keys.add(key)
        else:
            self.active_keys.discard(key)

    def update(self, dt: float) -> None:
        dx = 0.0
        dy = 0.0
        if pygame.K_LEFT in self.active_keys or pygame.K_a in self.active_keys:
            dx -= 1.0
        if pygame.K_RIGHT in self.active_keys or pygame.K_d in self.active_keys:
            dx += 1.0
        if pygame.K_UP in self.active_keys or pygame.K_w in self.active_keys:
            dy -= 1.0
        if pygame.K_DOWN in self.active_keys or pygame.K_s in self.active_keys:
            dy += 1.0
        if dx != 0.0 and dy != 0.0:
            diagonal_scale = 0.70710678118
            dx *= diagonal_scale
            dy *= diagonal_scale

        next_x = self.player_position[0] + dx * self.movement_speed * dt
        next_x = max(0.0, min(self.world_size[0], next_x))
        next_y = self.player_position[1] + dy * self.movement_speed * dt
        next_y = max(self.road_y - self.path_half_height, min(self.road_y + self.path_half_height, next_y))
        self.player_position = (next_x, next_y)
        self._refresh_camera()
        self.ensure_npcs_ahead()
        self._discard_far_behind_npcs()

    def ensure_npcs_ahead(self) -> None:
        target_x = self.player_position[0] + 1400.0
        while self.next_spawn_x < target_x:
            self.npc_stream.append(self._spawn_npc(self.next_spawn_x))
            step = self.spawn_spacing + self._rng.uniform(-self.spawn_variance, self.spawn_variance)
            self.next_spawn_x += max(180.0, step)

    def _spawn_npc(self, spawn_x: float) -> HubNpc:
        index = len(self.npc_stream) % len(NPC_ARCHETYPES)
        key, label, role = NPC_ARCHETYPES[index]
        lane_offset = self._rng.choice((-72.0, -46.0, -18.0, 18.0, 46.0, 72.0))
        return HubNpc(key, label, role, (spawn_x, self.road_y + lane_offset))

    def _refresh_camera(self) -> None:
        self.camera_x = max(0.0, self.player_position[0] - self.camera_margin)

    def _discard_far_behind_npcs(self) -> None:
        cutoff = self.camera_x - 300.0
        self.npc_stream = [npc for npc in self.npc_stream if npc.position[0] >= cutoff]
