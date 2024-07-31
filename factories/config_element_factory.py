from typing import List, Dict, Tuple, Any, Iterable

from models.target_element import TargetElement
from models.requires import Requires

ELEMENT_TARGET = 'target'
INVALID_ID = 'invalid_id'
NO_REF_ELEMENT = 'no_ref_element'


class ConfigElementFactory:

    @classmethod
    def create_elements(cls, element_iter: Iterable[Tuple[str, Dict[Any, Any]]], data_order: List[str]) \
            -> tuple[list[TargetElement], Requires]:
        """
        Creates elements based on the provided generator and sorts them according to the data order.

        :param element_iter: An iterable yielding element type and data.
        :param data_order: The order elements should be in.

        :return: Tuple[List[TargetElement], Requires]: List containing created and sorted elements.
        """
        elements, requires = cls._create_elements(element_iter)
        cls._sort_elements(elements, data_order)

        unique_requires = Requires()
        unique_requires.merge_requires(*requires)

        return elements, unique_requires

    @classmethod
    def _create_elements(cls, element_iter: Iterable[Tuple[str, Dict[Any, Any]]]) \
            -> Tuple[List[TargetElement], List[Requires]]:
        """
        Create and return a list of elements based on the provided generator.

        :param element_iter: An iterable yielding element type and data.

        :return: List[TargetElement]: List of created elements.
        """
        elements = []
        requirements = []

        for element_type, element_data in element_iter:
            element_id = element_data.get('id', INVALID_ID)
            element_name = element_data.get('name', NO_REF_ELEMENT)

            if element_id == INVALID_ID:
                raise ValueError(f"Invalid element id: {element_data}")

            if element_type == ELEMENT_TARGET:
                elements.append(cls._create_target(element_name, int(element_id), element_data))
            else:
                raise ValueError(
                    f"Invalid element type: {element_type}, possibly missing either a css selector, "
                    f"a search hierarchy, or tags and attributes"
                )

            element_requirements = element_data.get('requires', {})

            requirements.append(Requires().build_requires(element_requirements))

        return elements, requirements

    @staticmethod
    def _create_target(element_name: str, element_id: int, element_data: Dict[Any, Any]) -> TargetElement:
        """
        Create a TargetElement.

        :param element_name: The name of the element.
        :param element_id: The element's ID.
        :param element_data: Data related to the element.

        :return: TargetElement: The created TargetElement.
        """
        formatted_attrs = TargetElement.collect_attributes(element_data.get('attributes', []))
        search_hierarchy = element_data.get('search_hierarchy', [])

        if search_hierarchy and formatted_attrs:
            raise ValueError(
                f'Improperly formatted element, you cannot specify a search hierarchy and, '
                f'attributes on the same element: {element_data}'
            )

        target_element = TargetElement(element_name, element_id)

        if not formatted_attrs:
            css_selector = element_data.get('css_selector', '')

            if css_selector:
                formatted_attrs = TargetElement.collect_attributes([{'css_selector': css_selector}])

        # Convert attributes into a search hierarchy to simplify the scraping process.
        if search_hierarchy:
            target_element.search_hierarchy = TargetElement.create_search_hierarchy_from_raw_hierarchy(search_hierarchy)
        elif formatted_attrs:
            target_element.create_search_hierarchy_from_attributes(formatted_attrs)
        else:
            raise ValueError(f'Missing either a search hierarchy or a attribute selector {formatted_attrs}')

        return target_element

    @staticmethod
    def _sort_elements(element_selectors: List[TargetElement], data_order: List[str]) -> None:
        """
        Sort the element_selectors list based on the order in data_order.

        :param element_selectors: List of SelectorElement or TargetElement.
        :param data_order: The desired order of elements.
        """
        element_selectors.sort(key=lambda x: data_order.index(x.name))
