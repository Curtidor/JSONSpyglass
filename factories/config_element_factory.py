from typing import Generator, List, Dict, Tuple, Any

from models.selector_element import SelectorElement
from models.target_element import TargetElement


class ConfigElementFactory:
    ELEMENT_SELECTOR = 'selector'
    ELEMENT_TARGET = 'target'

    @staticmethod
    def create_elements(generator: Generator[Tuple[str, Dict[Any, Any]], None, None]) -> Dict[str, List[SelectorElement | TargetElement]]:
        """Creates elements based on the provided generator.

        Args:
            generator (Generator[Tuple[str, Dict[Any, Any]]]): A generator yielding element type and data.

        Returns:
            Dict[str, List[SelectorElement | TargetElement]]: Dictionary containing created elements.
        """
        elements: Dict[str, List[Any]] = {
            ConfigElementFactory.ELEMENT_SELECTOR: [],
            ConfigElementFactory.ELEMENT_TARGET: []
        }

        for element_type, element_data in generator:
            target_pages = element_data.get('target_pages', 'any')
            element_id = element_data.get('id', 'invalid_id')
            element_name = element_data.get('name', 'no_ref_element')

            if element_id == 'invalid_id':
                raise ValueError(f"Invalid element id: {element_data}")

            if element_type == ConfigElementFactory.ELEMENT_SELECTOR:
                css_selector = element_data.get('css_selector', '')
                if not css_selector:
                    raise SyntaxError(f'Improperly formatted element, missing css selector: {element_data}')

                elements[element_type].append(SelectorElement(element_name, element_id, target_pages, css_selector))
            elif element_type == ConfigElementFactory.ELEMENT_TARGET:
                tag = element_data.get('tag', "")
                attrs = TargetElement.collect_attributes(element_data.get('attributes', []))

                if not tag or not attrs:
                    raise SyntaxError(f'Improperly formatted element, missing tag or attributes: {element_data}')

                elements[element_type].append(TargetElement(element_name, element_id, target_pages, tag, attrs))

            else:
                raise ValueError(f"Invalid element type {element_type}")

        return elements
