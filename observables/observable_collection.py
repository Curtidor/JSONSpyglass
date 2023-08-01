import functools
import time
import threading
import weakref
from typing import Dict, Type, List, Callable

from utils.logger import Logger, LoggerLevel
from observables.collection_event import CollectionEvent


class ObservableCollection:
    """
    A base class for observable collections.

    This class provides functionality to register observers that are interested in changes to the collection.
    Observers can register callbacks to be notified when new items are appended to the collection.

    Attributes:
        name (str): An optional identifier for the collection.
    """
    _memory_cleaner_started = False
    _observable_collections: Dict[
        Type['ObservableCollection'], Dict[str, weakref.ref[Type['ObservableCollection']]]] = {}

    def __init__(self, name: str = None):
        """
        Initialize the ObservableCollection.

        Args:
            name (str, optional): An optional identifier for the collection. Defaults to None.
        """
        self.name = name if name is not None else id(self)
        self._observers: List[Callable] = []

        self._register_collection_name()

    def add_observer(self, callback: Callable) -> None:
        """
        Register an observer to be notified when new items are appended to the collection.

        Args:
            callback (Callable): A callable function to be notified on collection updates.
        """

        if callback not in self._observers:
            self._observers.append(callback)

    def remove_observer(self, callback: Callable) -> None:
        """
        Remove an observer from the list of registered observers.

        Args:
            callback (Callable): The callable function to be removed from the list of observers.
        """
        self._observers.remove(callback)

    @staticmethod
    def add_observer_to_target(collection_name: str, callback: Callable,
                               collection_type: Type['ObservableCollection'] = None) -> bool:
        """
        Add an observer to a specific ObservableCollection instance based on its name.

        Args:
            collection_name (str): The name of the ObservableCollection to observe.
            callback (Callable): The callback function to be notified on collection updates.
            collection_type (Type['ObservableCollection'], optional): The type of ObservableCollection to observe.
                If specified, only collections of this type will be considered for observation.
                Defaults to None, meaning all observable collections will be searched and the first found match is used,
                no matter the type of collection.

        Returns:
            bool: True if the observer was successfully added to the specified collection, False otherwise.
        """
        if collection_type is not None:
            collection = ObservableCollection._try_get_collection(
                ObservableCollection._observable_collections.get(collection_type),
                collection_name)
            if collection is not None:
                collection.add_observer(callback)
                return True

        for c_type in ObservableCollection._observable_collections:
            collection = ObservableCollection._try_get_collection(
                ObservableCollection._observable_collections[c_type],
                collection_name
            )
            if collection is None:
                continue

            collection.add_observer(callback)
            return True

        Logger.console_log(f"No observable collection was found by the name: [{collection_name}] "
                           f"Callback: [{callback.__name__}]", LoggerLevel.WARNING)
        return False

    @staticmethod
    def _try_get_collection(collection_data: Dict[str, weakref.ref], name: str) -> 'ObservableCollection':
        """
        Check if a specific collection name exists in the collection data.

        Args:
            collection_data (Dict[str, weakref.ref]): The dictionary containing collection names and weak references.
            name (str): The name of the collection to look for.

        Returns:
            ObservableCollection or None: The observable collection if found, otherwise None.
        """
        for collection_name, collection_ref in collection_data.items():
            if collection_name == name:
                return collection_ref()
        return None

    def _notify_observers(self, event: CollectionEvent, *args, **kwargs) -> None:
        """
        Notify all registered observers with the given event and optional arguments.

        This method iterates over all registered observers and calls their respective callback functions
        with the provided event and any additional arguments passed as *args and **kwargs.

        Args:
            event (CollectionEvent): The event to be sent to all observers.
            *args: Optional positional arguments to be passed to the observers' callback functions.
            **kwargs: Optional keyword arguments to be passed to the observers' callback functions.

        Note:
            The observers' callback functions must be designed to handle the provided event and optional arguments.
        """
        for observer in self._observers:
            observer(event, *args, **kwargs)

    @staticmethod
    def _memory_cleanup_decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if not ObservableCollection._memory_cleaner_started:
                ObservableCollection.start_memory_cleanup_thread()
            return func(*args, **kwargs)

        return wrapper

    @_memory_cleanup_decorator
    def _register_collection_name(self):
        """
        Register the collection name and its weak reference in the dictionary.

        This method is called during the initialization of the ObservableCollection.
        If the collection name is already registered in the dictionary, it logs an error message.
        """
        collection_type = type(self)
        collection_data = ObservableCollection._observable_collections.get(collection_type)
        # if the name is already registered, log an error
        if collection_data and self.name in collection_data:
            Logger.console_log(f"Observable collection name already registered: [{self.name}] "
                               f"Type: [{collection_type.__name__}]", LoggerLevel.ERROR)
        # if the collection_type key is already in the dict, add a new mapping of the collection's name (key)
        # and its weak_ref (value)
        elif collection_type in ObservableCollection._observable_collections:
            ObservableCollection._observable_collections[collection_type].update({self.name: weakref.ref(self)})
        # if the collection type is not already in the dict, add it
        else:
            ObservableCollection._observable_collections[collection_type] = {self.name: weakref.ref(self)}

    @staticmethod
    def _remove_dead_weakrefs(collection_data):
        # Create a list of keys to remove
        keys_to_remove = [collection_name for collection_name, ref in collection_data.items() if ref() is None]

        # Remove the keys from the dictionary
        for key in keys_to_remove:
            Logger.console_log(f"cleaned up dead reference: {key}", LoggerLevel.INFO)
            collection_data.pop(key)

    @staticmethod
    def _memory_cleanup():
        while True:
            for collection_type in ObservableCollection._observable_collections:
                collection_data = ObservableCollection._observable_collections[collection_type]
                ObservableCollection._remove_dead_weakrefs(collection_data)
            time.sleep(60)  # Sleep for 1 minute before the next cleanup

    @staticmethod
    def start_memory_cleanup_thread() -> None:
        """
        Start the memory cleanup thread as a daemon thread.
        """
        if ObservableCollection._memory_cleaner_started:
            return
        cleanup_thread = threading.Thread(target=ObservableCollection._memory_cleanup)
        cleanup_thread.daemon = True
        cleanup_thread.start()

        ObservableCollection._memory_cleaner_started = True
