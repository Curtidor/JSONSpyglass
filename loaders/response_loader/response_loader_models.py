from enum import Enum
from dataclasses import dataclass
from typing import List
from playwright.async_api import Page, Locator, Union


@dataclass
class ResponseLoaderSettings:
    max_responses: int = 60
    max_renders: int = 5
    use_proxies: bool = False
    max_proxies: int = 10,
    render_pages: bool = False
    max_retires: int = 0


@dataclass
class ScrapedResponse:
    html: str
    status_code: int
    url: str
    href_elements: List[Locator]
    page: Union[Page, None]


# this if for a future feature where we can try to get different states of a page event
# when previous ones failed
class RenderStateRetry(Enum):
    INITIAL = 0,
    LOAD_STATE_TIMEOUT = 1,
    REQUEST_FINISHED_EVENT_TIMEOUT = 2
