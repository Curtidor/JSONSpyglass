from typing import Generator, List
from dataclasses import dataclass

from selectolax.parser import Node


@dataclass
class ScrapedData:
    """Class for holding scraped data"""
    url: str
    nodes: List[Node]
    target_element_id: int

    def get_nodes(self) -> Generator[Node, None, None]:
        for node in self.nodes:
            yield node

    def __repr__(self):
        return f"URL: {self.url}, ELEMENTS: {self.nodes}"
