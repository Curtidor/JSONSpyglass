import json
from typing import Dict, List, Any, Tuple, Generator

from utils.logger import Logger, LoggerLevel


class ConfigLoader:
    def __init__(self, config_file_path: str):
        self._parsing_options_cache = {}

        self.config_file_path = config_file_path
        self.config_data = self.load_config()

        self._target_url_table = {}
        self._formate_config()

    def load_config(self) -> dict:
        try:
            with open(self.config_file_path) as file:
                return json.load(file)
        except Exception as e:
            raise Exception(f"Failed to load the config file: {e}")

    def get_target_urls(self) -> List[str]:
        # target urls are stored in a list of dicts
        # this code loops over each dict and gets the first key (the url)
        urls = [next(iter(url)) for url in self.config_data.get("target_urls", [])]

        if not urls:
            raise Exception(f"No urls where found in config: {self.config_file_path}, at least one is required")

        return urls

    def is_target_url_scrapable(self, url: str) -> bool:
        """Check if a target URL is scrapable based on the configuration.

        This method checks whether a given URL is allowed for scraping, according to the configuration data
        provided in the 'target_urls' section. The 'target_urls' configuration specifies which URLs are
        considered scrapable and which are not based on the urls corresponding value.

        Args:
            url (str): The URL to be checked for scrapability.

        Note:
            If the url is not in the table, it is assumed to be scrapable, as this function only checks the
            urls specified in the configuration file.

        Returns:
            bool: True if the URL is allowed for scraping, False otherwise.
        """
        # if the table has been built return the value
        if self._target_url_table:
            return self._target_url_table.get(url, True)

        # otherwise build the table then return the value
        for url_data in self.config_data.get('target_urls', []):
            self._target_url_table.update(url_data)

        return self._target_url_table.get(url, True)

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
            if element.get('tag', ""):
                element_type = "target"
            elif element.get('css_selector', ""):
                element_type = "selector"
            else:
                raise ValueError(f"Invalid element configuration: {element}")

            yield element_type, element

    def _formate_config(self):
        index_id = 0
        for _, element in self.get_raw_target_elements():
            if element.get("id"):
                continue
            element["id"] = index_id
            index_id += 1

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

    def has_page_navigator(self) -> bool:
        elements = self.get_raw_target_elements()

        for _, element in elements:
            if element.get('page_navigator'):
                return True

        return self.config_data.get('page_navigator') is not None

    def get_raw_page_navigator_data(self, element_id) -> dict:
        elements = self.get_raw_target_elements()

        for _, element in elements:
            if element.get('page_navigator') != element_id:
                continue
            return element.get('page_navigator')

        return {}

    def get_raw_global_page_navigator_data(self) -> dict:
        page_nav_data = self.config_data.get('page_navigator')

        if not page_nav_data:
            Logger.console_log(f"No page navigation data in config: {self.config_file_path}", LoggerLevel.WARNING)

        return page_nav_data
