import asyncio
import re

from typing import List, Generator, Any, Union, Dict
from urllib.robotparser import RobotFileParser
from selectolax.parser import HTMLParser

from loaders.response_loader import ResponseLoader, ResponseInformation
from events.event_dispatcher import EventDispatcher


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
        self._to_visit = set()
        self._visited = set()
        self._loop = None
        self._urls_to_retry = set()
        self._running_tasks = set()

        # robot.txt parser
        self._robot_parser = RobotFileParser()
        self._robot_parser.set_url(self._get_robot_txt_url())
        self._robot_parser.read()

        # debug variables
        self._total_link_build_attempts = 0

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
        print("TOTAL ATTEMPTED LINK BUILDS:", self._total_link_build_attempts)
        print("TOTAL ERRORS:", len(self._urls_to_retry))
        print("SITES TO VISIT:", len(self._to_visit))

    def extract_links(self, base_url: str, html: str) -> Generator[str, Any, Any]:
        """
        Extract hrefs from the HTML and try to build URLs from them.

        Args:
            base_url (str): The base URL of the HTML page.
            html (str): The HTML content to extract links from.

        Yields:
            str: The extracted URLs.
        """
        parser = HTMLParser(html)
        for a_tag in parser.css("a"):
            href = a_tag.attributes.get("href")
            self._total_link_build_attempts += 1
            yield ResponseLoader.build_link(base_url, href)

    async def _run(self):
        """
        Internal method to perform the crawling asynchronously.
        """

        new_urls = set()
        while self._to_visit and self._current_depth <= self.max_depth:
            if self.has_crawl_delay:
                # If there's a crawl delay, process URLs one at a time
                # by popping a URL from the _to_visit set
                response_pairs = await ResponseLoader.load_responses(self._to_visit.pop(), render_pages=self.render_pages)
                await asyncio.sleep(self.crawl_delay)
            else:
                # If no crawl delay, process all URLs at once
                response_pairs = await ResponseLoader.load_responses(*self._to_visit, render_pages=self.render_pages)
                self._to_visit.clear()

            for url in self._process_responses(response_pairs):
                if url not in self._visited and self._is_url_allowed(url):
                    self._visited.add(url)
                    new_urls.add(url)

            if not self._to_visit:
                # Once we have processed all the URLs in _to_visit, copy over all the new URLs and increase the depth
                self._to_visit.update(new_urls)
                self._current_depth += 1
                new_urls.clear()

    def _process_responses(self, responses: Dict[str, Union[ResponseInformation, BaseException]]) -> Generator[str, Any, Any]:
        """
        Process the responses and yield extracted URLs.

        Args:
            responses (Dict[str, Union[ResponseInformation, BaseException]]): A dictionary of URLs mapped to responses or exceptions.

        Yields:
            str: Extracted URLs.
        """
        for url, response_info in responses.items():
            if isinstance(response_info, Exception):
                print("ERROR:", response_info)
                self._urls_to_retry.add(url)
                continue
            self._visited.add(url)
            print(f"status_code={response_info.status_code}, url={url}, depth={self._current_depth}")

            for new_url in self.extract_links(url, response_info.html):
                yield new_url

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
        if self.url_patterns and not any([url_pattern for url_pattern in self.url_patterns if re.search(url_pattern, url)]):
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
