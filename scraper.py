import asyncio

from scraping.data_parser import DataParser
from events.event_dispatcher import EventDispatcher
from loaders.config_loader import ConfigLoader
from loaders.response_loader import ResponsesLoader
from scraping.data_scraper import DataScraper
from scraping.page_navigator import PageNavigator
from factories.config_element_factory import ConfigElementFactory


async def main():
    print("STARTING..")

    event_dispatcher = EventDispatcher(debug_mode=True)
    event_dispatcher.start()

    #  config = ConfigLoader('configs/scrape_this_site_sandbox/hockey_teams_pagination.json')
    config = ConfigLoader('configs/books.toscrape.com.json')

    responses_loader = ResponsesLoader(config, event_dispatcher)

    elements = ConfigElementFactory.create_elements(config.get_raw_target_elements())
    ds = DataScraper(config, elements, event_dispatcher, 10)
    dp = DataParser(config, event_dispatcher)
    pg = PageNavigator(config.get_raw_global_page_navigator_data(), event_dispatcher)

    # this will start everything by getting the initial responses
    await responses_loader.collect_responses()

    await event_dispatcher.close()

    print("END...")

if __name__ == "__main__":
    asyncio.run(main())
