import re
from typing import Generator, Tuple

from bs4 import PageElement

from loaders.config_loader import ConfigLoader
from models.scarped_data import ScrapedData
from utils.logger import Logger, LoggerLevel


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

            collect_attr_data = parsing_data.get("collect_attr_value")
            if collect_attr_data:
                if collect_attr_data.get('attr_name'):
                    name = collect_attr_data['attr_name']
                    value = self.collect_attr_value(name, str(element.unwrap()))
                    cleaned_data.append(value)
                else:
                    Logger.console_log(f'No attribute name found, missing {{"attr_name": "value"}}: FOUND => {collect_attr_data}', LoggerLevel.ERROR)

        return cleaned_data

    def get_elements(self) -> Generator[Tuple[PageElement, int], None, None]:
        for scraped_data in self.result_data:
            target_element_id = scraped_data.target_element_id
            for element in scraped_data.get_elements():
                yield element, target_element_id

    @staticmethod
    def collect_attr_value(attr_name, element_text: str):
        value = re.search(f'{attr_name}="([^"]*)"', element_text)
        if value:
            return value.group(1)
        return ""

    @staticmethod
    def remove_special_characters(text: str) -> str:
        special_characters_pattern = r'[^\w\s]'  # Matches any non-word character and non-whitespace character

        cleaned_text = re.sub(special_characters_pattern, '', text)

        return cleaned_text
