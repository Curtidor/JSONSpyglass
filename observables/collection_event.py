from typing import Any
from enum import Enum


class CollectionEventType(Enum):
    APPEND = 'append'
    REMOVE = 'remove'
    INSERT = 'insert'
    EXTEND = 'extend'
    SET = 'set'
    DELETE = 'delete'
    CLEAR = 'clear'
    UPDATE = 'update'
    POP = 'pop'
    POPITEM = 'pop_item'


class CollectionEvent:
    def __init__(self, event_type: CollectionEventType, item: Any = None, index: int = -1):
        self.event_type = event_type
        self.item = item
        self.index = index
