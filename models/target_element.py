from typing import Any, List, Dict
from dataclasses import dataclass

from .config_element import ConfigElement


@dataclass
class TargetElement(ConfigElement):
    """Class for holding target element data from the configuration file"""
    tag: str
    attributes: Dict[str, List[Any]] = None

    def add_attribute(self, attribute_name: str, attribute_value: Any) -> None:
        if self.attributes is None:
            self.attributes = {}
        if attribute_name in self.attributes:
            self.attributes[attribute_name].append(attribute_value)
        else:
            self.attributes[attribute_name] = [attribute_value]

    @staticmethod
    def collect_attributes(attributes: List[Dict[str, Any]]) -> Dict[str, List[Any]]:
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
