import json
import logging

from typing import Dict, List, Any, Tuple, Generator

from EVNTDispatch import EventDispatcher

from loaders.response_loader import ResponseLoader
from scraping.crawler import Crawler
from utils.clogger import CLogger
from utils.deserializer import Deserializer


class ConfigLoader:
    """
    Loads and processes configuration data for scraping.

    Args:
        config_file_path (str): Path to the configuration file.

    Attributes:
        config_file_path (str): The path to the configuration file.
        config_data (dict): The loaded configuration data.
        _total_elements (int): Total number of elements.
        _element_names (set): Set of element names.
        _options_url_table (dict): Table of target URLs and their options.
        _parsing_options_cache (dict): Cache for data parsing options.
    """

    def __init__(self, config_file_path: str):
        self.config_file_path = config_file_path

        self.config_data = self.load_config()

        self._total_elements = 0
        self._element_names = set()

        # dict[url, options_data]
        self._options_url_table = {}
        # dict[url, response_loader_data]
        self._response_loader_table = {}
        self._crawler_table = {}
        self._parsing_options_cache = {}

        self._logger = CLogger("ConfigLoafer", logging.INFO, {logging.StreamHandler(): logging.INFO})

        self._build_tables()
        self._format_config()

    def load_config(self) -> dict:
        """
        Load configuration data from the specified file.

        Returns:
            dict: The loaded configuration data.

        Raises:
            FileNotFoundError: If the configuration file is not found.
            json.JSONDecodeError: If there's an issue with JSON decoding.
        """
        try:
            with open(self.config_file_path) as file:
                return json.load(file)
        except FileNotFoundError as e:
            raise FileNotFoundError(f"Config file not found: {self.config_file_path}") from e
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to decode JSON in config file: {self.config_file_path}") from e

    def get_target_urls(self) -> List[str]:
        """
        Get a list of target URLs from the configuration data.

        Returns:
            List[str]: List of target URLs.

        Raises:
            ValueError: If no valid URLs are found in the configuration.
        """
        urls = [url.get('url') for url in self.config_data.get("target_urls", []) if url.get('url')]
        if not urls:
            raise ValueError(f"No valid URLs found in config: {self.config_file_path}")

        return urls

    def get_crawlers(self, dispatcher: EventDispatcher) -> Generator[Crawler, Any, Any]:
        """
        Generate Crawler instances based on configuration data.

        Yields:
            Crawler: A Crawler instance.
        """
        seeds = self.get_target_urls()

        crawler_options_collection = [self._crawler_table[url] for url in self._crawler_table]

        for url, crawler_options_raw_data, response_loader in zip(seeds, crawler_options_collection, self._get_response_loaders(dispatcher)):
            crawler = Crawler(url, [], response_loader)
            Deserializer.deserialize(crawler, crawler_options_raw_data)

            yield crawler

    def _get_response_loaders(self, dispatcher: EventDispatcher) -> Generator[ResponseLoader, None, None]:
        seeds = self.get_target_urls()

        response_loader_collection = [self._response_loader_table[url] for url in self._response_loader_table]

        for urls, response_loader_data in zip(seeds, response_loader_collection):
            response_loader = ResponseLoader(dispatcher, False, False, 0, 0)
            Deserializer.deserialize(response_loader, response_loader_data)

            yield response_loader

    def only_scrape_sub_pages(self, url: str) -> bool:
        """
        Check if a target URL is set to only scrape sub-pages.

        Args:
            url (str): The URL to be checked.

        Returns:
            bool: True if only sub-pages are to be scraped, False otherwise.
        """
        return self._options_url_table.get(url, {}).get('only_scrape_sub_pages', False)

    def get_raw_target_elements(self) -> Generator[Tuple[str, Dict[Any, Any]], None, None]:
        """
        Generate raw target elements or selectors from the configuration.

        Yields:
            Tuple[str, Dict[Any, Any]]: A tuple where the first element is 'target' or 'selector',
                                       and the second element is the raw element configuration.
        """
        elements = self.config_data.get("elements", [])

        for element in elements:
            element_type = "BAD SELECTOR"
            # we treat search hierarchies the same as target elements as all target elements are
            # formatted into search hierarchies
            if element.get('search_hierarchy', '') or element.get('css_selector', ''):
                element_type = "target"

            yield element_type, element

    def get_data_parsing_options(self, element_id: int) -> dict:
        """
        Get data parsing options for a given element ID.

        Args:
            element_id (int): The ID of the element.

        Returns:
            dict: Data parsing options for the element.
        """
        options = self._parsing_options_cache.get(element_id)

        if options:
            return options

        for _, element in self.get_raw_target_elements():
            if element.get("id") != element_id:
                continue

            element_parsing_data = element.get('data_parsing', '')
            if not element_parsing_data:
                self._logger.info(f"element has no data parsing options specified, collect data will be ignored: {element}")
            else:
                self._parsing_options_cache.update({element_id: element_parsing_data})

            return element_parsing_data

        return {}

    def get_saving_data(self) -> Dict[Any, Any]:
        """
        Get data saving options from the configuration.

        Returns:
            Dict[Any, Any]: Data saving options.
        """
        return self.config_data.get('data_saving')

    def get_data_order(self) -> List[str]:
        """
        Get the order of data elements based on configuration.

        Returns:
            List[str]: Ordered list of data element names.

        Raises:
            ValueError: If an element name in the data order is not found.
        """
        data_order = self.config_data.get('data_order', [])

        if len(data_order) != self._total_elements:
            for element_name in self._element_names:
                if element_name not in data_order:
                    data_order.append(element_name)

        unique_data_order = []
        for item in data_order:
            if item not in unique_data_order:
                unique_data_order.append(item)
            if item not in self._element_names:
                raise ValueError(f"Unknown name in data-order: {item}")
        return unique_data_order

    def _format_config(self) -> None:
        """
        Format the configuration data by setting defaults and IDs for elements.
        """
        for index, (_, element) in enumerate(self.get_raw_target_elements()):
            element["id"] = index
            element_name = element.get('name', None)
            if not element_name:
                element["name"] = f"element {index}"
            self._element_names.add(element_name)

    def _build_tables(self) -> None:
        """
        Build the options and response_loader table using configuration data.
        """
        for url_data in self.config_data.get('target_urls', []):
            url = url_data.get('url')

            options_data = url_data.get('options', {})
            response_data = url_data.get('response_loader', {})
            crawler_data = url_data.get('crawler', {})

            options_table = self._build_table(url, options_data, {'only_scrape_sub_pages': True})
            response_loader_table = self._build_table(url, response_data, {'use_proxies': False, 'render_pages': False, 'max_retires': 0})
            crawler_table = self._build_table(url, crawler_data, {'ignore_robots_txt': False, 'crawl_delay': 0.1, 'max_depth': 6, 'allowed_domains': [ResponseLoader.get_domain(url)]})

            self._options_url_table.update({url: options_table})
            self._response_loader_table.update({url: response_loader_table})
            self._crawler_table.update({url: crawler_table})

    def _build_table(self, url: str, user_specified_options: Dict, default_options: Dict) -> Dict[str, bool]:
        """
        Build options for a target URL with default values.

        Args:
            url (str): The target URL.
            user_specified_options (Dict): User-defined options.

        Returns:
            Dict[str, bool]: Built options.
        """
        for option in default_options:
            if user_specified_options.get(option) is None:
                self._logger.warning(
                    f"missing options argument in target url: {url} missing option: {option}, defaulting to {default_options[option]}"
                )
                user_specified_options.update({option: default_options[option]})
        return user_specified_options

