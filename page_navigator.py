import re

from urllib.parse import urlparse

from loaders.config_loader import ConfigLoader
from utils.deserializer import Deserializer
from loaders.response_loader import ResponsesLoader


class PageNavigator:
    def __init__(self, config: ConfigLoader):
        self.config = config
        self.page_nav_data = self.config.get_raw_page_nav()

        self.allowed_domains = []
        self.target_elements = []
        self.url_pattern = ""
        self.sleep_time = 0
        self.max_depth = 5

        Deserializer.deserialize(self, self.page_nav_data)

    def navigate(self, base_url: str, hrefs: list[str]) -> None:
        urls = []
        for href in hrefs:
            if self.is_same_domain(base_url, href):
                print(href)

        rl = ResponsesLoader(urls)
        rl.collect_responses()
    def is_valid_url(self, url: str) -> bool:
        # check if its valid domain and if there is no domain then we assume it's valid
        domain_match = re.match(r'(?:https|http):\/\/([^\/]+)', url)
        if domain_match and domain_match.group(0) not in self.allowed_domains:
            return False

        # check if the urls path matches the specified pattern for valid url paths
        url_path_match = re.match(self.url_pattern, url)
        if url_path_match:
            return True

        # this return is reached when it's a valid domain but url path that
        # didn't match the pattern
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
