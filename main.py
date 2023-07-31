import re

from data_scaper import DataScraper
from models.target_element import TargetElement
from loaders.config_loader import ConfigLoader
from loaders.response_loader import ResponsesLoader

config = ConfigLoader('configs/books.toscrape.com.json')
target_elements = TargetElement.create_target_elements(config.get_raw_target_elements())

ds = DataScraper(target_elements)

ResponsesLoader.add_urls(config.get_target_urls())
ResponsesLoader.collect_responses()



"""
cleaned_data = DataParser(config, raw_data).parse_data()

for elements in DataParser(config, raw_data).parse_data():
    print("NEW DATA SET")
    for element in elements:
        cleaned_string = re.sub(r'\s+', ' ', element)
        print(cleaned_string)
        
"""


