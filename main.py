from data_parser import DataParser
from events.event_dispatcher import EventDispatcher
from loaders.config_loader import ConfigLoader
from loaders.response_loader import ResponsesLoader
from models.target_element import TargetElement
from data_scaper import DataScraper
from page_navigator import PageNavigator

print("STARING..")

event_dispatcher = EventDispatcher(debug_mode=True)


def dparser(item):
    print(item)


config = ConfigLoader('configs/books.toscrape.com.json')

responses_loader = ResponsesLoader(config, event_dispatcher)

target_elements = TargetElement.create_target_elements(config.get_raw_target_elements())
dp = DataParser(config, event_dispatcher)
ds = DataScraper(target_elements, dparser, event_dispatcher)
pg = PageNavigator(config.get_raw_global_page_navigator_data(), event_dispatcher)

# this will start everything by getting the initial responses
responses_loader.collect_responses()

print("END...")