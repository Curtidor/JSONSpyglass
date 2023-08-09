from dataclasses import dataclass

from .config_element import ConfigElement


@dataclass
class SelectorElement(ConfigElement):
    """Class for holding selector element data from the configuration file"""
    css_selector: str
