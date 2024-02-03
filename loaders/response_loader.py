import asyncio
import logging
import httpx

from enum import Enum
from typing import Coroutine, Dict, AsyncGenerator, List, Set, Tuple, Iterable
from urllib.parse import urlsplit, urlunsplit, urljoin, urlparse
from playwright.async_api import Page, Request, Locator
from selectolax.parser import HTMLParser
from EVNTDispatch import EventDispatcher, PEvent, EventType

from scraping.proxy_manager import ProxyManager, Proxy
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
    _HREF_VALUES_TO_CLICK = {'#', 'javascript:void(0);', 'javascript:;'}

    def __init__(self, event_dispatcher: EventDispatcher, use_proxies: bool = False, render: bool = False, max_proxies: int = 30, max_retries: int = 3):
        # max responses to load at once
        self.max_responses = 60
        # max pages to render at once
        self.max_renders = 5
        self.use_proxies = use_proxies
        self.max_proxies = max_proxies
        self.render = render
        self.max_retires = max_retries

        # noinspection PyTypeChecker
        self._current_proxy: Proxy = None
        self._event_dispatcher = event_dispatcher
        self._response_semaphore = asyncio.Semaphore(self.max_responses)
        self._render_semaphore = asyncio.Semaphore(self.max_renders)
        self._is_initialized = False
        self._logger = CLogger("ResponseLoader", logging.INFO, {logging.StreamHandler(): logging.INFO})
        self._proxy_manager = ProxyManager()

        # Dict[url: times_retired]
        self._urls_to_retry: Dict[str, int] = {}

    async def setup(self) -> None:
        if self._is_initialized:
            return

        self._is_initialized = True

        if self.use_proxies:
            await self._proxy_manager.load_proxies(self.max_proxies)
            self._current_proxy = self._proxy_manager.get_random_proxy()

    @staticmethod
    def normalize_url(url: str) -> str:
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

    async def wait_for_page_load(self, page: Page, timeout_time: float = 30) -> None:
        try:
            await asyncio.wait_for(
                asyncio.gather(
                    page.wait_for_load_state("load", timeout=timeout_time),
                    page.wait_for_load_state("networkidle", timeout=timeout_time),
                ),
                timeout=timeout_time / 1000  # Convert back to seconds
            )
        except asyncio.TimeoutError as te:
            self._logger.error(
                f"TIME OUT ERROR WHEN WAITING FOR [load state]: {te}\n URL: {page.url}",
            )

    async def get_rendered_response(self, url: str, timeout_time: float = 30) -> ScrapedResponse:
        timeout_time *= 1000

        async with self._render_semaphore:
            page = await BrowserManager.get_page()

            response = await page.goto(url, timeout=timeout_time)
            content_future = asyncio.Future()

            async def request_finished_callback(request: Request) -> None:
                content = await request.frame.content()
                if not content_future.done():
                    content_future.set_result(content)

            page.on("requestfinished", request_finished_callback)

            await self.wait_for_page_load(page, timeout_time)

            html = ""
            try:
                html = await asyncio.wait_for(content_future, timeout=timeout_time / 1000)
            except asyncio.TimeoutError as te:
                self._logger.error(
                    f"TIME OUT ERROR WHEN WAITING FOR [request finished] event: {te}\n (T-O-E) URL: {url}"
                )
            finally:
                page.remove_listener("requestfinished", request_finished_callback)

            hrefs_elements = await self.collect_null_hrefs(page)

            if not html:
                self._logger.warning("Failed to fetch html, falling back to safety fetch")
                html = await page.content()

            status_code = response.status if response else 400
            return ScrapedResponse(html, status_code, href_elements=hrefs_elements, page=page, url=url)

    async def get_response(self, url: str, timeout_time: float = 30) -> ScrapedResponse:
        async with self._response_semaphore:
            if not self.use_proxies:
                async with httpx.AsyncClient(timeout=timeout_time) as client:
                    response = await client.get(url=url)
                    html = response.text
            else:
                formatted_proxy = f'{self._current_proxy.protocol}://{self._current_proxy.ip}:{self._current_proxy.port}'

                if self._current_proxy.protocol == 'http':
                    url = url.replace('https', 'http', 1) if url.startswith('https') else url

                async with httpx.AsyncClient(proxies=formatted_proxy, timeout=timeout_time) as client:
                    response = await client.get(url=url)
                    html = response.text

            return ScrapedResponse(html, response.status_code, url=url)

    async def load_responses(self, urls: Set[str]) -> Dict[str, ScrapedResponse]:

        response_method = self.get_rendered_response if self.render else self.get_response

        # noinspection PyTypeChecker
        tasks = [response_method(url) for url in urls]

        results = {}
        event_data = {}
        async for url, scraped_response in self._generate_responses(tasks, urls):
            self._log_response(scraped_response)

            if scraped_response.status_code != 200:
                continue

            results.update({url: scraped_response})
            event_data.update({url: scraped_response.html})

        async for url, scraped_response in self._retry_urls():
            self._log_response(scraped_response)

            if scraped_response.status_code != 200:
                continue

            results.update({url: scraped_response})
            event_data.update({url: scraped_response.html})

        self._event_dispatcher.sync_trigger(PEvent("new_responses", EventType.Base, data=event_data))

        return results

    async def _retry_urls(self) -> AsyncGenerator[Tuple[str, ScrapedResponse], None]:
        urls = []
        urls_to_remove = []
        while self._urls_to_retry:
            for url in self._urls_to_retry:
                if self._urls_to_retry[url] >= self.max_retires:
                    urls_to_remove.append(url)
                else:
                    urls.append(url)

            response_method = self.get_rendered_response if self.render else self.get_response

            # noinspection PyTypeChecker
            tasks = [response_method(url) for url in urls]

            async for url, response in self._generate_responses(tasks, urls, skip_errors=False):
                if isinstance(response, BaseException) or response.status_code != 200:
                    self._urls_to_retry[url] += 1
                    self._logger.warning(f'retry failed: url {url}, times: {self._urls_to_retry[url]}')
                else:
                    self._logger.info(f'retry successful: url {url}')
                    self._urls_to_retry.pop(url)
                    yield url, response

            for r_url in reversed(urls_to_remove):
                self._urls_to_retry.pop(r_url)

            urls.clear()
            urls_to_remove.clear()

    async def collect_null_hrefs(self, page: Page) -> List[Locator]:
        href_elements_locator = page.locator('a[href]')

        hrefs_to_click = []
        for href_element in await href_elements_locator.all():
            href = await href_element.get_attribute('href')

            if href in self._HREF_VALUES_TO_CLICK:
                hrefs_to_click.append(href_element)

        return hrefs_to_click

    @staticmethod
    def build_link(base_url: str, href: str) -> str:
        if not href:
            return ""

        url = urljoin(base_url, href)
        return ResponseLoader.normalize_url(url)

    @staticmethod
    def get_domain(url: str) -> str:
        return urlparse(url).netloc

    @staticmethod
    def get_hrefs_from_html(html: str) -> List[str]:
        parser = HTMLParser(html)
        for a_tag in parser.css("a"):
            href = a_tag.attributes.get("href")
            if href in ResponseLoader._HREF_VALUES_TO_CLICK:
                continue
            yield href

    async def _generate_responses(self, tasks: List[Coroutine[None, None, ScrapedResponse]], urls: Iterable[str], skip_errors: bool = True) \
            -> AsyncGenerator[Tuple[str, ScrapedResponse], None]:

        responses = await asyncio.gather(*tasks, return_exceptions=True)

        for url, response_info in zip(urls, responses):
            if isinstance(response_info, Exception) or response_info.status_code != 200: # noqa
                self._logger.error(f"Responses Error: {response_info.__class__}")

                self._urls_to_retry.update({url: 0})
                if skip_errors:
                    continue

            yield url, response_info

    def _log_response(self, response: ScrapedResponse) -> None:
        message = f"URL={response.url}, Status={response.status_code}"

        if response.status_code != 200:
            self._logger.warning(f"Bad Response Received: {message}")
        else:
            self._logger.info(f"Good Response Received: {message}")
