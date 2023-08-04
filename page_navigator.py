import re

from typing import Generator
from urllib.parse import urlparse, urljoin

from utils.deserializer import Deserializer
from events.observables.observable_list import ObservableList


class PageNavigator:
    def __init__(self, page_navigator_json: dict):

        self.allowed_domains = []
        self.target_elements = []
        self.url_pattern = ""
        self.sleep_time = 0
        self.max_depth = 5

        Deserializer.deserialize(self, page_navigator_json)
        ObservableList.add_listener_to_target("hrefs", self.show_hfres, collection_type=ObservableList)

    def show_hfres(self, event):
        print("AHHHHHH", event.data)

    @staticmethod
    def formate_urls(base_url: str, hrefs: str) -> Generator[str, None, None]:
        for href in hrefs:
            yield urljoin(base_url, href)

    @staticmethod
    def is_valid_href(url_pattern: str, href: str) -> bool:
        # check if the urls path matches the specified pattern for valid url paths
        url_path_match = re.search(url_pattern, href)
        if url_path_match:
            return True

        return False

    @staticmethod
    def is_same_domain(base_url, href):
        # Parse the base URL and href to get their components
        base_domain = urlparse(base_url).netloc
        href_domain = urlparse(href).netloc

        # If the domain of the href is empty, it's a relative link, so assume it's the same domain
        if not href_domain:
            return True

        # Check if the href domain is the same as the base domain
        return href_domain == base_domain

    def __repr__(self):
        return f"PageNavigator(allowed_domains={self.allowed_domains}, " \
               f"sleep_time={self.sleep_time}, " \
               f"url_pattern={self.url_pattern}, " \
               f"target_elements={self.target_elements})"
