import aiohttp
import asyncio
from typing import List, Tuple, Generator

from aiohttp import ClientSession

from utils.logger import Logger, LoggerLevel
from observables.observable_dict import ObservableDict


class ResponsesLoader:
    _hooks = {'response': Logger.console_log}

    def __init__(self, responses_collection_name: str):
        self._responses = ObservableDict(responses_collection_name)
        self._urls = []

    @staticmethod
    async def _apply_hooks(url: str, response: aiohttp.ClientResponse) -> Tuple[str, str]:
        content = await response.text()

        response_hook = ResponsesLoader._hooks.get('response')
        if response_hook:
            response_hook(f"Received response from {url}", LoggerLevel.INFO, include_time=True)

        return url, content

    async def fetch_url(self, session: ClientSession, url: str) -> Tuple[str, str]:
        async with session.get(url) as response:
            self._urls.remove(url)
            return await self._apply_hooks(url, response)

    async def fetch_multiple_urls(self) -> None:
        responses = {}
        async with aiohttp.ClientSession() as session:
            tasks = [self.fetch_url(session, url) for url in self._urls]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, Exception):
                    Logger.console_log(f'{result}', LoggerLevel.WARNING)
                    self._add_error(f"ERROR: {result}")
                else:
                    url, content = result
                    responses.update({url: content})
        self._responses.update(responses)

    def _add_error(self, error: str) -> None:
        if self._responses.get("ERROR") is None:
            self._responses.update({"ERROR": []})

        self._responses.get("ERROR").append(error)

    def collect_responses(self) -> ObservableDict:
        asyncio.run(self.fetch_multiple_urls())
        return self._responses

    def get_responses(self, included_errors: bool = False) -> Generator[Tuple[str, str], None, None]:
        for response in self._responses:
            for url, content in response.items():
                if url.startswith("ERROR") and not included_errors:
                    continue
                yield url, content

    def add_urls(self, urls: List[str]):
        self._urls += urls
