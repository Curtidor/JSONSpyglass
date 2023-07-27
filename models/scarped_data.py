from typing import Generator

from bs4 import ResultSet, PageElement


class ScrapedData:
    def __init__(self, url: str, elements: ResultSet, target_element_id: int):
        self.url = url
        self.elements = elements
        self.target_element_id = target_element_id

    def get_elements(self) -> Generator[PageElement, None, None]:
        for element in self.elements:
            yield element

    def __repr__(self):
        return f"URL: {self.url}, ELEMENTS: {self.elements}"
