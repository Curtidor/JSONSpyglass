from enum import Enum


class EventType(Enum):
    """Base class for event types"""
    pass


class CollectionEventType(EventType):
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