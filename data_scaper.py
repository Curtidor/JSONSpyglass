from typing import List, Callable, Dict, Any
from bs4 import BeautifulSoup, PageElement

from events.event_dispatcher import EventDispatcher, Event
from models.target_element import TargetElement
from models.scarped_data import ScrapedData
from utils.logger import LoggerLevel, Logger


class DataScraper:
    # responses to be processed
    def __init__(self, target_elements: list[TargetElement], parser_call_back: Callable,event_dispatcher: EventDispatcher ):
        self.target_elements: list[TargetElement] = target_elements
        self.parser_call_back = parser_call_back

        self.event_dispatcher = event_dispatcher
        self.event_dispatcher.add_listener("new_responses", self.collect_data)

    def collect_data(self, event: Event) -> None:
        responses = event.data
        if not responses:
            Logger.console_log("No data to scrape", LoggerLevel.WARNING)

        hrefs = []
        results = []
        for response in responses:
            page_data = self._process_response(response)
            hrefs.extend(page_data['hrefs'])
            results.extend(page_data['results'])

        # this event is listened for by the data parser
        self.event_dispatcher.trigger(Event("scraped_data", "raw_data", data=results))
        # editing this list will trigger the page navigator
        self.event_dispatcher.trigger(Event("new_hrefs", "data_update", data=hrefs))

    def _process_response(self, response: Dict[str, str]) -> Dict[str, Any]:
        hrefs = []
        results = []
        for url, content in response.items():
            # Parse the HTML content of the response
            soup = BeautifulSoup(content, "html.parser")
            hrefs.extend(self._collect_hrefs(soup))
            for target_element in self.target_elements:
                if not self.is_target_page(target_element.target_pages, url):
                    continue
                data = self.collect_all_target_elements(url, target_element, soup)
                results.append(data)

        return {'hrefs': hrefs, 'results': results}

    @staticmethod
    def _collect_hrefs(soup: BeautifulSoup) -> List[PageElement]:
        return [href.unwrap() for href in soup.find_all("a", href=True)]

    @staticmethod
    def collect_all_target_elements(url: str, target_element: TargetElement, soup: BeautifulSoup) -> list[ScrapedData]:
        results = []
        for attr_name, attr_value in target_element.attributes.items():
            # Find all elements that match the target_element's tag and attributes
            # unless attr_value contains (any) in which case we collect all data for the given tag
            if attr_value.count('any'):
                results.append(
                    ScrapedData(url, soup.find_all(target_element.tag), target_element.element_id))
            else:
                results.append(
                    ScrapedData(url, soup.find_all(target_element.tag, attr_value), target_element.element_id))
        return results

    @staticmethod
    def is_target_page(element_target_pages: list[str], url: str) -> bool:
        # Check if the element is meant to target the current URL
        return url in element_target_pages or element_target_pages.count('any')
