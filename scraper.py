import asyncio

from scraping.data_parser import DataParser
from events.event_dispatcher import EventDispatcher
from loaders.config_loader import ConfigLoader
from loaders.response_loader import ResponseLoader
from scraping.crawler import Crawler
from scraping.data_saver import DataSaver
from scraping.data_scraper import DataScraper
from factories.config_element_factory import ConfigElementFactory

# Use named constants for better readability
EMPTY_RESPONSE_THRESHOLD = 10


async def main():
    print("STARTING..")

    event_dispatcher = EventDispatcher(debug_mode=False)
    event_dispatcher.start()

    config = ConfigLoader('configs/books.toscrape.com.json')

    elements = ConfigElementFactory.create_elements(config.get_raw_target_elements(), config.get_data_order())

    data_saver = DataSaver(config.get_saving_data(), config.get_data_order())
    data_saver.setup()
    data_scraper = DataScraper(config, elements, event_dispatcher, EMPTY_RESPONSE_THRESHOLD)
    data_parser = DataParser(config, event_dispatcher, data_saver)

    ResponseLoader.setup(event_dispatcher=event_dispatcher)

    for url, crawler in config.get_setup_information():
        print("RUNNING CRAWLER")
        crawler.start()
        await crawler.exit()

    print("END...")

if __name__ == "__main__":
    asyncio.run(main())
