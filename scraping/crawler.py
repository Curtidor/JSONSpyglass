import asyncio
import re

from asyncio import Queue
from typing import List, Any, Generator, AsyncGenerator, Iterable
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
        self._elements_to_click = Queue()

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
            self.crawl_delay = crawl_delay if crawl_delay else self.crawl_delay

        self._to_visit.add(self.seed)
        task = self._loop.create_task(self._run())
        self._running_tasks.add(task)

    async def exit(self):
        """
        Print summary statistics on exit.
        """
        await asyncio.gather(*self._running_tasks)
        print("TOTAL SITES VISITED:", len(self._visited))
        print("SITES TO VISIT:", len(self._to_visit))

    def collect_urls(self, urls: Iterable[str], scraped_responses: Iterable[ScrapedResponse]) \
            -> Generator[str, Any, Any]:
        for base_url, response in zip(urls, scraped_responses):
            for href in ResponseLoader.get_hrefs_from_html(response.html):
                child_url = ResponseLoader.build_link(base_url, href)
                if child_url not in self._visited and self._is_url_allowed(child_url):
                    yield child_url
                self._visited.add(child_url)

    async def scrape_dynamic_ajax_content(self) -> AsyncGenerator[ScrapedResponse, Any]:
        """
        Scrapes dynamic content by clicking on specified elements triggering AJAX requests
        and then waiting for the requests to finish before collecting data.

        This function clicks on specific elements, waits for AJAX requests to complete,
        and then gathers data from the loaded pages.
        """
        pages_to_close = []  # List to store pages that need to be closed

        # Iterate through the elements to click in the queue
        while not self._elements_to_click.empty():
            page_info: ScrapedResponse = await self._elements_to_click.get()

            # Iterate through href elements and click them
            for click_element in page_info.href_elements:
                await click_element.click()

                responses = await ResponseLoader.load_responses(page_info.page.url, render_pages=True)
                # we can get the first value of the dict as we are only sending out 1 url, so we will only get 1 response
                response = next(iter(responses.values()))
                # if there are no elements to click we can close the page
                # as its no longer need
                if not response.href_elements:
                    pages_to_close.append(response.page)

                yield response

            # Mark the element as processed
            self._elements_to_click.task_done()

        # Close all opened pages using asyncio.gather
        await asyncio.gather(*[BrowserManager.close_page(page, feed_into_pool=True) for page in pages_to_close])

    async def _run(self):
        """
        Internal method to perform the crawling asynchronously.
        """

        new_urls = set()
        while self._to_visit and self._current_depth <= self.max_depth:
            Logger.console_log(f"DEPTH {self._current_depth}", LoggerLevel.INFO)
            if self.has_crawl_delay:
                # If there's a crawl delay, process URLs one at a time
                # by popping a URL from the _to_visit set
                response_pairs = await ResponseLoader.load_responses(self._to_visit.pop(),
                                                                     render_pages=self.render_pages)
                await asyncio.sleep(self.crawl_delay)
            else:
                # If no crawl delay, process all URLs at once
                response_pairs = await ResponseLoader.load_responses(*self._to_visit, render_pages=self.render_pages)
                self._to_visit.clear()

            for url, response_info in response_pairs.items():
                self._visited.add(url)
                # if there are elements that need to be clicked
                if response_info.href_elements:
                    self._elements_to_click.put_nowait(response_info)
                elif self.render_pages and not response_info.href_elements:
                    await BrowserManager.close_page(response_info.page, feed_into_pool=True)

            new_urls.update(self.collect_urls(response_pairs.keys(), response_pairs.values()))

            if self.render_pages:
                responses_to_click_through = []
                async for response in self.scrape_dynamic_ajax_content():
                    self._visited.add(response.url)
                    # if there are href elements we need to keep the page open
                    if response.href_elements:
                        responses_to_click_through.append(response)
                    # else we can return the page to the pool
                    else:
                        await BrowserManager.close_page(response.page, feed_into_pool=True)
                    new_urls.update(self.collect_urls([response.url], [response]))
                for response_to_click_through in responses_to_click_through:
                    if response_to_click_through.url in self._visited:
                        await BrowserManager.close_page(response_to_click_through.page, feed_into_pool=True)
                        continue
                    self._elements_to_click.put_nowait(response_to_click_through)

            if not self._to_visit:
                # Once we have processed all the URLs in _to_visit, copy over all the new URLs and increase the depth
                self._to_visit.update(new_urls)
                self._current_depth += 1
                new_urls.clear()

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
        # if rule patterns are defined and the url does not match any pattern return false
        if self.url_patterns and not any(
                [url_pattern for url_pattern in self.url_patterns if re.search(url_pattern, url)]):
            return False
        if ResponseLoader.get_domain(url) not in self.allowed_domains:
            return False
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
