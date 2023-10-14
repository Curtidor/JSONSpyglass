import asyncio

from scraping.data_parser import DataParser
from events.event_dispatcher import EventDispatcher
from loaders.config_loader import ConfigLoader
from loaders.response_loader import ResponseLoader
from scraping.data_saver import DataSaver
from scraping.data_scraper import DataScraper
from factories.config_element_factory import ConfigElementFactory

# TODO: add a feature to scrape multiple of the same element


async def load_and_scrape_data():
    # Load and configure the event dispatcher
    event_dispatcher = EventDispatcher(debug_mode=True)
    event_dispatcher.start()

    # Load the configuration
    config = ConfigLoader('configs/scrap_this_site.com/Oscar_Winning_Films_AJAX_and_Javascript.json')

    # Create elements from the configuration
    elements = ConfigElementFactory.create_elements(config.get_raw_target_elements(), config.get_data_order())

    # Configure and set up the data saver
    data_saver = DataSaver(config.get_saving_data(), config.get_data_order())
    data_saver.setup(clear=True)

    # Initialize data scraper and parser
    DataScraper(config, elements, event_dispatcher)
    DataParser(config, event_dispatcher, data_saver)

    # Set up the ResponseLoader
    ResponseLoader.setup(event_dispatcher=event_dispatcher)

    # Start and wait for crawlers to finish
    for crawler in config.get_crawlers():
        crawler.start()
        await crawler.exit()


def main():
    print("STARTING...")

    asyncio.run(load_and_scrape_data())

    print("END...")


if __name__ == "__main__":
    main()