import re
import aiohttp
import asyncio

from dataclasses import dataclass
from typing import Coroutine, Dict, AsyncGenerator, List, Set, Tuple

import playwright.async_api
from aiohttp import ClientTimeout
from urllib.parse import urlsplit, urlunsplit, urljoin
from playwright.async_api import async_playwright, Browser

from events.event_dispatcher import EventDispatcher, Event
from utils.logger import LoggerLevel, Logger


@dataclass
class ResponseInformation:
    html: str
    status_code: int


class ResponseLoader:
    """
    A utility class for loading and processing web responses.
    """

    _max_responses = 60
    _max_renders = 5
    _event_dispatcher: EventDispatcher = None

    _response_lock = asyncio.Semaphore(_max_responses)
    _render_lock = asyncio.Semaphore(_max_renders)

    _browser: Browser = None

    @staticmethod
    def setup(event_dispatcher: EventDispatcher) -> None:
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
    async def get_rendered_response(cls, url: str, timeout_time: float = 30) -> ResponseInformation:
        """
        Get the rendered HTML response content of a web page.

        Args:
            url (str): The URL of the web page.
            timeout_time (float) Maximum operation time in seconds, defaults to 30 seconds

        Returns:
            str: The rendered HTML content.
        """
        browser = await cls._get_browser()
        timeout_time *= 1000

        async with cls._render_lock:
            page = await browser.new_page()
            response = await page.goto(url, timeout=timeout_time)
            html = await response.text()
            await page.close()
            Logger.console_log(f"Responses Received: URL={url}, Status={response.status}", LoggerLevel.INFO,
                               include_time=True)
            return ResponseInformation(html, response.status)

    @classmethod
    async def get_response(cls, url: str, timeout_time: float = 30) -> ResponseInformation:
        """
        Get the text response content of a web page.

        Args:
            url (str): The URL of the web page.
            timeout_time (float) Maximum operation time in seconds, defaults to 30 seconds

        Returns:
            str: The text response content.
        """
        async with cls._response_lock:
            timeout = ClientTimeout(total=timeout_time)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    html = await response.text()
                    Logger.console_log(f"Responses Received: URL={url}, Status={response.status}", LoggerLevel.INFO,
                                       include_time=True)
                    return ResponseInformation(html, response.status)

    @staticmethod
    async def load_responses(*urls, render_pages: bool = False) -> Dict[str, ResponseInformation]:
        urls = set(urls)

        response_method = ResponseLoader.get_rendered_response if render_pages \
            else ResponseLoader.get_response

        html_responses = []
        results = {}
        tasks = [response_method(url) for url in urls]
        async for result in ResponseLoader._generate_responses(tasks, urls):
            url, html = result
            html_responses.append({url: html.html})
            results.update({url: html})

        ResponseLoader._event_dispatcher.trigger(Event("new_responses", "NEW_DATA", data=html_responses))
        return results

    @staticmethod
    def build_link(base_url: str, href: str) -> str:
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

        return ResponseLoader.normalize_url(urljoin(base_url, href))

    @staticmethod
    def get_domain(url: str) -> str:
        # if a bad url is give and no match if found an error is thrown
        match = re.search(r'https?://([^/]+)', url)
        return match.group(0)

    @staticmethod
    async def _generate_responses(tasks: List[Coroutine[None, None, ResponseInformation]], urls: Set[str]) -> \
            AsyncGenerator[Tuple[str, ResponseInformation], None]:
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

    @classmethod
    async def _get_browser(cls):
        if cls._browser is None:
            p = await async_playwright().start()
            cls._browser = await p.chromium.launch()
        return cls._browser

    @staticmethod
    async def close():
        if ResponseLoader._browser:
            await ResponseLoader._browser.close()
