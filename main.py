from loaders.config_loader import ConfigLoader
from loaders.response_loader import ResponsesLoader
from models.target_element import TargetElement
from data_scaper import DataScraper

print("STARING..")

def dparser(item):
    print(item)


config = ConfigLoader('configs/books.toscrape.com.json')

responses_loader = ResponsesLoader("responses")
responses_loader.add_urls(config.get_target_urls())

target_elements = TargetElement.create_target_elements(config.get_raw_target_elements())
ds = DataScraper(target_elements, dparser)
#dfq = DataScraper(target_elements, dparser)
responses_loader.collect_responses()


print("END...")