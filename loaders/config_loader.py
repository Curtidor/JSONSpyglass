import json

from utils.logger import Logger, LoggerLevel


class ConfigLoader:
    def __init__(self, config_file_path: str):
        self._parsing_options_cache = {}

        self.config_file_path = config_file_path
        self.config_data = self.load_config()

        self._formate_config()

    def load_config(self) -> dict:
        try:
            with open(self.config_file_path) as file:
                return json.load(file)
        except Exception as e:
            raise Exception(f"Failed to load the config file: {e}")

    def get_target_urls(self) -> list:
        urls = self.config_data.get("target_urls", [])

        if not urls:
            Logger.console_log(f"No urls where found in config: {self.config_file_path}", LoggerLevel.WARNING)

        return urls

    def get_raw_target_elements(self) -> list[dict]:
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

    def get_raw_page_nav(self) -> dict:
        page_nav_data = self.config_data.get('page_navigator')

        if not page_nav_data:
            Logger.console_log(f"No page navigation data in config ({self.config_file_path})", LoggerLevel.INFO)

        return page_nav_data
