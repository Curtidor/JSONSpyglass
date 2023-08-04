from typing import Any, Callable
from dataclasses import dataclass

from .event_type import EventType


@dataclass
class Event:
    event_name: str
    event_type: EventType
    data: Any = None
    source: Callable = None
    max_responders: int = -1
