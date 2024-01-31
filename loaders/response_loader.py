import aiohttp
import asyncio
import logging

from enum import Enum
from typing import Coroutine, Dict, AsyncGenerator, List, Set, Tuple, Generator, Any
from aiohttp import ClientTimeout
from urllib.parse import urlsplit, urlunsplit, urljoin, urlparse
from playwright.async_api import Page, Request, Locator
from selectolax.parser import HTMLParser
from EVNTDispatch import EventDispatcher, PEvent, EventType

from scraping.page_manager import BrowserManager
from utils.clogger import CLogger


class ScrapedResponse:
    def __init__(self, html: str, status_code: int, url: str, href_elements: List[Locator] = None,
                 page: Page = None):
        self.html: str = html
        self.status_code: int = status_code
        self.url: str = url
        self.href_elements: List[Locator] = href_elements
        self.page: Page = page

    def __eq__(self, other):
        if isinstance(other, ScrapedResponse):
            return (
                    self.html == other.html and
                    self.status_code == other.status_code and
                    self.url == other.url and
                    self.href_elements == other.href_elements
            )
        return False

    def __hash__(self):
        return hash((self.html, self.status_code, self.url))


# this if for a future feature where we can try to get different states of a page event
# when previous ones failed
class RenderStateRetry(Enum):
    INITIAL = 0,
    LOAD_STATE_TIMEOUT = 1,
    REQUEST_FINISHED_EVENT_TIMEOUT = 2


