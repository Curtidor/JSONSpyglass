import json

from typing import Dict, List, Any, Tuple, Generator

from loaders.response_loader import ResponseLoader
from scraping.crawler import Crawler
from utils.logger import Logger, LoggerLevel
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
        _target_url_table (dict): Table of target URLs and their options.
        _parsing_options_cache (dict): Cache for data parsing options.
    """

    def __init__(self, config_file_path: str):
        self.config_file_path = config_file_path

        self.config_data = self.load_config()

        self._total_elements = 0
        self._element_names = set()
        self._target_url_table = {}
        self._parsing_options_cache = {}
        self._build_target_url_table()
        self.format_config()

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

    def get_crawlers(self) -> Generator[Crawler, Any, Any]:
        """
        Generate Crawler instances based on configuration data.

        Yields:
            Crawler: A Crawler instance.
        """
        seeds = self.get_target_urls()
        NO_CRAWLER_FOUND = 'no_crawler_found'
        crawler_options_collection = [crawler_data.get('crawler', NO_CRAWLER_FOUND) for crawler_data in
                                      self.config_data.get('target_urls')]
        # for every target_url there's an url, so we can safely use the index from crawler_options_collection to
        # index the seeds list as they are in the same order and of the same length
        for index, crawler_options_raw_data in enumerate(crawler_options_collection):
            render_pages = self._target_url_table.get(seeds[index], {}).get('render_pages', False)
            if crawler_options_raw_data == NO_CRAWLER_FOUND:
                crawler_options = Crawler(seeds[index], [ResponseLoader.get_domain(seeds[index])],
                                          render_pages=render_pages)
            else:
                crawler_options = Deserializer.deserialize(Crawler(seeds[index], [], render_pages=render_pages),
                                                           crawler_options_raw_data)
            yield crawler_options

    def only_scrape_sub_pages(self, url: str) -> bool:
        """
        Check if a target URL is set to only scrape sub-pages.

        Args:
            url (str): The URL to be checked.

        Returns:
            bool: True if only sub-pages are to be scraped, False otherwise.
        """
        if self._target_url_table:
            return self._target_url_table.get(url, {}).get('only_scrape_sub_pages', False)

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
            if element.get('tag', "") or element.get('search_hierarchy'):
                element_type = "target"
            elif element.get('css_selector', ""):
                element_type = "selector"

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
                Logger.console_log(
                    f"element has no data parsing options specified, collect data will be ignored: {element}",
                    LoggerLevel.WARNING)
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

    def format_config(self) -> None:
        """
        Format the configuration data by setting defaults and IDs for elements.
        """
        for index, (_, element) in enumerate(self.get_raw_target_elements()):
            element["id"] = index
            element_name = element.get('name', None)
            if not element_name:
                element["name"] = f"element {index}"
            self._element_names.add(element_name)

    def _build_target_url_table(self) -> None:
        """
        Build the target URL table using configuration data.
        """
        for url_data in self.config_data.get('target_urls', []):
            url = url_data.get('url')
            options = url_data.get('options', {})
            self._target_url_table.update({url: self._build_options(url, options)})

    @staticmethod
    def _build_options(url: str, options: Dict) -> Dict[str, bool]:
        """
        Build options for a target URL with default values.

        Args:
            url (str): The target URL.
            options (Dict): User-defined options.

        Returns:
            Dict[str, bool]: Built options.
        """
        DEFAULT_OPTIONS = {'only_scrape_sub_pages': True, 'render_pages': False}
        for option in DEFAULT_OPTIONS:
            if options.get(option) is None:
                Logger.console_log(
                    f"missing options argument in target url: {url} missing option: {option}, defaulting to {DEFAULT_OPTIONS[option]}",
                    LoggerLevel.WARNING)
                options.update({option: DEFAULT_OPTIONS[option]})
        return options
