from scraping.data_parser import DataParser
from events.event_dispatcher import EventDispatcher
from loaders.config_loader import ConfigLoader
from loaders.response_loader import ResponsesLoader
from scraping.data_scaper import DataScraper
from scraping.page_navigator import PageNavigator
from factories.config_element_factory import ConfigElementFactory
print("STARING..")

event_dispatcher = EventDispatcher(debug_mode=False)


config = ConfigLoader('configs/scrapethissite.com.json')

responses_loader = ResponsesLoader(config, event_dispatcher)

elements = ConfigElementFactory.create_elements(config.get_raw_target_elements())
ds = DataScraper(config, elements, event_dispatcher, 10)
dp = DataParser(config, event_dispatcher)
pg = PageNavigator(config.get_raw_global_page_navigator_data(), event_dispatcher)

# this will start everything by getting the initial responses
responses_loader.collect_responses()

print("END...")