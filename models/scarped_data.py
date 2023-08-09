from typing import Generator
from dataclasses import dataclass

from bs4 import ResultSet, PageElement


@dataclass
class ScrapedData:
    """Class for holding scraped data"""
    url: str
    elements: ResultSet
    target_element_id: int

    def get_elements(self) -> Generator[PageElement, None, None]:
        for element in self.elements:
            yield element

    def __repr__(self):
        return f"URL: {self.url}, ELEMENTS: {self.elements}"
