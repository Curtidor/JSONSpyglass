import re
from typing import Generator, Tuple, List

from loaders.config_loader import ConfigLoader
from models.scarped_data import ScrapedData
from utils.logger import Logger, LoggerLevel
from events.event_dispatcher import EventDispatcher, Event


class DataParser:
    def __init__(self, config: ConfigLoader, event_dispatcher: EventDispatcher):
        self.config = config
        event_dispatcher.add_listener("scraped_data", self.parse_data)

    def parse_data(self, event: Event) -> None:
        data_matrix = event.data
        if not data_matrix:
            return
        for scraped_data, element_id in self.get_elements(data_matrix):
            parsing_data = self.config.get_data_parsing_options(element_id)
            cleaned_data = []
            for element in scraped_data.get_elements():

                if parsing_data.get("collect_text"):
                    cleaned_data.append(element.text.strip())

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
            print(f'{cleaned_data}: {scraped_data.url} DATA')

    @staticmethod
    def get_elements(data_matrix: List[ScrapedData]) -> Generator[Tuple[ScrapedData, int], None, None]:
        for scraped_data in data_matrix:
            yield scraped_data, scraped_data.target_element_id

    @staticmethod
    def collect_attr_value(attr_name, element_text: str):
        value = re.search(f'{attr_name}="([^"]*)"', element_text)
        if value:
            return value.group(1)
        return ""
