import asyncio

from typing import List, Tuple
from httpx_html import AsyncHTMLSession
from requests import Response

from events.event_dispatcher import EventDispatcher, Event
from loaders.config_loader import ConfigLoader
from utils.logger import Logger, LoggerLevel

# TODO: add rotating proxy servers and rotating user agents

class ResponsesLoader:
    _hooks = {'response': Logger.console_log}
    _user_agent = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    }

    def __init__(self, config: ConfigLoader, event_dispatcher: EventDispatcher):
        self._errors: List[str] = []
        self._urls = config.get_target_urls()
        self.event_dispatcher = event_dispatcher
        self.event_dispatcher.add_listener("new_urls", self.add_urls)
        self.responses = []

    async def fetch_url(self, session: AsyncHTMLSession(), url: str) -> Tuple[str, str]:
        response = await session.get(url, headers=ResponsesLoader._user_agent)
        return self._apply_hooks(url, response)

    async def fetch_multiple_urls(self) -> None:
        await asyncio.sleep(0.1)
        responses = []
        session = AsyncHTMLSession()
        tasks = [self.fetch_url(session, url) for url in self._urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                Logger.console_log(f'{result}', LoggerLevel.WARNING)
                self._add_error(f"ERROR: {result}")
            else:
                url, content = result
                responses.append({url: content})

        self._urls.clear()
        self.responses = responses

    def collect_responses(self) -> None:
        asyncio.run(self.fetch_multiple_urls())
        self.event_dispatcher.trigger(Event("new_responses", "loaded_responses", data=self.responses))

    def add_urls(self, event):
        self._urls += event.data
        asyncio.run(self.fetch_multiple_urls())
        self.event_dispatcher.trigger(Event("new_responses", "loaded_responses", data=self.responses))

    def show_errors(self) -> None:
        for error in self._errors:
            print(error)

    @staticmethod
    def _apply_hooks(url: str, response: Response) -> Tuple[str, str]:
        response_hook = ResponsesLoader._hooks.get('response')
        if response_hook:
            response_hook(f"Received response from {url}", LoggerLevel.INFO, include_time=True)
        return url, response.text

    def _add_error(self, error: str) -> None:
        self._errors.append(error)