class ResponseLoader:
    """
    A utility class for loading and processing web responses.
    """
    _BAD_RESPONSE_CODE = -1

    _max_responses = 60
    _max_renders = 5
    _event_dispatcher: EventDispatcher = None

    _response_semaphore = asyncio.Semaphore(_max_responses)
    _render_semaphore = asyncio.Semaphore(_max_renders)

    _hrefs_values_to_click = {'#', 'javascript:void(0);', 'javascript:;'}

    _is_initialized: bool = False

    _logger = CLogger("ResponseLoader", logging.INFO, {logging.StreamHandler(): logging.INFO})

    @classmethod
    def setup(cls, event_dispatcher: EventDispatcher) -> None:
        cls._event_dispatcher = event_dispatcher

    @staticmethod
    def normalize_url(url: str) -> str:
        """
        Normalize a URL.

        Args:
            url (str): The URL to be normalized.

        Returns:
            str: The normalized URL.
        """
        components = urlsplit(url)
        normalized_components = [
            components.scheme.lower(),
            components.netloc.lower(),
            components.path,
            components.query,
            components.fragment
        ]
        normalized_url = urlunsplit(normalized_components)
        return normalized_url

    @classmethod
    async def wait_for_page_load(cls, page: Page, timeout_time: float = 30) -> None:
        try:
            await asyncio.wait_for(
                asyncio.gather(
                    # ERROR: the load event is creating time out errors
                    page.wait_for_load_state("load", timeout=timeout_time),
                    page.wait_for_load_state("networkidle", timeout=timeout_time),
                ),
                timeout=timeout_time / 1000  # Convert back to seconds
            )
        except asyncio.TimeoutError as te:
            cls._logger.error(
                f"TIME OUT ERROR WHEN WAITING FOR [load state]: {te}\n URL: {page.url}",
            )

    @classmethod
    async def get_rendered_response(cls, url: str, timeout_time: float = 30) -> ScrapedResponse:
        """
        Get the rendered HTML response content of a web page.

        Args:
          url (str): The URL of the web page.
          timeout_time (float): Maximum operation time in seconds (default is 30 seconds).

        Returns:
          ScrapedResponse: A response object containing the rendered HTML content and additional information.

        Note:
          If href elements are returned, the page is not closed, and the caller is responsible for managing
          the page's lifetime.
        """
        timeout_time *= 1000

        async with cls._render_semaphore:
            page = await BrowserManager.get_page()

            response = await page.goto(url, timeout=timeout_time)
            content_future = asyncio.Future()

            async def request_finished_callback(request: Request) -> None:
                content = await request.frame.content()
                if not content_future.done():
                    content_future.set_result(content)

            page.on("requestfinished", request_finished_callback)

            await cls.wait_for_page_load(page, timeout_time)

            html = ""
            try:
                # Wait for the content_future with a timeout
                html = await asyncio.wait_for(content_future, timeout=timeout_time / 1000)
            except asyncio.TimeoutError as te:
                cls._logger.error(
                    f"TIME OUT ERROR WHEN WAITING FOR [request finished] event: {te}\n (T-O-E) URL: {url}"
                )
            finally:
                page.remove_listener("requestfinished", request_finished_callback)

            hrefs_elements = await cls.collect_hrefs_with_elements(page)

            # fallback when we couldn't render the page and extract the html
            if not html:
                cls._logger.warning("Failed to fetch html, falling back to safety fetch")
                html = await page.content()

            status_code = response.status if response else cls._BAD_RESPONSE_CODE
            return ScrapedResponse(html, status_code, href_elements=hrefs_elements, page=page, url=url)

    @classmethod
    async def get_response(cls, url: str, timeout_time: float = 30) -> ScrapedResponse:
        """
        Get the text response content of a web page.

        Args:
            url (str): The URL of the web page.
            timeout_time (float) Maximum operation time in seconds, defaults to 30 seconds

        Returns:
            str: The text response content.
        """
        async with cls._response_semaphore:
            timeout = ClientTimeout(total=timeout_time)

            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    html = await response.text()
                    return ScrapedResponse(html, response.status, url=url)

    @classmethod
    async def load_responses(cls, urls: Set[str], render_pages: bool = False) -> Dict[str, ScrapedResponse]:
        """
        Load and retrieve responses from the specified URLs.

        Args:
            *urls: Variable-length arguments representing the URLs to load responses from.
            render_pages (bool): Whether to render pages with JavaScript (default is False).

        Returns:
            Dict[str, ScrapedResponse]: A dictionary containing the loaded responses indexed by URL.

        Note:
            This method loads responses from the provided URLs. If rendering pages is enabled, it will render pages
            with JavaScript. The method triggers a "new_responses" event with the loaded response data.
        """

        # the response method to use based on if we are rending the page or not
        response_method = cls.get_rendered_response if render_pages \
            else cls.get_response

        # noinspection PyTypeChecker
        # The error indicates that the URL is considered of the wrong type for the response_method parameter,
        # but this is not accurate. The URL is of type string, which has been confirmed through testing.
        # This type error is likely a bug, and for now, it can be safely ignored.
        tasks = [response_method(url) for url in urls]

        results = {}
        event_data = {}
        async for result in cls._generate_responses(tasks, urls):
            url, scraped_response = result

            cls._log_response(scraped_response)

            if scraped_response.status_code == cls._BAD_RESPONSE_CODE:
                continue

            results.update({url: scraped_response})
            event_data.update({url: scraped_response.html})

        cls._event_dispatcher.sync_trigger(PEvent("new_responses", EventType.Base, data=event_data))

        return results

    @classmethod
    def build_link(cls, base_url: str, href: str) -> str:
        """
        Build a full URL from a base URL and a relative href.

        Args:
            base_url (str): The base URL.
            href (str): The relative href.

        Returns:
            str: The full URL.
        """
        if not href:
            return ""

        url = urljoin(base_url, href)
        return cls.normalize_url(url)

    @staticmethod
    def get_domain(url: str) -> str:
        return urlparse(url).netloc

    @classmethod
    async def collect_hrefs_with_elements(cls, page: Page) -> List[Locator]:
        """
        Collects and returns a list of Locator elements representing anchor tags (href) with specific values on a web page.

        Args:
            page (Page): The Playwright Page object to search for anchor tags.

        Returns:
            List[Locator]: A list of Locator elements representing anchor tags with specific href attribute values.

        """
        href_elements_locator = page.locator('a[href]')

        hrefs_to_click = []
        for href_element in await href_elements_locator.all():
            href = await href_element.get_attribute('href')

            if href in cls._hrefs_values_to_click:
                hrefs_to_click.append(href_element)

        return hrefs_to_click

    @classmethod
    def get_hrefs_from_html(cls, html: str) -> Generator[str, Any, Any]:
        parser = HTMLParser(html)
        for a_tag in parser.css("a"):
            href = a_tag.attributes.get("href")
            if href in cls._hrefs_values_to_click:
                continue
            yield href

    @classmethod
    async def _generate_responses(cls, tasks: List[Coroutine[None, None, ScrapedResponse]], urls: Set[str]) -> \
            AsyncGenerator[Tuple[str, ScrapedResponse], None]:
        """
        Generate responses form a list of tasks and URLs.

        Args:
            tasks (List[Coroutine[Any, Any, str]]): List of tasks to generate responses.
            urls (List[str]): List of URLs corresponding to the tasks.

        Yields:
            Generator[Any, Any, Dict[str, str]]: A generator yielding dictionaries mapping URLs to their response content.
        """
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        for url, response_info in zip(urls, responses):
            if isinstance(response_info, Exception):
                cls._logger.error(f"Responses Error: {response_info}")
                continue
            yield url, response_info

    @classmethod
    def _log_response(cls, response: ScrapedResponse) -> None:
        message = f"URL={response.url}, Status={response.status_code}"

        if response.status_code == cls._BAD_RESPONSE_CODE:
            cls._logger.warning(f"Bad Response Received: {message}")
        else:
            cls._logger.info(f"Good Response Received: {message}")
