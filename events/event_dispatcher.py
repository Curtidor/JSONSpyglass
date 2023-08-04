import asyncio

from typing import Callable, Any, Set, List

from .event_listener import EventListener, Priority


class EventDispatcher:
    _busy_listeners: Set['Callable'] = set()

    def __init__(self):
        self._listeners: List['EventListener'] = []

    def add_listener(self, listener: Callable, priority: Priority = Priority.NORMAL) -> None:
        """
        Add a listener to the event.
        """
        if callable(listener):
            self._listeners.append(EventListener(callback=listener, priority=priority))
            self._sort_listeners()

        else:
            raise ValueError("Listener must be callable (a function or method).")

    def remove_listener(self, listener: Callable) -> None:
        """
        Remove a listener from the event.
        """
        for event_listener in self._listeners:
            if event_listener.callback == listener:
                self._listeners.remove(event_listener)
                return  # To ensure only one instance is removed

    def trigger(self, event_response, max_responders: int = - 1, *args, **kwargs) -> None:
        """
        Trigger the event and notify all registered listeners.
        """
        responses = 0
        # Sort the listeners based on their priority using the sorted() function
        # The key=lambda item: item[1].value specifies that we sort based on the Priority enum value
        for listener in self._listeners:
            if max_responders == -1 or responses < max_responders:
                listener.callback(event_response, *args, **kwargs)
                responses += 1
            # max responses reached exit the function
            else:
                return

    async def async_trigger(self, max_responders: int = -1, *args: Any, **kwargs: Any) -> None:
        """
        Async trigger the event and notify all registered listeners.
        """
        responses = 0
        # Sort the listeners based on their priority using the sorted() function
        # The key=lambda item: item[1].value specifies that we sort based on the Priority enum value
        for listener in self._listeners:
            if listener.callback in EventDispatcher._busy_listeners:
                print("BUSY", listener.callback.__name__)
                continue
            elif max_responders == -1 or responses < max_responders:
                EventDispatcher._busy_listeners.add(listener.callback)
                await asyncio.create_task(listener.callback(*args, **kwargs))
                EventDispatcher._busy_listeners.remove(listener.callback)
                responses += 1
            # max responses reached
            else:
                break

    def _sort_listeners(self) -> None:
        self._listeners = sorted(self._listeners, key=lambda event_listener: event_listener.priority.value)


