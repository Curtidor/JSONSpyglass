import asyncio

from scraping.data_parser import DataParser
from events.event_dispatcher import EventDispatcher
from loaders.config_loader import ConfigLoader
from loaders.response_loader import ResponsesLoader
from scraping.data_scraper import DataScraper
from scraping.page_navigator import PageNavigator
from factories.config_element_factory import ConfigElementFactory

# Use named constants for better readability
EMPTY_RESPONSE_THRESHOLD = 10


async def main():
    print("STARTING..")

    event_dispatcher = EventDispatcher(debug_mode=False)
    event_dispatcher.start()

    # config = ConfigLoader('configs/books.toscrape.com.json')
    config = ConfigLoader('configs/scrape_this_site_sandbox/hockey_teams_pagination.json')

    responses_loader = ResponsesLoader(config, event_dispatcher)
    elements = ConfigElementFactory.create_elements(config.get_raw_target_elements())

    ds = DataScraper(config, elements, event_dispatcher, EMPTY_RESPONSE_THRESHOLD)
    dp = DataParser(config, event_dispatcher)
    pg = PageNavigator(config.get_raw_global_page_navigator_data(), event_dispatcher)

    # This will start everything by getting the initial responses
    await responses_loader.collect_responses()

    # Wait until the target response threshold is met
    await ds.wait_for_empty_responses_to_reach_threshold()

    # wait for final events to finish
    await event_dispatcher.close()

    print("END...")

if __name__ == "__main__":
    asyncio.run(main())
