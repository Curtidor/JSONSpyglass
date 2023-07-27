import re
from typing import Generator, Tuple

from bs4 import PageElement

from loaders.config_loader import ConfigLoader
from models.scarped_data import ScrapedData


class DataParser:
    def __init__(self, config: ConfigLoader, result_data: list[ScrapedData]):
        self.config = config
        self.result_data = result_data

    def parse_data(self) -> list[str]:
        cleaned_data = []

        if not self.result_data:
            print("WARNING: No data to parse")
            return []

        for element, element_id in self.get_elements():
            parsing_data = self.config.get_data_parsing_options(element_id)

            if parsing_data.get("collect_text"):
                cleaned_data.append(element.text)

            elif parsing_data.get("remove_tags"):
                cleaned_data.append(str(element.unwrap()))

        return cleaned_data

    def get_elements(self) -> Generator[Tuple[PageElement, int], None, None]:
        for scraped_data in self.result_data:
            target_element_id = scraped_data.target_element_id
            for element in scraped_data.get_elements():
                yield element, target_element_id

    @staticmethod
    def remove_special_characters(text: str) -> str:
        special_characters_pattern = r'[^\w\s]'  # Matches any non-word character and non-whitespace character

        cleaned_text = re.sub(special_characters_pattern, '', text)

        return cleaned_text
