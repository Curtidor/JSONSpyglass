import re

from typing import Generator, Tuple, List
from selectolax.parser import Node

from events.event_dispatcher import EventDispatcher, Event
from loaders.config_loader import ConfigLoader
from models.scarped_data import ScrapedData
from scraping.data_saver import DataSaver
from utils.logger import Logger, LoggerLevel


class DataParser:
    def __init__(self, config: ConfigLoader, event_dispatcher: EventDispatcher, data_saver: DataSaver):
        self.config = config
        self.data_saver = data_saver

        event_dispatcher.add_listener("scraped_data", self.parse_data)

    async def parse_data(self, event: Event) -> None:
        url_element_pairs = event.data
        if not url_element_pairs:
            return

        cleaned_data = []

        for scraped_data, element_id in self.get_elements(url_element_pairs):
            parsing_data = self.config.get_data_parsing_options(element_id)

            for node in scraped_data.get_nodes():
                if parsing_data.get("collect_text"):
                    text = self.collect_text(node)
                    cleaned_data.append(text)
                elif parsing_data.get("remove_tags"):
                    cleaned_data.append(self.remove_tags(node))

                attr_data = parsing_data.get("collect_attr_value")
                if attr_data and attr_data.get('attr_name'):
                    cleaned_data.append(self.collect_attribute_value(str(node.unwrap()), attr_data['attr_name']))
                elif attr_data and not attr_data.get('attr_name'):
                    self.log_missing_attribute_name(attr_data)

        await self.data_saver.save(cleaned_data)

    @staticmethod
    def get_elements(scraped_data_list: List[ScrapedData]) -> Generator[Tuple[ScrapedData, int], None, None]:
        for scraped_data in scraped_data_list:
            yield scraped_data, scraped_data.target_element_id

    @staticmethod
    def collect_attribute_value(attr_name, element_text: str):
        match = re.search(f'{attr_name}="([^"]*)"', element_text)
        if match:
            return match.group(1)
        return ""

    @staticmethod
    def collect_text(node: Node) -> str:
        return node.text().strip()

    @staticmethod
    def remove_tags(node: Node) -> str:
        return str(node.unwrap())

    @staticmethod
    def log_missing_attribute_name(attr_data: dict) -> None:
        error_message = (
            f'No attribute name found for collecting attribute value, '
            f'missing {{"attr_name": "attr_value"}}: FOUND => {attr_data}'
        )
        Logger.console_log(error_message, LoggerLevel.ERROR)
