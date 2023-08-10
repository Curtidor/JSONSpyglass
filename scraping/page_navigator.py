import re

from typing import Generator
from urllib.parse import urlparse, urljoin

from utils.deserializer import Deserializer
from events.event_dispatcher import EventDispatcher, Event
from utils.logger import Logger, LoggerLevel

# TODO
# fix bugs in parse_hrefs


class PageNavigator:
    def __init__(self, page_navigator_json: dict, event_dispatcher: EventDispatcher, debug_mode: bool = False):
        self.debug_mode = debug_mode
        self.base_url = ""
        self.allowed_domains = []
        self.target_elements = []
        self.url_pattern = ""
        self.sleep_time = 0
        self.max_depth = 5

        Deserializer.deserialize(self, page_navigator_json)

        self.event_dispatcher = event_dispatcher
        # listen for new hrefs found by the data scaper
        self.event_dispatcher.add_listener("new_hrefs", self.parse_hrefs)

    def parse_hrefs(self, event) -> None:
        # this function has a few bugs and need to be worked fixed later, for now its functional enough

        # use a set to avoid any potential duplicate urls
        urls = set()
        for href in event.data:

            href_url_match = re.search(r'<a[^>]* href="([^"]*)"', str(href))
            if not href_url_match:
                if self.debug_mode: 
                    Logger.console_log(f"Bad href: {href}", LoggerLevel.INFO)
                continue

            href_url = href_url_match.group(1)
            if self.is_valid_href(self.url_pattern, href_url):
                urls.add(urljoin(self.base_url, href_url))

        self.event_dispatcher.trigger(Event("new_urls", "data_update", data=urls))

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
