from typing import List, Callable, Dict, Any
from bs4 import BeautifulSoup, PageElement

from events.event import Event
from models.target_element import TargetElement
from models.scarped_data import ScrapedData
from events.observables.observable_list import ObservableList


class DataScraper:
    # responses to be processed
    def __init__(self, target_elements: list[TargetElement], parser_call_back: Callable):
        self.target_elements: list[TargetElement] = target_elements
        self.parser_call_back = parser_call_back

        self.observable_hrefs = ObservableList("hrefs")

        # listen for new responses from the responses loader
        ObservableList.add_listener_to_target("responses", self.collect_data, collection_type=ObservableList)

    def collect_data(self, event: Event) -> None:
        responses = event.data

        hrefs = []
        results = []
        for response in responses:
            page_data = self._process_response(response)
            hrefs.extend(page_data['hrefs'])
            results.append(page_data['results'])

        self.parser_call_back(results)
        # editing this list will trigger the page navigator
        self.observable_hrefs.extend(hrefs)

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
