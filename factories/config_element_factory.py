from typing import Generator, List, Dict, Tuple, Any

from models.target_element import TargetElement


class ConfigElementFactory:
    ELEMENT_TARGET = 'target'
    INVALID_ID = 'invalid_id'
    NO_REF_ELEMENT = 'no_ref_element'

    @staticmethod
    def create_elements(generator: Generator[Tuple[str, Dict[Any, Any]], None, None], data_order: List[str]) \
            -> List[TargetElement]:
        """
        Creates elements based on the provided generator and sorts them according to the data order.

        :param generator: A generator yielding element type and data.
        :param data_order: The order elements should be in.

        :return: List[TargetElement]: List containing created and sorted elements.
        """
        elements = ConfigElementFactory._create_elements(generator)
        ConfigElementFactory._sort_elements(elements, data_order)

        return elements

    @staticmethod
    def _create_elements(generator: Generator[Tuple[str, Dict[str, str]], None, None]) \
            -> List[TargetElement]:
        """
        Create and return a list of elements based on the provided generator.

        :param generator: A generator yielding element type and data.

        :return: List[TargetElement]: List of created elements.
        """
        elements = []

        for element_type, element_data in generator:
            element_id = element_data.get('id', ConfigElementFactory.INVALID_ID)
            element_name = element_data.get('name', ConfigElementFactory.NO_REF_ELEMENT)

            if element_id == ConfigElementFactory.INVALID_ID:
                raise ValueError(f"Invalid element id: {element_data}")

            if element_type == ConfigElementFactory.ELEMENT_TARGET:
                elements.append(ConfigElementFactory._create_target(element_name, element_id, element_data))
            else:
                raise ValueError(
                    f"Invalid element type: {element_type}, possibly missing either a css selector, "
                    f"a search hierarchy, or tags and attributes"
                )

        return elements

    @staticmethod
    def _create_target(element_name: str, element_id: int, element_data: Dict[Any, Any]) -> TargetElement:
        """
        Create a TargetElement.

        :param element_name: The name of the element.
        :param element_id: The element's ID.
        :param element_data: Data related to the element.

        :return: TargetElement: The created TargetElement.
        """
        tag = element_data.get('tag', "")
        attrs = TargetElement.collect_attributes(element_data.get('attributes', []))
        search_hierarchy = element_data.get('search_hierarchy', [])

        if search_hierarchy and (tag or attrs):
            raise ValueError(
                f'Improperly formatted element, you cannot specify a search hierarchy and, '
                f'tags and attributes on the same element: {element_data}'
            )

        new_element = TargetElement(element_name, element_id)

        # Convert attributes into a search hierarchy to simplify the scraping process.
        if search_hierarchy:
            new_element.element_search_hierarchy = TargetElement.create_search_hierarchy_from_raw_hierarchy(search_hierarchy)
        else:
            new_element.create_search_hierarchy_from_attributes(attrs)

        return new_element

    @staticmethod
    def _sort_elements(element_selectors: List[TargetElement], data_order: List[str]) -> None:
        """
        Sort the element_selectors list based on the order in data_order.

        :param element_selectors: List of SelectorElement or TargetElement.
        :param data_order: The desired order of elements.
        """
        element_selectors.sort(key=lambda x: data_order.index(x.name))
