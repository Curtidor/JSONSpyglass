import asyncio
import re

from typing import List, Tuple
from requests_html import AsyncHTMLSession, HTMLResponse

from events.event_dispatcher import EventDispatcher, Event
from loaders.config_loader import ConfigLoader
from utils.logger import Logger, LoggerLevel


# TODO:
#  add rotating proxy servers and rotating user agents
#  fix this error when rendering: sys:1: RuntimeWarning: coroutine 'Launcher.killChrome' was never awaited


class ResponsesLoader:
    _hooks = {'response': Logger.console_log}
    _user_agent = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
                                 "AppleWebKit/537.36 (KHTML, like Gecko)"
                                 "Chrome/115.0.0.0 Safari/537.36"}

    def __init__(self, config: ConfigLoader, event_dispatcher: EventDispatcher):
        self.event_dispatcher = event_dispatcher
        self.event_dispatcher.add_listener("new_urls", self.add_urls)
        self.responses = []

        self._errors: List[str] = []
        self._urls = config.get_target_urls()
        self._domains_to_render = config.get_render_domains()

        self._max_renders = 4
        self._render_semaphore = asyncio.Semaphore(self._max_renders)

    async def fetch_url(self, url: str, session: AsyncHTMLSession) -> tuple[str, bytes]:
        async with self._render_semaphore:
            response: HTMLResponse = await session.get(url, headers=ResponsesLoader._user_agent)

            if response.status_code == 200:
                Logger.console_log(f"Received response from: {url}", LoggerLevel.INFO, include_time=True)
            else:
                Logger.console_log(f"Bad response from: {url}, status code: [{response.status_code}]", LoggerLevel.ERROR, include_time=True)

            if self._get_domain(url) in self._domains_to_render:
                Logger.console_log(f"Rendering page: {url}", LoggerLevel.INFO, include_time=True)
                await response.html.arender(timeout=10)

            return url, response.content

    async def fetch_multiple_urls(self) -> None:
        responses = []
        session = AsyncHTMLSession()

        tasks = [self.fetch_url(url, session) for url in self._urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        await session.close()

        for result in results:
            if isinstance(result, Exception):
                # results in this case will be the error information
                Logger.console_log(f'Response error: {result}', LoggerLevel.WARNING)
                self._add_error(f"ERROR: {result}")
            else:
                url, content = result
                responses.append({url: content})

        self._urls.clear()
        self.responses = responses

    async def collect_responses(self):
        await self.fetch_multiple_urls()
        await self.event_dispatcher.async_trigger(Event("new_responses", "loaded_responses_type", data=self.responses))

    async def add_urls(self, event):
        self._urls += event.data
        await self.collect_responses()

    def show_errors(self) -> None:
        for error in self._errors:
            print(error)

    def _add_error(self, error: str) -> None:
        self._errors.append(error)

    @staticmethod
    def _get_domain(url: str) -> str:
        return re.search(r'(?:https?://)?(?:www\.)?([^/]+)', url).group(1)
