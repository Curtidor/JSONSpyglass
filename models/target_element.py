from typing import List, Dict, Generator
from dataclasses import dataclass


@dataclass
class TargetElement:
    name: str
    element_id: int
    search_hierarchy: List[str] = None

    @staticmethod
    def collect_attributes(attributes: List[Dict[str, str]]) -> Dict[str, str]:
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
                css_selector = attribute.get('css_selector', '')
                if css_selector:
                    name = "css_selector"
                    value = css_selector
                else:
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
    def create_search_hierarchy_from_raw_hierarchy(cls, raw_hierarchy: List[Dict[str, str]]) -> List[str]:
        """
            Create a search hierarchy by processing a raw hierarchy of HTML attributes.

            Args:
                raw_hierarchy (List[Dict[str, str]): A list of dictionaries representing raw HTML attributes.

            Returns:
                List[str]: A list of CSS selectors generated from the processed raw HTML attributes.

            This method takes a list of dictionaries, where each dictionary represents raw HTML attributes, and
            processes them to create a search hierarchy. The raw HTML attributes are formatted and transformed into
            CSS selectors, which are then returned as a list.

            Example:
            raw_hierarchy = [
                {'name': 'class', 'value': 'btn active'},
                {'name': 'id', 'value': 'submit-button'},
                {'name': 'data-role', 'value': 'button'}
            ]
            create_search_hierarchy_from_raw_hierarchy(raw_hierarchy)
            # Output: ['.btn.active', '[id=submit-button]', '[data-role=button]']
            """
        raw_formatted_hierarchy = [cls.collect_attributes([h_element]) for h_element in raw_hierarchy]

        search_hierarchy = []
        for formatted_attr in raw_formatted_hierarchy:
            # check if it's already a css selector
            p_css_selector = formatted_attr.get('css_selector', '')
            if p_css_selector:
                search_hierarchy.append(p_css_selector)
                continue
            # else format the attributes into a css and append them
            for css_selector in cls.format_css_selectors(formatted_attr):
                search_hierarchy.append(css_selector)

        return search_hierarchy

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
                raise ValueError(f"improperly formatted attribute, value: {formatted_attributes} {attr_name}")

            if attr_name == 'css_selector':
                css_selector = values
            else:
                css_selector = f".{'.'.join(values.split())}" if attr_name == CLASS_ATTR \
                    else f"[{attr_name}={values}]"

            yield css_selector

    def create_search_hierarchy_from_attributes(self, formatted_attrs: Dict[str, str]) -> None:
        """
        Creates a search hierarchy based on the current attributes.

        Note:
            Make sure the attributes have been formatted before using this method
        """

        self.search_hierarchy = self.format_search_hierarchy_from_attributes([formatted_attrs])
