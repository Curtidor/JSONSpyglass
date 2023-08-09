from dataclasses import dataclass
from typing import List


@dataclass
class ConfigElement:
    """Base class for holding element data in from the configuration file"""
    name: str
    element_id: int
    target_pages: List[str]