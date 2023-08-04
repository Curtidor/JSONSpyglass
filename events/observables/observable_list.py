from typing import Any, Iterable

from events.observables.observable_collection import ObservableCollection
from events.event import Event
from events.event_type import CollectionEventType


class ObservableList(list, ObservableCollection):
    def __init__(self, collection_name: str = None):
        """
        Initialize the ObservableList.

        Args:
            collection_name (str, optional): An optional identifier for the collection. Defaults to None.
        """
        # Call __init__ from the first parent class, 'list'
        super().__init__()
        # Call __init__ from the second parent class, 'ObservableCollection'
        ObservableCollection.__init__(self, collection_name=collection_name)

    def append(self, item: Any) -> None:
        """
        Append an item to the list and notify all registered observers.

        Args:
            item (Any): The item to be appended to the list.
        """
        super().append(item)
        self.trigger(Event(self.collection_name, CollectionEventType.APPEND, data=item))

    def extend(self, iterable: Iterable):
        """
        Extend the list by appending elements from the iterable and notify all registered observers.

        Args:
            iterable (Iterable): An iterable of items to be appended to the list.
        """
        super().extend(iterable)
        self.trigger(Event(self.collection_name, CollectionEventType.EXTEND, data=iterable))


