from dataclasses import dataclass, field
from typing import Dict, Any, Literal, Set, Tuple

VALID_STATES = {"domcontentloaded", "load", "networkidle"}
ACCEPTED_ELEMENT_TYPES = {'search_hierarchy', 'css_selector'}


VALID_EVENTS = {
    "close",
    "console",
    "crash",
    "dialog",
    "domcontentloaded",
    "download",
    "filechooser",
    "frameattached",
    "framedetached",
    "framenavigated",
    "load",
    "pageerror",
    "popup",
    "request",
    "requestfailed",
    "requestfinished",
    "response",
    "websocket",
    "worker"
}


@dataclass
class Requires:
    loaded_elements: Set[Tuple[str, str]] = field(default_factory=set)
    events: Set[str] = field(default_factory=set)
    states: Set[Literal["domcontentloaded", "load", "networkidle"]] = field(default_factory=set)

    def build_requires(self, requires_data: Dict[Any, Any]) -> 'Requires':
        """
        Populates the Requires instance with data from a given dictionary.

        Args:
            requires_data (Dict[Any, Any]): A dictionary containing the 'requires' data.

        Returns:
            Requires: The updated instance with loaded elements, events, and valid states.
        """
        if not requires_data:
            return self

        for element_load in requires_data.get('loaded', [{}]):
            if any(element_type in ACCEPTED_ELEMENT_TYPES for element_type in element_load):
                self.loaded_elements.update(element_load.items())

        self.events.update({event for event in requires_data.get('event', []) if event in VALID_EVENTS})

        self.states.update({state for state in requires_data.get('state', []) if state in VALID_STATES})

        return self

    def merge_requires(self, *requires_list: 'Requires') -> 'Requires':
        """
        Merges multiple Requires instances into the current instance, ensuring no repeating values.

        Args:
            requires_list (Requires): The Requires instances to merge.

        Returns:
            Requires: The merged Requires instance.
        """
        for req in requires_list:
            self.loaded_elements.update(req.loaded_elements)
            self.events.update(req.events)
            self.states.update(req.states)

        return self
