import functools
import time
import threading
import weakref

from typing import Dict, Type, Callable

from utils.logger import Logger, LoggerLevel
from events.event_dispatcher import EventDispatcher


class ObservableCollection(EventDispatcher):
    """
    A base class for observable collections.

    This class provides functionality to register observers that are interested in changes to the collection.
    Observers can register callbacks to be notified when new items are appended to the collection.

    Attributes:
        collection_name (str): An optional identifier for the collection.
    """
    _memory_cleaner_started = False
    _observable_collections: Dict[
        Type['ObservableCollection'], Dict[str, weakref.ref[Type['ObservableCollection']]]] = {}

    def __init__(self, collection_name: str = None):
        """
        Initialize the ObservableCollection.

        Args:
            collection_name (str, optional): An optional identifier for the collection. Defaults to objects id.
        """
        super(ObservableCollection, self).__init__()
        self.collection_name = collection_name if collection_name is not None else id(self)
        self._register_collection_name()

    @staticmethod
    def add_listener_to_target(collection_name: str, callback: Callable,
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
                collection.add_listener(collection_name, callback)
                return True

        for c_type in ObservableCollection._observable_collections:
            collection = ObservableCollection._try_get_collection(
                ObservableCollection._observable_collections[c_type],
                collection_name
            )
            if collection is None:
                continue

            collection.add_listener(collection_name, callback)
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

    @staticmethod
    def _memory_cleanup_decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if not ObservableCollection._memory_cleaner_started:
                ObservableCollection._start_memory_cleanup_thread()
            return func(*args, **kwargs)

        return wrapper

    @_memory_cleanup_decorator
    def _register_collection_name(self):
        """
        Register the collection name and its weak reference in the dictionary.

        This method is called during the initialization of the ObservableCollection.
        If the collection name is already registered in the dictionary, it logs an error message.
        """
        # if the collection was not given a name don't register it for look up
        if self.collection_name == id(self):
            return

        collection_type = type(self)
        collection_data = ObservableCollection._observable_collections.get(collection_type)
        # if the name is already registered, log an error
        if collection_data and self.collection_name in collection_data:
            raise Exception(f"Observable collection name already registered: [{self.collection_name}] "
                               f"Type: [{collection_type.__name__}]")
        # if the collection_type key is already in the dict, add a new mapping of the collection's name (key)
        # and its weak_ref (value)
        elif collection_type in ObservableCollection._observable_collections:
            ObservableCollection._observable_collections[collection_type].update({self.collection_name: weakref.ref(self)})
        # if the collection type is not already in the dict, add it
        else:
            ObservableCollection._observable_collections[collection_type] = {self.collection_name: weakref.ref(self)}

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
            time.sleep(60)  # Sleep  for 1 minute before the next cleanup

    @staticmethod
    def _start_memory_cleanup_thread() -> None:
        """
        Start the memory cleanup thread as a daemon thread.
        """
        if ObservableCollection._memory_cleaner_started:
            return
        cleanup_thread = threading.Thread(target=ObservableCollection._memory_cleanup)
        cleanup_thread.daemon = True
        cleanup_thread.start()

        ObservableCollection._memory_cleaner_started = True
