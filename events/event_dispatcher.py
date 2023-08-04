import asyncio

from typing import Callable, Any, Set, List, Dict

from .event_listener import EventListener, Priority
from .event import Event


class EventDispatcher:
    _busy_listeners: Set['Callable'] = set()

    def __init__(self):
        self._listeners: Dict[str, List['EventListener']] = {}

    def add_listener(self, event_name: str, listener: Callable, priority: Priority = Priority.NORMAL) -> None:
        """
        Add a listener to the event.
        """
        if callable(listener):
            self._register_event(event_name, listener, priority)
            self._sort_listeners(event_name)
        else:
            raise ValueError("Listener must be callable (a function or method).")

    def remove_listener(self, event_name: str, listener: Callable) -> None:
        """
        Remove a listener from the event.
        """
        for event_listener in self._listeners.get(event_name):
            if event_listener.callback == listener:
                self._listeners.get(event_name).remove(event_listener)
                return  # To ensure only one instance is removed

    def trigger(self, event: Event, *args, **kwargs) -> None:
        """
        Trigger the event and notify all registered listeners.
        """
        if event.event_name not in self._listeners:
            return

        responses = 0
        for listener in self._listeners[event.event_name]:
            if event.max_responders == -1 or responses < event.max_responders:
                listener.callback(event, *args, **kwargs)
                responses += 1
            # max responses reached exit the function
            else:
                return

    async def async_trigger(self, event: Event, *args: Any, **kwargs: Any) -> None:
        """
        Async trigger the event and notify all registered listeners.
        """
        listeners = self._listeners.get(event.event_name, [])
        max_responders = event.max_responders if event.max_responders != -1 else len(listeners)

        async def run_listener(listener: EventListener):
            if listener.callback not in self._busy_listeners:
                self._busy_listeners.add(listener.callback)
                await listener.callback(*args, **kwargs)
                self._busy_listeners.remove(listener.callback)

        await asyncio.gather(*[run_listener(listener) for listener in listeners[:max_responders]])

    def _register_event(self, event_name: str, callback: Callable, priority: Priority) -> None:
        # event has already been registered
        listener = EventListener(callback=callback, priority=priority)
        if event_name in self._listeners:
            self._listeners[event_name].append(listener)
        else:
            self._listeners.update({event_name: [listener]})

    def _sort_listeners(self, event_name: str) -> None:
        if event_name not in self._listeners:
            return
        self._listeners[event_name] = sorted(self._listeners[event_name], key=lambda event_listener: event_listener.priority.value)


