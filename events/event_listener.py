from typing import Callable
from enum import Enum


class Priority(Enum):
    LOW = 3
    NORMAL = 2
    HIGH = 1


class EventListener:
    def __init__(self, callback: Callable, priority: Priority = Priority.NORMAL):
        self.callback = callback
        self.priority = priority

    def __eq__(self, other: 'EventListener') -> bool:
        if not isinstance(other, EventListener):
            return False
        return self.priority == other.priority

    def __lt__(self, other: 'EventListener') -> bool:
        if not isinstance(other, EventListener):
            return False
        return self.priority.value < other.priority.value

    def __hash__(self) -> int:
        # We can use the hash value of the priority enum directly
        return hash(self.priority)
