import asyncio
import re

from typing import List, Any, Generator, AsyncGenerator, Iterable, Set
from urllib.robotparser import RobotFileParser

from loaders.response_loader import ResponseLoader, ScrapedResponse
from utils.logger import LoggerLevel, Logger
from .page_manager import BrowserManager


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

    def collect_urls(self, urls: Iterable[str], scraped_responses: Iterable[ScrapedResponse]) \
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
            Logger.console_log(f"DEPTH {self._current_depth}", LoggerLevel.INFO)
            if self.has_crawl_delay:
                # If there's a crawl delay, process URLs one at a time
                # by popping a URL from the _to_visit set
                response_pairs = await ResponseLoader.load_responses(
                    self._to_visit.pop(),
                    render_pages=self.render_pages
                )
                await asyncio.sleep(self.crawl_delay)
            else:
                # If no crawl delay, process all URLs at once
                response_pairs = await ResponseLoader.load_responses(
                    *self._to_visit,
                    render_pages=self.render_pages
                )
                self._to_visit.clear()

            # loop over all the responses
            for url, response_info in response_pairs.items():
                self._visited.add(url)
                # if there are elements that need to be clicked and at least 1 of them
                # are unique put href element in the click set
                if response_info.href_elements and self._has_unique_element_handle(response_info):
                    # POTENTIAL DUPE BUG
                    self._response_with_href_elements.add(response_info)
                # else if a page was used with the response, it can be recycled
                elif response_info.page:
                    await BrowserManager.close_page(response_info.page, feed_into_pool=True)

            new_urls.update(self.collect_urls(response_pairs.keys(), response_pairs.values()))

            if self.render_pages:
                async for dy_url in self._handle_dynamic_ajax_content():
                    new_urls.add(dy_url)

            if not self._to_visit:
                # Once we have processed all the URLs in _to_visit, copy over all the new URLs and increase the depth
                self._to_visit.update(new_urls)
                self._current_depth += 1
                new_urls.clear()

    async def _scrape_dynamic_ajax_content(self) -> AsyncGenerator[ScrapedResponse, Any]:
        """
        Scrapes dynamic content by clicking on specified elements triggering AJAX requests
        and then waiting for the requests to finish before collecting data.

        This function clicks on specific elements, waits for AJAX requests to complete,
        and then gathers data from the loaded pages.
        """
        pages_to_close = []  # List to store pages that need to be closed

        while len(self._response_with_href_elements):
            page_info: ScrapedResponse = self._response_with_href_elements.pop()

            # Iterate through href elements and click them
            for click_element in page_info.href_elements:
                await click_element.click()

                responses = await ResponseLoader.load_responses(page_info.page.url, render_pages=True)
                # we can get the first value of the dict as we are only sending out 1 url, so we will only get 1 response
                response = next(iter(responses.values()))
                # Check if there are no href elements, or no unique elements
                # if so close the page
                if not response.href_elements or not self._has_unique_element_handle(response):
                    pages_to_close.append(response.page)

                yield response

        # Close all opened pages using asyncio.gather
        await asyncio.gather(*[BrowserManager.close_page(page, feed_into_pool=True) for page in pages_to_close])

    async def _handle_dynamic_ajax_content(self) -> AsyncGenerator[Generator[str, None, None], None]:
        """
        Handle dynamic AJAX content scraping, including handling click-through responses.

        This method is responsible for managing dynamic AJAX content scraping, and if the `render_pages` option is enabled,
        it handles responses with click-through elements.

        Yields:
            Generator[str, None]: A generator of URLs for further processing, or None if no URLs are found.
        """
        if self.render_pages:
            new_elements_to_click = set()
            async for response in self._scrape_dynamic_ajax_content():
                self._visited.add(response.url)
                # If there are href elements, we need to keep the page open.
                if response.href_elements and self._has_unique_element_handle(response):
                    new_elements_to_click.add(response)
                # Otherwise, we can return the page to the pool.
                else:
                    await BrowserManager.close_page(response.page, feed_into_pool=True)
                yield self.collect_urls([response.url], [response])

            self._response_with_href_elements.update(new_elements_to_click)

    def _has_unique_element_handle(self, scraped_response: ScrapedResponse) -> bool:
        """
        Check if the `ScrapedResponse` contains at least one unique `ElementHandle` in its `href_elements`.

        Args:
           scraped_response (ScrapedResponse): The `ScrapedResponse` to check for unique `ElementHandles`.

        Returns:
           bool: True if the provided `ScrapedResponse` has at least one unique `ElementHandle` in its `href_elements`,
           False otherwise. Duplicate elements are removed from the `href_elements` during the check.
        """
        # Create a set of all ElementHandles from the responses
        all_elements = {elem for response in self._response_with_href_elements for elem in response.href_elements}

        for element in reversed(scraped_response.href_elements):
            if element in all_elements:
                scraped_response.href_elements.remove(element)

        return len(scraped_response.href_elements) > 1

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
