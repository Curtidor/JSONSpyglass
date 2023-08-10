from typing import Any, List, Dict
from dataclasses import dataclass

from .config_element import ConfigElement


@dataclass
class TargetElement(ConfigElement):
    """
    Class for holding target element data from the configuration file.

    Attributes:
        tag (str): The HTML tag of the target element.
        attributes (Dict[str, List[Any]]): Dictionary containing attribute names and values.
            Each attribute name maps to a list of values.
        element_search_hierarchy (List[Dict[Any, Any]]): List of dictionaries representing the search hierarchy.
            Each dictionary holds attribute criteria to locate the element within a hierarchy.
    """

    tag: str
    attributes: Dict[str, List[Any]] = None
    element_search_hierarchy: List[Dict[Any, Any]] = None

    @staticmethod
    def collect_attributes(attributes: List[Dict[str, Any]]) -> Dict[str, List[Any]]:
        """
        Collects attributes from a list of dictionaries and organizes them into a dictionary format.

        Args:
            attributes (List[Dict[str, Any]]): List of dictionaries containing attribute names and values.

        Returns:
            Dict[str, List[Any]]: Dictionary mapping attribute names to lists of values.
        """
        attr = {}
        for attribute in attributes:
            name = attribute.get("name", "")
            value = attribute.get("value", "None")

            if name:
                if name in attr:
                    attr[name].append(value)
                else:
                    if isinstance(value, list):
                        attr[name] = value
                    else:
                        attr[name] = [value]

        return attr

    def create_search_hierarchy_from_attributes(self):
        """
        Creates a search hierarchy based on the current attributes.
        The hierarchy consists of a list containing the current attributes' dictionary.
        """
        self.element_search_hierarchy = [self.attributes]

    def create_attributes_from_search_hierarchy(self):
        """
        Populates the attributes based on the search hierarchy.

        Note:
            The target's attributes will reflect the top-most parent attributes.
        """
        self.attributes = self.element_search_hierarchy[0] if self.element_search_hierarchy else {}
