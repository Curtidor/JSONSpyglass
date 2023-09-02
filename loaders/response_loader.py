import aiohttp
import asyncio

from dataclasses import dataclass
from typing import Coroutine, Dict, AsyncGenerator, List, Set, Tuple, Generator, Any
from aiohttp import ClientTimeout
from urllib.parse import urlsplit, urlunsplit, urljoin, urlparse
from playwright.async_api import ElementHandle, Page, Request
from selectolax.parser import HTMLParser

from events.event_dispatcher import EventDispatcher, Event
from scraping.page_manager import BrowserManager
from utils.logger import LoggerLevel, Logger


@dataclass
class ScrapedResponse:
    html: str
    status_code: int
    url: str
    href_elements: List[ElementHandle] = None
    page: Page = None


class ResponseLoader:
    """
    A utility class for loading and processing web responses.
    """

    _max_responses = 60
    _max_renders = 5
    _event_dispatcher: EventDispatcher = None

    _response_semaphore = asyncio.Semaphore(_max_responses)
    _render_semaphore = asyncio.Semaphore(_max_renders)

    _hrefs_values_to_click = ('#', 'javascript:void(0);', 'javascript:;')

    _is_initialized: bool = False

    @staticmethod
    async def setup(event_dispatcher: EventDispatcher, is_rendering: bool = False) -> None:
        await BrowserManager.initialize(is_rendering)
        ResponseLoader._event_dispatcher = event_dispatcher

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
    async def get_rendered_response(cls, url: str, timeout_time: float = 30) -> ScrapedResponse:
        """
        Get the rendered HTML response content of a web page.

        Args:
            url (str): The URL of the web page.
            timeout_time (float) Maximum operation time in seconds, defaults to 30 seconds

        Returns:
            str: The rendered HTML content.

        Note:
            If href elements are returned the page is not closed and the caller will be responsible for managing
            the pages lifetime
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

            try:
                await asyncio.wait_for(
                    asyncio.gather(
                        page.wait_for_load_state("load", timeout=timeout_time),
                        page.wait_for_load_state("networkidle", timeout=timeout_time),
                    ),
                    timeout=timeout_time / 1000  # Convert back to seconds
                )
            except asyncio.TimeoutError as te:
                print("TIME OUT ERROR WHEN WAITING FOR LOAD STATES:", te)

            try:
                # Wait for the content_future with a timeout
                html = await asyncio.wait_for(content_future, timeout=timeout_time / 1000)
            except asyncio.TimeoutError as te:
                print("TIME OUT ERROR WHEN WAITING FOR [request finished] event:", te)
            finally:
                page.remove_listener("requestfinished", request_finished_callback)

            hrefs_elements = await cls.collect_hrefs_with_elements(page)

            if not hrefs_elements:
                await BrowserManager.close_page(page, feed_into_pool=True)

            return ScrapedResponse(html, response.status, href_elements=hrefs_elements, page=page, url=url)

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
                    Logger.console_log(f"Responses Received: URL={url}, Status={response.status}", LoggerLevel.INFO)

                    return ScrapedResponse(html, response.status, url=url)

    @classmethod
    async def load_responses(cls, *urls, render_pages: bool = False) -> Dict[str, ScrapedResponse]:
        urls = set(urls)

        response_method = cls.get_rendered_response if render_pages \
            else cls.get_response

        html_responses = []
        tasks = [response_method(url) for url in urls]

        results = {}
        async for result in cls._generate_responses(tasks, urls):
            url, scraped_response = result
            Logger.console_log(
                f"Responses Received: URL={url}, Status={scraped_response.status_code}",
                LoggerLevel.INFO, include_time=True
            )
            html_responses.append({url: scraped_response.html})
            results.update({url: scraped_response})

        ResponseLoader._event_dispatcher.trigger(Event("new_responses", "NEW_DATA", data=html_responses))
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
    async def collect_hrefs_with_elements(cls, page: Page) -> List[ElementHandle]:
        href_elements = await page.query_selector_all('a[href]')

        hrefs_to_click = []
        for href_element in href_elements:
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

    @staticmethod
    async def _generate_responses(tasks: List[Coroutine[None, None, ScrapedResponse]], urls: Set[str]) -> \
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
                Logger.console_log(f"Responses Error: {response_info}", LoggerLevel.ERROR)
                continue
            yield url, response_info
