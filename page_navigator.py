import re

from urllib.parse import urlparse, urljoin

from loaders.config_loader import ConfigLoader
from utils.deserializer import Deserializer
from loaders.response_loader import ResponsesLoader


class PageNavigator:
    def __init__(self, config: ConfigLoader):
        self.config = config
        self.page_nav_data = self.config.get_raw_page_navigator_data()

        self.allowed_domains = []
        self.target_elements = []
        self.url_pattern = ""
        self.sleep_time = 0
        self.max_depth = 5

        Deserializer.deserialize(self, self.page_nav_data)

    def navigate(self, base_url: str, hrefs: list[str]) -> None:
        urls = []
        for href in hrefs:
            if self.is_same_domain(base_url, href) and self.is_valid_href(href):
                urls.append(urljoin(base_url, href))

        rl = ResponsesLoader(urls)
        rl.collect_responses()

        for response in rl.get_responses(included_errors=False):
            pass
            #print(response)

    def is_valid_href(self, href: str) -> bool:
        # check if the urls path matches the specified pattern for valid url paths
        url_path_match = re.search(self.url_pattern, href)
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
