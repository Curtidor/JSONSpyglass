from typing import Generator, List, Dict, Tuple, Any, Union

from models.selector_element import SelectorElement
from models.target_element import TargetElement


class ConfigElementFactory:
    ELEMENT_SELECTOR = 'selector'
    ELEMENT_TARGET = 'target'
    ELEMENT_SEARCH_HIERARCHY = 'hierarchy'

    @staticmethod
    def create_elements(generator: Generator[Tuple[str, Dict[Any, Any]], None, None], data_order: List[str]) \
            -> List[Union[SelectorElement, TargetElement]]:
        """
        Creates elements based on the provided generator.

        :param generator: generator yielding element type and data.
        :param data_order: the order elements should be in

        returns:
            List[Union[SelectorElement, TargetElement]]: List containing created and sorted elements.
        """

        elements = ConfigElementFactory._create_elements(generator)
        ConfigElementFactory._sort_elements(elements, data_order)

        return elements

    @staticmethod
    def _create_elements(generator: Generator[Tuple[str, Dict[Any, Any]], None, None]) \
            -> List[Union[SelectorElement, TargetElement]]:

        elements = []

        for element_type, element_data in generator:
            element_id = element_data.get('id', 'invalid_id')
            element_name = element_data.get('name', 'no_ref_element')

            if element_id == 'invalid_id':
                raise ValueError(f"Invalid element id: {element_data}")

            if element_type == ConfigElementFactory.ELEMENT_SELECTOR:
                css_selector = element_data.get('css_selector', '')
                if not css_selector:
                    raise SyntaxError(f'Improperly formatted element, missing css selector: {element_data}')

                elements.append(SelectorElement(element_name, element_type, element_id, css_selector))

            elif element_type == ConfigElementFactory.ELEMENT_TARGET:
                tag = element_data.get('tag', "")
                attrs = TargetElement.collect_attributes(element_data.get('attributes', []))
                search_hierarchy = element_data.get('search_hierarchy', [])

                if search_hierarchy and (tag or attrs):
                    raise ValueError(
                        f'Improperly formatted element, you cannot specify a search hierarchy and, tags and attributes on the same element: {element_data}')

                new_element = TargetElement(element_name, element_type, element_id, tag, attrs)

                if search_hierarchy:
                    search_hierarchy = TargetElement.format_search_hierarchy(search_hierarchy)

                    new_element.element_search_hierarchy = search_hierarchy
                    new_element.create_attributes_from_search_hierarchy()
                else:
                    new_element.create_search_hierarchy_from_attributes()
                elements.append(new_element)

            else:
                raise ValueError(
                    f"Invalid element type: {element_type}, possibly missing either a css selector, a search hierarchy, or tags and attributes ")

        return elements

    @staticmethod
    def _sort_elements(element_selectors: List[Union[SelectorElement, TargetElement]], data_order: List[str]) -> None:
        # Sort the element_selectors list based on the order in data_order
        element_selectors.sort(key=lambda x: data_order.index(x.name))
