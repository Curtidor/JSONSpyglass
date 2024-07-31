import asyncio
import functools
import logging
import traceback

import httpx

from typing import Coroutine, Dict, AsyncGenerator, List, Set, Tuple, Iterable, Any, Callable, Union
from urllib.parse import urlsplit, urlunsplit, urljoin, urlparse

from selectolax.parser import HTMLParser
from playwright.async_api import Page, Locator
from EVNTDispatch import EventDispatcher, PEvent, EventType

from scraping.proxy_manager import ProxyManager, Proxy
from scraping.page_manager import BrowserManager
from utils.clogger import CLogger
from models.requires import Requires
from .response_loader_models import ResponseLoaderSettings, ScrapedResponse


class ResponseLoader:
    """
    A utility class for loading and processing web responses.
    """
    _HREF_VALUES_TO_CLICK = {'#', 'javascript:void(0);', 'javascript:;'}

    def __init__(
            self,
            event_dispatcher: EventDispatcher,
            requirements: Union[Requires, None],
            max_responses: int = 60,
            max_renders: int = 5,
            use_proxies: bool = False,
            render: bool = False,
            max_proxies: int = 30,
            max_retries: int = 3
    ):

        self.settings = ResponseLoaderSettings(
            max_responses, max_renders, use_proxies, max_proxies, render, max_retries
        )

        # noinspection PyTypeChecker
        self._current_proxy: Proxy = None
        self._proxy_manager = ProxyManager()

        self._event_dispatcher = event_dispatcher
        self._requirements = requirements if requirements is not None else Requires()

        self._response_semaphore = asyncio.Semaphore(self.settings.max_responses)
        self._render_semaphore = asyncio.Semaphore(self.settings.max_renders)

        self._is_initialized = False

        self._logger = CLogger("ResponseLoader", logging.INFO, {logging.StreamHandler(): logging.INFO})

        # Dict[url: times_retired]
        self._urls_to_retry: Dict[str, int] = {}

    async def setup(self) -> None:
        if self._is_initialized:
            return

        self._is_initialized = True

        if self.settings.use_proxies:
            await self._proxy_manager.load_proxies(self.settings.max_proxies)
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

    @staticmethod
    def get_hrefs_from_html(html: str) -> List[str]:
        parser = HTMLParser(html)

        for a_tag in parser.css("a"):
            href = a_tag.attributes.get("href")

            if href in ResponseLoader._HREF_VALUES_TO_CLICK:
                continue

            yield href

    @staticmethod
    def get_domain(url: str) -> str:
        if not url:
            return ''
        return urlparse(url).netloc

    @classmethod
    def build_link(cls, base_url: str, href: str) -> str:
        if not href:
            return ""

        url = urljoin(base_url, href)
        return cls.normalize_url(url)

    async def load_responses(self, urls: Set[str]) -> Dict[str, ScrapedResponse]:

        response_method = self._get_response_method()

        default_timeout: float = 30
        tasks = [response_method(url, default_timeout) for url in urls]

        results = {}
        event_data = {}

        async def _generate_combined_responses():
            async for url, response in self._generate_responses(tasks, urls, return_exceptions=True):
                yield url, response

            async for url, response in self._retry_failed_urls():
                yield url, response

        async for url, scraped_response in _generate_combined_responses():
            if not isinstance(scraped_response, BaseException):
                self._log_response(scraped_response)
            else:
                self._logger.warning(f'failed to get a response from: {url} reason => {scraped_response} ')
                continue

            if scraped_response.status_code != 200:
                continue

            results.update({url: scraped_response})
            event_data.update({url: scraped_response.html})

        self._event_dispatcher.sync_trigger(PEvent("new_responses", EventType.Base, data=event_data))

        return results

    async def get_rendered_response(self, url: str, timeout_time: float = 30) -> ScrapedResponse:
        async with self._render_semaphore:
            page = await BrowserManager.get_page()
            response = await page.goto(url, timeout=timeout_time * 1000)

            page_loading_tasks = [
                self._wait_for_page_states(page, timeout_time),
                self._wait_for_page_events(page, timeout_time)
            ]

            html = ""
            try:
                await asyncio.wait_for(
                    asyncio.gather(*page_loading_tasks),
                    timeout=timeout_time
                )

                html = await page.content()
            except asyncio.TimeoutError as te:
                self._logger.error(
                    f"Timed out when waiting for `page_loading_task` {te}\n URL: {url}"
                )

            if not html:
                self._logger.warning("Failed to fetch html, falling back to safety fetch")
                html = await page.content()

            hrefs_elements = await self._collect_clickable_null_hrefs(page)

            status_code = response.status if response else 400
            return ScrapedResponse(html, status_code, href_elements=hrefs_elements, page=page, url=url)

    async def get_response(self, url: str, timeout_time: float = 30) -> ScrapedResponse:
        async with self._response_semaphore:
            proxy = None

            if self.settings.use_proxies and self._current_proxy:
                proxy = self._current_proxy.formate_proxy()

                if self._current_proxy.protocol == 'http':
                    url = url.replace('https', 'http', 1) if url.startswith('https') else url

            async with httpx.AsyncClient(proxies=proxy, timeout=timeout_time) as client:
                response = await client.get(url=url)
                html = response.text

            return ScrapedResponse(html, response.status_code, url=url, href_elements=[], page=None)

    async def _wait_for_page_states(self, page: Page, timeout: float = 30) -> None:
        """
        Waits for specified page states within a given timeout period.

        Args:
            page (Page): The page object to wait on.
            timeout (float): The maximum time to wait for all states, in seconds.

        Raises:
            asyncio.TimeoutError: If the timeout is exceeded while waiting for states.
        """
        # keep track of states, so we can log them if there's an error
        loaded_states = set()

        try:
            if not self._requirements:
                self._logger.info("No requirements to wait for.")
                return

            tasks = []
            for state in self._requirements.states:
                tasks.append(page.wait_for_load_state(state, timeout=timeout * 1000))  # convert the timeout to secs
                loaded_states.add(state)

            await asyncio.wait_for(asyncio.gather(*tasks), timeout=timeout)

        except asyncio.TimeoutError as te:
            self._logger.error(
                f"Timeout error when waiting for load states:{loaded_states}:{te}\nURL: {page.url}"
            )

    async def _wait_for_page_events(self, page: Any, timeout: float = 30) -> None:
        """
        Waits for specified events on a page until all are completed or the timeout is reached.

        Args:
            page (Any): The page object on which events will be monitored.
            timeout (float): The maximum time to wait for all events to complete in seconds. Default is 30 seconds.

        Raises:
            asyncio.TimeoutError: If the timeout is reached before all events are completed.
        """
        # keep track of events being waited for to log them in case of an error
        monitored_events = set()

        try:
            if not self._requirements or not self._requirements.events:
                self._logger.info("No requirements to wait for.")
                return

            def set_event_flag(event_flag: asyncio.Event, _event_arg: Any = None) -> None:
                event_flag.set()

            # prepare tasks for each required event
            tasks = set()
            for event in self._requirements.events:
                event_flag_l = asyncio.Event()
                monitored_events.add(event)

                task = asyncio.create_task(event_flag_l.wait())
                tasks.add(task)

                callback = functools.partial(set_event_flag, event_flag_l)
                page.on(event, callback)

            await asyncio.wait_for(asyncio.gather(*tasks), timeout=timeout)

        except asyncio.TimeoutError as timeout_error:
            self._logger.error(
                f"Timeout error when waiting for load events: {monitored_events}: {timeout_error}\nURL: {page.url}"
            )

    async def _retry_failed_urls(self) -> AsyncGenerator[Tuple[str, ScrapedResponse], None]:
        """
        Retry loading responses for URLs that previously failed until they succeed or reach the maximum retry limit.

        Yields:
            Tuple[str, ScrapedResponse]: A tuple containing the URL and the corresponding scraped response.
        """
        response_method = self._get_response_method()
        default_timeout: float = 30

        while self._urls_to_retry:
            urls_to_retry = list(self._urls_to_retry.keys())
            urls_to_remove = []
            tasks = []

            for url in urls_to_retry:
                if self._urls_to_retry[url] >= self.settings.max_retires:
                    urls_to_remove.append(url)
                else:
                    tasks.append(response_method(url, default_timeout))

            async for url, response in self._generate_responses(tasks, urls_to_retry, return_exceptions=True):
                if isinstance(response, BaseException) or response.status_code != 200:
                    self._urls_to_retry[url] += 1
                    self._logger.warning(f'Retry failed: URL {url}, attempt {self._urls_to_retry[url]}')
                else:
                    self._logger.info(f'Retry successful: URL {url}')
                    self._urls_to_retry.pop(url)
                    yield url, response

            for url_to_remove in urls_to_remove:
                self._urls_to_retry.pop(url_to_remove)

            urls_to_remove.clear()
            tasks.clear()

    async def _generate_responses(
            self,
            tasks: List[Coroutine[None, None, ScrapedResponse]],
            urls: Iterable[str],
            return_exceptions: bool = True
    ) -> AsyncGenerator[Tuple[str, ScrapedResponse], None]:
        """
        Execute the provided tasks and yield the responses, handling errors and retry logic.

        Args:
            tasks (List[Coroutine[None, None, ScrapedResponse]]): The tasks to be executed.
            urls (Iterable[str]): The URLs corresponding to the tasks.
            return_exceptions (bool): Whether to skip URLs that resulted in errors. Defaults to True.

        Yields:
            Tuple[str, ScrapedResponse]: The URL and the corresponding response.

        Logs errors and increments retry counts for failed tasks.
        """
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        for url, response in zip(urls, responses):
            if isinstance(response, Exception) or response.status_code != 200:
                self._logger.error(f"Response Error: {repr(response)}")

                # increment retry count for the URL
                self._urls_to_retry[url] = self._urls_to_retry.get(url, -1) + 1
                if not return_exceptions:
                    continue

                traceback.print_stack()

            yield url, response

    async def _collect_clickable_null_hrefs(self, page: Page) -> List[Locator]:
        """
           Collects and returns a list of hyperlink elements with href values that are considered
           non-navigable or empty, such as `#`, `javascript:void(0);`, and `javascript:;`.

           Args:
               page (Page): The Playwright Page object from which to collect href elements.

           Returns:
               List[Locator]: A list of Locator objects representing the hyperlink elements with
               non-navigable href values.
           """
        href_elements_locator = page.locator('a[href]')

        hrefs_to_click = []
        for href_element in await href_elements_locator.all():
            href = await href_element.get_attribute('href')

            if href in self._HREF_VALUES_TO_CLICK:
                hrefs_to_click.append(href_element)

        return hrefs_to_click

    def _get_response_method(self) -> Callable[[str, float], Coroutine[Any, Any, ScrapedResponse]]:
        return self.get_rendered_response if self.settings.render_pages else self.get_response

    def _log_response(self, response: ScrapedResponse) -> None:
        message = f"URL={response.url}, Status={response.status_code}"

        if response.status_code != 200:
            self._logger.warning(f"Bad Response Received: {message}")
        else:
            self._logger.info(f"Good Response Received: {message}")
