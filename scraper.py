import asyncio

from scraping.data_parser import DataParser
from events.event_dispatcher import EventDispatcher
from loaders.config_loader import ConfigLoader
from loaders.response_loader import ResponseLoader
from scraping.data_saver import DataSaver
from scraping.data_scraper import DataScraper
from factories.config_element_factory import ConfigElementFactory

# TODO: add a feature to scrape multiple of the same element


async def main():
    print("STARTING..")

    event_dispatcher = EventDispatcher(debug_mode=True)
    event_dispatcher.start()

    config = ConfigLoader('configs/books.toscrape.com.json')
    # config = ConfigLoader('configs/scrap_this_site.com/Oscar_Winning_Films_AJAX_and_Javascript.json')

    elements = ConfigElementFactory.create_elements(config.get_raw_target_elements(), config.get_data_order())

    data_saver = DataSaver(config.get_saving_data(), config.get_data_order())
    data_saver.setup(clear=True)

    DataScraper(config, elements, event_dispatcher)
    DataParser(config, event_dispatcher, data_saver)

    await ResponseLoader.setup(event_dispatcher=event_dispatcher)

    for crawler in config.get_crawlers():
        crawler.start()
        await crawler.exit()

    print("END...")

if __name__ == "__main__":
    asyncio.run(main())
