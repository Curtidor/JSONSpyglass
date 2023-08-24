import json
import re
from typing import Dict, List, Any, Tuple, Generator

from loaders.response_loader import ResponseLoader
from scraping.crawler import Crawler
from utils.logger import Logger, LoggerLevel
from utils.deserializer import Deserializer


class ConfigLoader:
    def __init__(self, config_file_path: str):
        self.config_file_path = config_file_path
        self.config_data = self.load_config()

        self._target_url_table = {}
        self._parsing_options_cache = {}
        self._formate_config()
        self._build_target_url_table()

    def load_config(self) -> dict:
        try:
            with open(self.config_file_path) as file:
                return json.load(file)
        except Exception as e:
            raise Exception(f"Failed to load the config file: {e}")

    def get_setup_information(self) -> Generator[Tuple[str, Crawler], Any, Any]:
        # target urls are stored in a list of dicts
        # this code loops over each dict and gets the first key (the url)
        urls = [url_data.get('url', 'invalid_url_formate') for url_data in self.config_data.get("target_urls", [])]

        if not urls:
            raise Exception(f"No urls where found in config: {self.config_file_path}, at least one is required")

        for url, crawler_data in zip(urls, self._build_crawlers_setup_data(urls)):
            yield url, crawler_data

    def only_scrape_sub_pages(self, url: str) -> bool:
        """Check if a target URL is scrapable based on the configuration.

        This method checks whether a given URL is allowed for scraping, according to the configuration data
        provided in the 'target_urls' section. The 'target_urls' configuration specifies which URLs are
        considered scrapable and which are not based on the urls corresponding value. true we scrape the target
        and its sub-pages, false we only scrape the sub-pages

        Args:
            url (str): The URL to be checked for scrapability.

        Note:
            If the url is not in the table, it is assumed to be scrapable, as this function only checks the
            urls specified in the configuration file.

        Returns:
            bool: True if the URL is allowed for scraping, False otherwise.
        """
        if self._target_url_table:
            return self._target_url_table.get(url, {}).get('only_scrape_sub_pages', False)

    def get_raw_target_elements(self) -> Generator[Tuple[str, Dict[Any, Any]], None, None]:
        """
        Generator function to yield raw target elements or selectors from the configuration.

        Yields:
            Tuple[str, Dict[Any, Any]]: A tuple where the first element is 'target' or 'selector',
                                       and the second element is the raw element configuration.
        """
        elements = self.config_data.get("elements", [])

        if not elements:
            raise ValueError(f"No elements were found in the file: {self.config_file_path}")

        for element in elements:
            element_type = "BAD SELECTOR"
            # we treat search hierarchies the same as target elements as all target elements are
            # formatted into search hierarchies
            if element.get('tag', "") or element.get('search_hierarchy'):
                element_type = "target"
            elif element.get('css_selector', ""):
                element_type = "selector"

            yield element_type, element

    def get_data_parsing_options(self, element_id: int) -> dict:
        options = self._parsing_options_cache.get(element_id)

        # if a cache value is found return it
        if options:
            return options

        # else manually search for the element
        for _, element in self.get_raw_target_elements():
            if element.get("id") != element_id:
                continue

            # get the data parsing options from the element
            element_parsing_data = element.get('data_parsing', '')
            # if there's no data parsing options inform the user
            if not element_parsing_data:
                Logger.console_log(
                    f"element has no data parsing options specified, collect data will be ignored: {element}",
                    LoggerLevel.WARNING)
            # if there is data parsing options update the cache with its id and parsing options
            else:
                self._parsing_options_cache.update({element_id: element_parsing_data})

            # return the elements data parsing data
            return element_parsing_data

        # no data parsing options where found
        return {}

    def get_saving_data(self) -> Dict[Any, Any]:
        return self.config_data.get('data_saving')

    def get_data_order(self) -> List[str]:
        return self.config_data.get('data_order', None)

    def _formate_config(self):
        index_id = 0
        for _, element in self.get_raw_target_elements():
            if element.get("id"):
                continue
            element["id"] = index_id
            index_id += 1

    def _build_crawlers_setup_data(self, urls: List[str]) -> Generator[Crawler, Any, Any]:
        NO_CRAWLER_FOUND = 'no_crawler_found'

        crawler_options_collection = [crawler_data.get('crawler', NO_CRAWLER_FOUND) for crawler_data in self.config_data.get('target_urls')]
        # for every target_url there's an url, so we can safely use the index from crawler_options_collection to
        # index the urls list as they are in the same order and of the same length
        for index, crawler_options_raw_data in enumerate(crawler_options_collection):
            if crawler_options_raw_data == NO_CRAWLER_FOUND:
                crawler_options = Crawler(urls[index], [ResponseLoader.get_domain(urls[index])])
            else:
                crawler_options = Deserializer.deserialize(Crawler(urls[index], []), crawler_options_raw_data)
            yield crawler_options

    def _build_target_url_table(self):
        for url_data in self.config_data.get('target_urls', []):
            url = url_data.get('url')

            options = url_data.get('options', {})
            # incase the options dict doesn't hava all the proper arguments instead of throwing a error we
            # build the rest of the options with specified default values
            self._target_url_table.update({url: ConfigLoader._build_options(url, options)})

    @staticmethod
    def _build_options(url: str, options: Dict) -> Dict:
        DEFAULT_OPTIONS = {'only_scrape_sub_pages': True, 'render_pages': False}

        for option in DEFAULT_OPTIONS:
            if options.get(option) is None:
                Logger.console_log(
                    f"missing options argument in target url: {url} missing option: {option}, defaulting to {DEFAULT_OPTIONS[option]}",
                    LoggerLevel.WARNING)
                options.update({option: DEFAULT_OPTIONS[option]})

        return options
