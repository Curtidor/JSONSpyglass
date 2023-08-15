import csv
import re
from typing import Generator, Tuple, List

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

    @staticmethod
    def get_elements(scraped_data_list: List[ScrapedData]) -> Generator[Tuple[ScrapedData, int], None, None]:
        for scraped_data in scraped_data_list:
            yield scraped_data, scraped_data.target_element_id

    @staticmethod
    def collect_attr_value(attr_name, element_text: str):
        match = re.search(f'{attr_name}="([^"]*)"', element_text)
        if match:
            return match.group(1)
        return ""

    def parse_data(self, event: Event) -> None:
        url_element_pairs = event.data
        if not url_element_pairs:
            return
        cleaned_data = []
        for scraped_data, element_id in self.get_elements(url_element_pairs):
            parsing_data = self.config.get_data_parsing_options(element_id)

            for element in scraped_data.get_elements():
                if parsing_data.get("collect_text"):
                    cleaned_data.append(element.text.strip())
                elif parsing_data.get("remove_tags"):
                    cleaned_data.append(str(element.unwrap()))

                attr_data = parsing_data.get("collect_attr_value")
                if attr_data and attr_data.get('attr_name'):
                    cleaned_data.append(self.collect_attr_value(attr_data['attr_name'], str(element.unwrap())))
                elif attr_data and not attr_data.get('attr_name'):
                    Logger.console_log(f'No attribute name found for collecting attributes value, '
                                       f'missing {{"attr_name": "attr_value"}}: FOUND => {attr_data}', LoggerLevel.ERROR)

        self.data_saver.save(cleaned_data)

    @staticmethod
    def write_to_csv(data, csv_file_path):
        # Split the data into book names and prices
        book_names = data[::3]
        prices = data[1::3]
        stock = data[2::3]

        book_names.insert(0, "BOOK NAME")
        prices.insert(0, "PRICES")
        stock.insert(0, "STOCK")

        # Combine book names and prices into rows
        rows = [book_names, prices, stock]

        # Write the rows to the CSV file
        with open('data.csv', mode='w', newline='') as csv_file:
            csv_writer = csv.writer(csv_file)
            csv_writer.writerows(rows)