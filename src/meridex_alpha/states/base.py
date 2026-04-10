from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class StateResult:
    next_state: str | None = None


class BaseState(ABC):
    name: str

    @abstractmethod
    def enter(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def handle_event(self, event: Any) -> StateResult | None:
        raise NotImplementedError

    @abstractmethod
    def update(self, dt: float) -> StateResult | None:
        raise NotImplementedError

    @abstractmethod
    def render(self, surface: Any) -> None:
        raise NotImplementedError
