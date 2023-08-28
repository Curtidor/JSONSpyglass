from dataclasses import dataclass


@dataclass
class ConfigElement:
    """Base class for holding element data in from the configuration file"""
    name: str
    element_type: str
    element_id: int
