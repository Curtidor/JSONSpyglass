import asyncio

from asyncio import Queue, QueueEmpty
from typing import Callable, Any, Set, List, Dict

from utils.logger import Logger, LoggerLevel
from .event_listener import EventListener, Priority
from .event import Event


class EventDispatcher:
    _busy_listeners: Set['Callable'] = set()

    def __init__(self, debug_mode: bool = False):
        self._event_loop_running = False
        self._listeners: Dict[str, List['EventListener']] = {}
        self.debug_mode = debug_mode
        self._cancel_events = False

        self._event_queue = Queue()

    def add_listener(self, event_name: str, listener: Callable, priority: Priority = Priority.NORMAL) -> None:
        """
        Add a listener to the event.
        """
        if callable(listener):
            self._register_event_listener(event_name, listener, priority)
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
        self._event_queue.put_nowait((self._trigger, event, args, kwargs))

    def _trigger(self, event: Event, *args, **kwargs) -> None:
        """
        Trigger the event and notify all registered listeners.
        """

        if event.event_name not in self._listeners or self._cancel_events:
            return

        responses = 0
        for listener in self._listeners[event.event_name]:
            if self.debug_mode:
                Logger.console_log(f"calling: [{listener.callback.__name__}] from event: [{event.event_name}]",
                                   LoggerLevel.INFO, include_time=True)

            if event.max_responders == -1 or responses < event.max_responders:
                listener.callback(event, *args, **kwargs)
                responses += 1
            # max responses reached exit the function
            else:
                return

    async def async_trigger(self, event: Event, *args: Any, **kwargs: Any) -> None:
        self._event_queue.put_nowait((self._async_trigger, event, args, kwargs))

    async def _async_trigger(self, event: Event, *args: Any, **kwargs: Any) -> None:
        """
        Async trigger the event and notify all registered listeners.
        """

        if self._cancel_events:
            return

        listeners = self._listeners.get(event.event_name, [])
        max_responders = event.max_responders if event.max_responders != -1 else len(listeners)

        async def run_listener(listener: EventListener):
            if self.debug_mode:
                Logger.console_log(
                    f"async calling: [{listener.callback.__name__}] from event: [{event.event_name}]",
                    LoggerLevel.INFO, include_time=True)

                if listener.callback in self._busy_listeners:
                    Logger.console_log(
                        f"skipping call to: [{listener.callback.__name__}] as its busy",
                        LoggerLevel.INFO, include_time=True)

            if listener.callback not in self._busy_listeners or event.allow_busy_trigger:
                self._busy_listeners.add(listener.callback)
                await listener.callback(event, *args, **kwargs)
                self._remove_busy_listener(listener.callback)

        await asyncio.gather(*[run_listener(listener) for listener in listeners[:max_responders]])

    def disable_all_events(self) -> None:
        self._cancel_events = True

    def enable_all_events(self) -> None:
        self._cancel_events = False

    def start_event_loop(self):
        if not self._event_loop_running:
            asyncio.create_task(self._event_loop())
            self._event_loop_running = True

    def close_event_loop(self):
        if self._event_loop_running:
            self._event_queue.put_nowait(None)

    def is_queue_empty(self) -> bool:
        return self._event_queue.empty()

    def queue_size(self) -> int:
        return self._event_queue.qsize()

    def _register_event_listener(self, event_name: str, callback: Callable, priority: Priority) -> None:
        listener = EventListener(callback=callback, priority=priority)

        # callback already register for the given event
        if listener.callback in [lstener for lstener in self._listeners.get(event_name, [])]:
            return

        if event_name in self._listeners:
            self._listeners[event_name].append(listener)
        else:
            self._listeners.update({event_name: [listener]})

    def _sort_listeners(self, event_name: str) -> None:
        if event_name not in self._listeners:
            return
        self._listeners[event_name] = sorted(self._listeners[event_name], key=lambda event_listener: event_listener.priority.value)

    def _remove_busy_listener(self, callback: Callable) -> None:
        if callback in self._busy_listeners:
            self._busy_listeners.remove(callback)

    async def _event_loop(self):
        while True:
            task = await self._event_queue.get()
            if task is None:  # sentinel value to stop the event loop
                self._event_loop_running = False
                break
            func, event, args, kwargs = task
            if asyncio.iscoroutinefunction(func):
                await func(event, *args, **kwargs)
            else:
                func(event, *args, **kwargs)
            self._event_queue.task_done()


