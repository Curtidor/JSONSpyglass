import weakref
from typing import Any, Callable, List, Dict

from utils.logger import Logger, LoggerLevel


class ObservableCollection(list):
    """
    A subclass of list that allows registering observers to watch for changes in the list.

    This class provides a basic implementation of an observable list, allowing observers (callable functions)
    to register interest in changes to the list. Whenever an item is appended to the list, all registered
    observers will be notified with the new item.

    Note: This class is designed to just include the necessary logic for this project's needs. It does not include all
    list methods or support more complex operations that a full-featured observable collection might require.

    Usage:
        collection = ObservableCollection()
        collection.add_observer(my_callback)

        # Appending an item will notify the registered observer.
        collection.append(item)

    Attributes:
        _observers (List[Callable]): A list of callable functions (observers) registered to be notified
            when items are appended to the list.
        name (str): An optional identifier for the collection.
    """

    _observable_collections: Dict[str, weakref.ref] = {}

    def __init__(self, name: str = None):
        """
        Initialize the ObservableCollection.

        Args:
            name (str, optional): An optional identifier for the collection. Defaults to None.
        """
        super(ObservableCollection, self).__init__()

        self._observers: List[Callable] = []
        self.name = name if name is not None else id(self)

        self._register_collection_name()

    def append(self, item: Any) -> None:
        """
        Append an item to the list and notify all registered observers.

        Args:
            item (Any): The item to be appended to the list.
        """
        super().append(item)
        self._notify_observers(item)

    def add_observer(self, call_back: Callable) -> None:
        """
        Register an observer to be notified when items are appended to the list.

        Args:
            call_back (Callable): A callable function to be notified on list updates.
        """
        if call_back not in self._observers:
            self._observers.append(call_back)

    def remove_observer(self, call_back: Callable) -> None:
        """
        Remove an observer from the list of registered observers.

        Args:
            call_back (Callable): The callable function to be removed from the list of observers.
        """
        self._observers.remove(call_back)

    @staticmethod
    def add_observer_to_target(collection_name: str, callback: Callable) -> bool:
        """
        Add an observer to a specific ObservableCollection instance based on its name.

        Args:
            collection_name (str): The name of the ObservableCollection to observe.
            callback (Callable): The callback function to be notified on list updates.

        Returns:
            bool: True if the observer was successfully added to the specified collection, False otherwise.
        """
        for collection_ref in ObservableCollection._observable_collections.values():
            collection = collection_ref()
            if collection_name == collection.name:
                collection.add_observer(callback)
                return True
        Logger.console_log(f"No observable collection was found by the name: [{collection_name}] "
                           f"Call back: [{callback.__name__}]", LoggerLevel.WARNING)
        return False

    def _notify_observers(self, item: Any) -> None:
        """
        Notify all registered observers with the new item that was appended to the list.

        Args:
            item (Any): The new item that was appended to the list.
        """
        ObservableCollection._remove_dead_refs()

        for observer in self._observers:
            observer(item)

    def _register_collection_name(self):
        """
        A method to register the collection name and its weak reference in the dictionary.

        This method is called during the initialization of the ObservableCollection.
        If the collection name is already registered in the dictionary, it logs an error message.
        """
        if self.name in ObservableCollection._observable_collections:
            Logger.console_log(f"Observable collection name already registered: {self.name}", LoggerLevel.ERROR)
        else:
            ObservableCollection._observable_collections[self.name] = weakref.ref(self)

    @staticmethod
    def _remove_dead_refs():
        dead_ref_keys = [key for key, ref in ObservableCollection._observable_collections.items() if ref() is None]

        for dead_ref_key in dead_ref_keys:
            ObservableCollection._observable_collections.pop(dead_ref_key)

