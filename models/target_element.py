from typing import Any


class TargetElement:
    def __init__(self, name, tag: str, target_pages: list[str], element_id: int, attributes: dict = None):
        self.name = name
        self.tag = tag
        self.attributes = attributes if attributes is not None else {}
        self.target_pages = target_pages
        self.element_id = element_id

    def add_attribute(self, attribute_name: str, attribute_value: Any) -> None:
        self.attributes[attribute_name] = attribute_value

    @staticmethod
    def create_target_elements(raw_element_data: list) -> list["TargetElement"]:
        new_elements = []

        if raw_element_data is None:
            print("Invalid configuration data!")
            return []

        for element in raw_element_data:
            tag = element.get('tag', "")
            target_pages = element.get('target_pages', 'any')
            element_id = element.get('id', 'invalid_id')

            if element_id == 'invalid_id':
                raise Exception(f"Invalid element, no id found: {element}")

            attributes = TargetElement.collect_attributes(element.get('attributes', []))
            element_name = element.get('name', 'no_ref_element')
            new_elements.append(TargetElement(element_name, tag, target_pages, element_id, attributes))

        return new_elements

    @staticmethod
    def collect_attributes(attributes: list) -> dict:
        attr = {}
        for attribute in attributes:
            name = attribute.get("name", "")
            value = attribute.get("value", "NONE")

            if name:
                if name in attr:
                    attr[name].append(value)
                else:
                    attr[name] = [value]

        return attr

    def __repr__(self):
        return f"TAG: {self.tag}, ATTRIBUTES: {self.attributes}, ID: {self.element_id}"
