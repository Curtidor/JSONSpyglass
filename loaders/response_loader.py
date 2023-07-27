import aiohttp
import asyncio
from typing import List, Tuple, Any, Generator

# todo
# add support for dynamic websites


class ResponsesLoader:
    def __init__(self, urls: List[str]):
        self._urls = urls
        self._responses = {}

    @staticmethod
    async def fetch_url(session, url) -> tuple[Any, Any]:
        async with session.get(url) as response:
            return url, await response.text()

    async def fetch_multiple_urls(self) -> None:
        async with aiohttp.ClientSession() as session:
            tasks = [self.fetch_url(session, url) for url in self._urls]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, Exception):
                    print(f"ERROR: {result}")
                    self._add_error(f"ERROR: {result}")
                else:
                    url, content = result
                    self._responses[url] = content

    def _add_error(self, error: str) -> None:
        if self._responses.get("ERROR") is None:
            self._responses.update({"ERROR": []})

        self._responses["ERROR"].append(error)

    def collect_responses(self) -> dict:
        self._responses.clear()

        asyncio.run(self.fetch_multiple_urls())
        return self._responses

    def get_responses(self, included_errors: bool = False) -> Generator[Tuple[str, str], None, None]:
        for url, content in self._responses.items():
            if url.startswith("ERROR") and not included_errors:
                continue
            yield url, content
