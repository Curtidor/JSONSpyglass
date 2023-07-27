import re

from data_scaper import DataScraper
from data_parser import DataParser
from models.target_element import TargetElement
from loaders.config_loader import ConfigLoader
from page_navigator import PageNavigator

config = ConfigLoader('configs/books.toscrape.com.json')
target_elements = TargetElement.create_target_elements(config.get_raw_target_elements())

pn = PageNavigator(config)
print(pn)

raw_data = DataScraper(config, target_elements).collect_data()

cleaned_data = DataParser(config, raw_data).parse_data()

for element in cleaned_data:
    cleaned_string = re.sub(r'\s+', ' ', element)
    print(cleaned_string)


