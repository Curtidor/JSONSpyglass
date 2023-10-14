from typing import Any, List, Dict, Generator
from dataclasses import dataclass

from .config_element import ConfigElement


@dataclass
class TargetElement(ConfigElement):
    attributes: Dict[str, Any] = None
    element_search_hierarchy: List[str] = None

    @staticmethod
    def collect_attributes(attributes: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Collect and format a list of attribute dictionaries into a consolidated dictionary.

        Args:
            attributes (List[Dict[str, str]): List of attribute dictionaries, where each dictionary
                contains 'name' and 'value' keys for attribute names and values.

        Returns:
            Dict[str, Any]: A dictionary where attribute names are keys and corresponding values are
                consolidated as space-separated strings.

        This method takes a list of dictionaries where each dictionary contains 'name' and 'value' keys
        representing attribute names and values. It collects these attributes and consolidates values
        for the same attribute name into space-separated strings within the returned dictionary.

        Note:
        The 'attributes' parameter should be a list of dictionaries, where each dictionary contains 'name' and 'value' keys.

        Example:
        attributes = [
            {'name': 'class', 'value': 'btn'},
            {'name': 'id', 'value': 'submit-button'},
            {'name': 'class', 'value': 'active'}
        ]
        collect_attributes(attributes)
        # Output: {'class': 'btn active', 'id': 'submit-button'}
        """
        attr = {}
        for attribute in attributes:
            name = attribute.get("name", "")
            value = attribute.get("value", "None")

            if not value or not name:
                raise ValueError(f"Improperly formatted attributes, missing value or name: {attribute}")

            if name in attr:
                attr[name].append(value)
            else:
                attr[name] = [value]

        return {k: ' '.join(v) for k, v in attr.items()}

    @classmethod
    def format_search_hierarchy_from_attributes(cls, attr_collection: List[Dict[str, str]]) -> List[str]:
        """
        Format a list of attribute dictionaries into a list of CSS selectors.

        Args:
            attr_collection (List[Dict[str, str]): List of attribute dictionaries, where each dictionary
                contains 'name' and 'value' keys for attribute names and values.

        Returns:
            List[str]: A list of CSS selectors generated based on the provided attributes.

        This method takes a list of dictionaries where each dictionary contains 'name' and 'value' keys
        representing attribute names and values. It then generates CSS selectors based on these attributes
        and returns a list of these CSS selectors.

        Note:

        attr_collection = [
            {'name': 'class', 'value': 'btn active']},
            {'name': 'id', 'value': 'submit-button'}
         ]

        format_search_hierarchy(attr_collection)
        # Output: ['.btn.active', '[id=submit-button]']
        """

        search_hierarchy = []
        for attributes in attr_collection:
            search_hierarchy.extend(cls.format_css_selectors(attributes))

        return search_hierarchy

    @classmethod
    def format_search_hierarchy_from(cls, raw_hierarchy_data: List[Dict[str, str]]) -> List[str]:
        pass

    @classmethod
    def format_css_selectors(cls, formatted_attributes: Dict[str, str]) -> Generator[str, None, None]:
        """
        Generate CSS selectors from formatted attribute data.

        Args:
            formatted_attributes (Dict[str, str]): A dictionary with attribute names as keys and corresponding
                values as strings.

        Yields:
            Generator[str]: A generator that yields formatted CSS selectors based on the provided attributes.

        This method takes a dictionary of attribute names and corresponding values as strings and generates
        CSS selectors for these attributes. It yields the generated CSS selectors one by one.

        Note:
        The 'formatted_attributes' parameter should be a dictionary where the keys represent attribute names
        and the values represent attribute values as strings.

        Example:
        formatted_attributes = {'class': 'btn active', 'id': 'submit-button'}
        for selector in formate_css_selectors(formatted_attributes):
            print(selector)
        # Output:
        # .btn.active
        # [id=submit-button]
        """
        CLASS_ATTR = 'class'

        for attr_name, values in formatted_attributes.items():
            if not values:
                raise ValueError(f"improperly formatted attribute, missing name or value: {formatted_attributes}")

            css_selector = f".{'.'.join(values.split())}" if attr_name == CLASS_ATTR \
                else f"[{attr_name}={values}]"

            yield css_selector

    def create_search_hierarchy_from_attributes(self):
        """
        Creates a search hierarchy based on the current attributes.

        Note:
            Make sure the attributes have been formatted before using this method
        """

        self.element_search_hierarchy = self.format_search_hierarchy_from_attributes([self.attributes])

    def create_attributes_from_search_hierarchy(self):
        """
        Populates the attributes based on the search hierarchy.
        """
        raise NotImplementedError
