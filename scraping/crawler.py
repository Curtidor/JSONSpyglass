import asyncio
import re

from typing import List, Any, Generator, Iterable, Set, Dict
from urllib.robotparser import RobotFileParser

from playwright.async_api import Locator

from loaders.response_loader import ResponseLoader, ScrapedResponse
from utils.logger import LoggerLevel, Logger
from .page_manager import BrowserManager

# TODO (SPEED AND EFFICIENCY IMPROVEMENT) Need work on page management pages are closed to soon


class Crawler:
    """
    Asynchronous web crawler.

    seed (str): The starting URL for crawling.
    allowed_domains (List[str]): List of allowed domains to crawl.
    max_depth (int, optional): Maximum crawling depth. Defaults to 6.
    ignore_robots_txt (bool, optional): If True, ignore robots.txt rules. Defaults to False.
    crawl_delay (float, optional): Delay between requests in seconds. Defaults to 1.
    loop (asyncio.AbstractEventLoop, optional): Custom event loop to use. If not provided,
        a new event loop will be created. Defaults to None.
    user_agent (str, optional): User-Agent string for requests. Defaults to "*".
    """

    def __init__(self,
                 seed: str,
                 allowed_domains: List[str],
                 max_depth: int = 6,
                 crawl_delay: float = 1,
                 loop: asyncio.AbstractEventLoop = None,
                 ignore_robots_txt: bool = False,
                 render_pages: bool = False,
                 url_patters: List[str] = None,
                 user_agent: str = "*"):

        self.seed = seed
        self.allowed_domains = allowed_domains
        self.max_depth = max_depth
        self.ignore_robots_txt = ignore_robots_txt
        self.render_pages = render_pages
        self.crawl_delay = crawl_delay
        self.user_agent = user_agent
        self.url_patterns = url_patters

        self._current_depth = 0
        self._loop = None
        self._to_visit = set()
        self._visited = set()
        self._clicked_elements = set()
        self._running_tasks = set()

        self._response_with_href_elements: Set[ScrapedResponse] = set()
        self._processed_href_locators: Set[Locator] = set()

        # robot.txt parser
        self._robot_parser = RobotFileParser()
        self._robot_parser.set_url(self._get_robot_txt_url())
        self._robot_parser.read()

        # set event loop
        self._set_event_loop(loop=loop)

    @property
    def has_crawl_delay(self) -> bool:
        """
        Check if there is a crawl delay set.

        Returns:
            bool: True if crawl delay is set, False otherwise.
        """
        return self.crawl_delay > 0

    def start(self):
        """
        Start the crawling process.
        """
        if not self.ignore_robots_txt:
            crawl_delay = self._robot_parser.crawl_delay(self.user_agent)
            # if the robot.txt file specifies a crawl delay use it else use the one specified by the user
            self.crawl_delay = crawl_delay if crawl_delay else self.crawl_delay

        # add the initial link to the to-vist set
        self._to_visit.add(self.seed)

        task = self._loop.create_task(self._run())
        self._running_tasks.add(task)

    async def exit(self) -> None:
        """
        Waits for all crawling task to finish and print summary statistics on exit.
        """
        await asyncio.gather(*self._running_tasks)
        await BrowserManager.close()

        print("TOTAL SITES VISITED:", len(self._visited))
        print("SITES TO VISIT:", len(self._to_visit))

    def collect_child_urls_from_responses(self, urls: Iterable[str], scraped_responses: Iterable[ScrapedResponse]) \
            -> Generator[str, Any, Any]:
        """
        Collect URLs from scraped responses.

        Args:
            urls (Iterable[str]): Iterable of base URLs.
            scraped_responses (Iterable[ScrapedResponse]): Iterable of scraped responses.

        Yields:
            str:  URLs that meet the specified conditions.
        """
        for base_url, response in zip(urls, scraped_responses):
            # iterate through each href in the html
            for href in ResponseLoader.get_hrefs_from_html(response.html):
                child_url = ResponseLoader.build_link(base_url, href)
                if child_url not in self._visited and self._is_url_allowed(child_url):
                    yield child_url
                self._visited.add(child_url)

    async def _run(self):
        """
        Internal method to perform the crawling asynchronously.
        """
        await BrowserManager.initialize(self.render_pages)

        new_urls = set()
        while self._to_visit and self._current_depth <= self.max_depth:
            # Log crawler status
            Logger.console_log(f"DEPTH {self._current_depth}", LoggerLevel.INFO)

            # populate structure with all the urls to get responses from
            urls_to_get_responses_from = {self._to_visit.pop()} if self.has_crawl_delay else self._to_visit

            response_pairs = await ResponseLoader.load_responses(
                urls_to_get_responses_from,
                render_pages=self.render_pages
            )

            # if there's no crawl delay that means we sent all the urls to vist to be
            # processed, so we can clear the set
            if not self.has_crawl_delay:
                self._to_visit.clear()
            else:
                await asyncio.sleep(self.crawl_delay)

            # Process responses
            await self._process_responses(response_pairs)

            new_urls.update(
                self.collect_child_urls_from_responses(response_pairs.keys(), response_pairs.values())
            )

            if self.render_pages:
                await self._collect_button_redirect()

            if not self._to_visit:
                # Once we have processed all the URLs in _to_visit, copy over all the new URLs and increase the depth
                self._to_visit.update(new_urls)
                self._current_depth += 1
                new_urls.clear()

    async def _process_responses(self, response_pairs: Dict[str, ScrapedResponse]) -> None:
        """
        Process the responses and update crawled data and visited URLs.

        Args:
            response_pairs (Dict[str, ScrapedResponse]): A dictionary of URL-response pairs to process.
        """
        for url, response_info in response_pairs.items():
            self._visited.add(url)
            # if there are elements that need to be clicked and at least 1 of them
            # are unique, put href elements in the click set
            if response_info.href_elements and await self._has_unique_locator(response_info):
                # POTENTIAL DUPE BUG
                self._response_with_href_elements.add(response_info)
            # else if a page was used with the response, it can be recycled or closed
            elif response_info.page:
                await BrowserManager.close_page(response_info.page, feed_into_pool=True)

    async def _collect_button_redirect(self) -> None:
        """
        Clicks on all the buttons and puts the url they lead to into the to_vist set
        """

        collected_href_locators = [element for rwh_elements in self._response_with_href_elements for element in
                                   rwh_elements.href_elements]

        self._processed_href_locators.update(collected_href_locators)

        # while there is response with elements to click
        while len(self._response_with_href_elements):
            # get a response that has elements to click
            scraped_response: ScrapedResponse = self._response_with_href_elements.pop()

            for click_element in scraped_response.href_elements:
                await click_element.click()

                if click_element.page.url not in self._visited:
                    self._to_visit.add(click_element.page.url)

            # the page has clicked through all its elements and can now be reused
            await BrowserManager.close_page(scraped_response.page, feed_into_pool=True)

    async def _has_unique_locator(self, scraped_response: ScrapedResponse) -> bool:
        """
        Check if the `ScrapedResponse` contains at least one unique `Locator` in its `href_elements`.

        Args:
           scraped_response (ScrapedResponse): The `ScrapedResponse` to check for unique `Locator`.

        Returns:
           bool: True if the provided `ScrapedResponse` has at least one unique `Locator` in its `href_elements`,
           False otherwise. Duplicate elements are removed from the `href_elements` during the check.
        """
        P_LOCATOR_URLS = {p_locator.page.url for p_locator in self._processed_href_locators}

        unique_locators = []
        for locator in scraped_response.href_elements:
            if locator.page.url not in P_LOCATOR_URLS:
                unique_locators.append(locator)

        scraped_response.href_elements = unique_locators
        return len(scraped_response.href_elements) > 0

    def _set_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """
        Set the event loop, creating a new one if needed.
        """
        if not loop:
            try:
                self._loop = asyncio.get_running_loop()
            except RuntimeError:
                self._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._loop)
        else:
            self._loop = loop

    def _get_robot_txt_url(self) -> str:
        """
        Returns the URL to the robot txt file.

        Note:
            If no match is found or an invalid URL is returned, the robot parser's
            method can_fetch will always output the value True.

        Returns:
            str: The URL to the robot.txt file.
        """
        root_url = re.match(r'^https?://([^/]+)', self.seed).group(0)
        return f"{root_url}/robots.txt" if root_url else ""

    def _is_url_allowed(self, url: str) -> bool:
        """
        Check if the given URL is allowed for scraping.

        Args:
            url (str): The URL to check.

        Returns:
            bool: True if the URL is allowed; otherwise, False.
        """
        if self._is_url_allowed_by_patterns(url) and self._is_url_allowed_by_domain(url):
            return self._is_url_allowed_robot(url)
        return False

    def _is_url_allowed_by_patterns(self, url: str) -> bool:
        """
        Check if the URL matches any of the defined patterns.

        Args:
            url (str): The URL to check.

        Returns:
            bool: True if the URL matches a pattern or no patterns are defined; otherwise, False.
        """
        if not self.url_patterns:
            return True

        return any(re.search(pattern, url) for pattern in self.url_patterns)

    def _is_url_allowed_by_domain(self, url: str) -> bool:
        """
        Check if the domain of the given URL is in the set of allowed domains.

        Args:
            url (str): The URL to check.

        Returns:
            bool: True if the domain is allowed; otherwise, False.
        """
        return ResponseLoader.get_domain(url) in self.allowed_domains

    def _is_url_allowed_robot(self, url: str) -> bool:
        """
        Check if the URL is allowed according to the robots.txt rules.

        Args:
            url (str): The URL to check.

        Returns:
            bool: True if the URL is allowed by robots.txt, or we ignore the file; otherwise, False.
        """
        if self.ignore_robots_txt:
            return True
        return self._robot_parser.can_fetch(self.user_agent, url)

    def __repr__(self):
        return (
            f"Crawler("
            f"seed='{self.seed}', "
            f"allowed_domains={self.allowed_domains}, "
            f"user_agent='{self.user_agent}', "
            f"crawl_delay={self.crawl_delay}, "
            f"max_crawl_depth={self.max_depth}, "
            f"render_pages={self.render_pages}, "
            f"ignore_robots_txt={self.ignore_robots_txt})"
        )
