from observables.collection_event import CollectionEvent, CollectionEventType
from observables.observable_collection import ObservableCollection


class ObservableDict(dict, ObservableCollection):
    def __init__(self, name: str = None):
        # Call __init__ from the first parent class, 'dict'
        super().__init__()
        # Call __init__ from the second parent class, 'ObservableCollection'
        ObservableCollection.__init__(self, name=name)

    def __setitem__(self, key, value):
        """
        Set the value for the given key and notify all registered observers.

        Args:
            key: The key for which to set the value.
            value: The value to be set.
        """
        super().__setitem__(key, value)
        self._notify_observers(CollectionEvent(CollectionEventType.UPDATE, item=(key, value)))

    def __delitem__(self, key):
        """
        Delete the item with the given key and notify all registered observers.

        Args:
            key: The key of the item to be deleted.
        """
        super().__delitem__(key)
        self._notify_observers(CollectionEvent(CollectionEventType.DELETE, item=key))

    def clear(self):
        """
        Clear all items from the dictionary and notify all registered observers.
        """
        super().clear()
        self._notify_observers(CollectionEvent(CollectionEventType.CLEAR))

    def pop(self, key, default=None):
        """
        Remove and return the value for the given key and notify all registered observers.

        Args:
            key: The key of the item to be removed.
            default: The value to be returned if the key is not found.

        Returns:
            The value for the given key if found, otherwise the default value.
        """
        value = super().pop(key, default)
        self._notify_observers(CollectionEvent(CollectionEventType.POP, item=value))
        return value

    def popitem(self):
        """
        Remove and return an arbitrary (key, value) pair from the dictionary and notify all registered observers.

        Returns:
            An arbitrary (key, value) pair from the dictionary.
        """
        key, value = super().popitem()
        self._notify_observers(CollectionEvent(CollectionEventType.POPITEM, item=(key, value)))
        return key, value

    def setdefault(self, key, default=None):
        """
        Set the value for the given key if it doesn't exist and return the value.
        If the key already exists, return its value and do not modify the dictionary.

        Args:
            key: The key for which to set the value.
            default: The value to be set if the key doesn't exist.

        Returns:
            The value for the given key if found, otherwise the default value.
        """
        value = super().setdefault(key, default)
        self._notify_observers(CollectionEvent(CollectionEventType.UPDATE, item=(key, value)))
        return value

    def update(self, *args, **kwargs):
        """
        Update the dictionary with the items from an iterable and/or keyword arguments.
        If a key from the iterable/kwargs already exists, its value will be updated.

        After updating the dictionary, notify all registered observers.

        Args:
            *args: An iterable of items to update the dictionary.
            **kwargs: Keyword arguments to update the dictionary.
        """
        super().update(*args, **kwargs)
        self._notify_observers(CollectionEvent(CollectionEventType.UPDATE, item=dict(*args, **kwargs)))

