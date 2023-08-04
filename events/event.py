from typing import Any, Callable
from dataclasses import dataclass

from .event_type import EventType


@dataclass
class Event:
    event_name: str
    event_type: EventType | str
    data: Any = None
    source: Callable = None
    max_responders: int = -1
    allow_busy_trigger: bool = False
