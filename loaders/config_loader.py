import json
from typing import Dict, List, Any

from utils.logger import Logger, LoggerLevel
from models.target_url import TargetURL


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
        # if the table has been built return the value
        if self._target_url_table:
            return self._target_url_table.get(url, True)

        # otherwise build the table then return the value
        for url_data in self.config_data.get('target_urls', []):
            self._target_url_table.update(url_data)

        return self._target_url_table.get(url, True)

    def get_raw_target_elements(self) -> List[Dict[Any, Any]]:
        elements = self.config_data.get("elements", [])

        if not elements:
            Logger.console_log(f"No elements where found in config: {self.config_file_path}", LoggerLevel.WARNING)

        return elements

    def _formate_config(self):
        index_id = 0
        for element in self.get_raw_target_elements():
            if element.get("id"):
                continue
            element["id"] = index_id
            index_id += 1

    def get_data_parsing_options(self, element_id: int) -> dict:
        elements = self.get_raw_target_elements()
        options = self._parsing_options_cache.get(element_id)

        # if a cache value is found return it
        if options:
            return options

        # else manually search for the element
        for element in elements:
            if element.get("id") != element_id:
                continue
            # if the element is found cache the element then return it
            self._parsing_options_cache.update({element_id: element.get('data_parsing')})
            return element.get('data_parsing')

        # no data parsing options where found
        return {}

    def has_page_navigator(self) -> bool:
        elements = self.get_raw_target_elements()

        for element in elements:
            if element.get('page_navigator'):
                return True

        return self.config_data.get('page_navigator') is not None

    def get_raw_page_navigator_data(self, element_id) -> dict:
        elements = self.get_raw_target_elements()

        for element in elements:
            if element.get('page_navigator') != element_id:
                continue
            return element.get('page_navigator')

        return {}

    def get_raw_global_page_navigator_data(self) -> dict:
        page_nav_data = self.config_data.get('page_navigator')

        if not page_nav_data:
            Logger.console_log(f"No page navigation data in config ({self.config_file_path})", LoggerLevel.INFO)

        return page_nav_data
