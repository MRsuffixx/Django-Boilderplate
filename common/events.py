from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ApplicationEvent:
    name: str
    actor_id: str | None = None
    target_type: str = ""
    target_id: str = ""
    data: dict[str, Any] = field(default_factory=dict)


class EventBus:
    _handlers: dict[str, list[Callable[[ApplicationEvent], None]]] = defaultdict(list)

    @classmethod
    def subscribe(cls, name: str, handler: Callable[[ApplicationEvent], None]) -> None:
        if handler not in cls._handlers[name]:
            cls._handlers[name].append(handler)

    @classmethod
    def publish(cls, event: ApplicationEvent) -> None:
        for handler in cls._handlers.get(event.name, []):
            try:
                handler(event)
            except Exception:
                logger.exception("event.handler_failed", extra={"event_name": event.name})
