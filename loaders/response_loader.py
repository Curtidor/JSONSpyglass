import aiohttp
import asyncio
from typing import List, Tuple, Generator

from aiohttp import ClientSession

from utils.logger import Logger, LoggerLevel
from observables.observable_collection import ObservableCollection


class ResponsesLoader:
    _hooks = {'response': Logger.console_log}
    _responses = ObservableCollection("responses")
    _urls = []

    @staticmethod
    async def _apply_hooks(url: str, response: aiohttp.ClientResponse) -> Tuple[str, str]:
        content = await response.text()

        response_hook = ResponsesLoader._hooks.get('response')
        if response_hook:
            response_hook(f"Received response from {url}", LoggerLevel.INFO, include_time=True)

        return url, content

    @staticmethod
    async def fetch_url(session: ClientSession, url: str) -> Tuple[str, str]:
        async with session.get(url) as response:
            ResponsesLoader._urls.remove(url)
            return await ResponsesLoader._apply_hooks(url, response)

    @staticmethod
    async def fetch_multiple_urls() -> None:
        async with aiohttp.ClientSession() as session:
            tasks = [ResponsesLoader.fetch_url(session, url) for url in ResponsesLoader._urls]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, Exception):
                    Logger.console_log(f'{result}', LoggerLevel.WARNING)
                    ResponsesLoader._add_error(f"ERROR: {result}")
                else:
                    url, content = result
                    ResponsesLoader._responses.append({url: content})

    @staticmethod
    def _add_error(error: str) -> None:
        if ResponsesLoader._responses[0].get("ERROR") is None:
            ResponsesLoader._responses.insert(0, {"ERROR": []})

        ResponsesLoader._responses[0]["ERROR"].append(error)

    @staticmethod
    def collect_responses() -> ObservableCollection:
        asyncio.run(ResponsesLoader.fetch_multiple_urls())
        return ResponsesLoader._responses

    @staticmethod
    def get_responses(included_errors: bool = False) -> Generator[Tuple[str, str], None, None]:
        for response in ResponsesLoader._responses:
            for url, content in response.items():
                if url.startswith("ERROR") and not included_errors:
                    continue
                yield url, content

    @staticmethod
    def add_urls(urls: List[str]):
        ResponsesLoader._urls += urls
