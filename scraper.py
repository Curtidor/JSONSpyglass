import asyncio

from EVNTDispatch import EventDispatcher

from factories.config_element_factory import ConfigElementFactory
from scraping.data_parser import DataParser
from scraping.data_saver import DataSaver
from scraping.data_scraper import DataScraper
from loaders.config_loader import ConfigLoader
from loaders.response_loader import ResponseLoader

# TODO: (FEATURE) add a feature to scrape multiple of the same element


async def load_and_scrape_data(config_path: str) -> None:
    # Load and configure the event dispatcher
    event_dispatcher = EventDispatcher(debug_mode=False)
    event_dispatcher.start()

    # Load the configuration
    config = ConfigLoader(config_path)

    # Create elements from the configuration
    elements = ConfigElementFactory.create_elements(config.get_raw_target_elements(), config.get_data_order())

    # Configure and set up the data saver
    data_saver = DataSaver(config.get_saving_data(), config.get_data_order())
    await data_saver.setup(clear=True)

    # Initialize data scraper and parser
    DataScraper(config, elements, event_dispatcher)
    DataParser(config, event_dispatcher, data_saver)

    # Set up the ResponseLoader
    ResponseLoader.setup(event_dispatcher=event_dispatcher)

    # Start and wait for crawlers to finish
    for crawler in config.get_crawlers():
        crawler.start()
        await crawler.exit()

    await event_dispatcher.close()


def main():
    print("STARTING...")

    asyncio.run(load_and_scrape_data('configs/books.toscrape.com.json'))
    # asyncio.run(load_and_scrape_data('configs/scrap_this_site.com/Oscar_Winning_Films_AJAX_and_Javascript.json'))

    print("END...")


if __name__ == "__main__":
    main()
