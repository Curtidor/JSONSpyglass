from typing import List, Dict
from bs4 import BeautifulSoup, PageElement

from events.event_dispatcher import EventDispatcher, Event
from models.target_element import TargetElement
from models.scarped_data import ScrapedData
from utils.logger import LoggerLevel, Logger


class DataScraper:
    def __init__(self, target_elements: list[TargetElement], event_dispatcher: EventDispatcher, max_empty_responses: int = 20):
        """
        Initialize the DataScraper class.

        Args:
            target_elements (list[TargetElement]): List of TargetElement instances representing the elements to scrape.
            event_dispatcher (EventDispatcher): An EventDispatcher instance used for event handling.
            max_empty_responses (int, optional): The maximum number of consecutive empty responses before exiting. Defaults to 20.
        """
        self.target_elements: list[TargetElement] = target_elements
        self._max_empty_responses = max_empty_responses
        self._empty_responses = 0

        self.event_dispatcher = event_dispatcher
        self.event_dispatcher.add_listener("new_responses", self.collect_data)

    def collect_data(self, event: Event) -> None:
        """
        Collect data from the responses obtained by the response loader.

        Args:
            event (Event): The event triggered with the responses data.
        """
        responses = event.data
        if not responses:
            Logger.console_log("No data to scrape", LoggerLevel.WARNING)
            if self._empty_responses == self._max_empty_responses:
                Logger.console_log(f"EXITING DUE TO NO DATA FOUND IN THE LAST {self._empty_responses} RESPONSES", LoggerLevel.INFO)
                return
            self._empty_responses += 1

        # use a set to ensure there are no duplicate hrefs to avoid redundant requests
        hrefs = set()
        results = []
        for response in responses:
            page_data = self._process_response(response)
            [hrefs.add(href) for href in page_data['hrefs']]
            results.extend(page_data['results'])

        # this event is listened for by the data parser
        self.event_dispatcher.trigger(Event("scraped_data", "raw_data", data=results))
        # editing this list will trigger the page navigator
        self.event_dispatcher.trigger(Event("new_hrefs", "data_update", data=hrefs))

    def _process_response(self, response: Dict[str, str]) -> dict[str, list[list[ScrapedData]] | set[PageElement]]:
        """
        Process the response data obtained from the response loader.

        Args:
            response (Dict[str, str]): Dictionary containing URL and HTML content.

        Returns:
            Dict[str, Any]: A dictionary containing extracted hrefs and target element data.
        """
        # use a set to ensure there are no duplicate hrefs to avoid redundant requests
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
        """
        Collect all hrefs from the HTML content.

        Args:
            soup (BeautifulSoup): The BeautifulSoup instance representing the parsed HTML content.

        Returns:
            List[PageElement]: A list of PageElement instances representing the hrefs found in the HTML.
        """
        return [href.unwrap() for href in soup.find_all("a", href=True)]

    @staticmethod
    def collect_all_target_elements(url: str, target_element: TargetElement, soup: BeautifulSoup) -> list[ScrapedData]:
        """
        Collect data from all target elements specified by the TargetElement.

        Args:
            url (str): The URL of the web page.
            target_element (TargetElement): The TargetElement instance representing the element to collect data from.
            soup (BeautifulSoup): The BeautifulSoup instance representing the parsed HTML content.

        Returns:
            list[ScrapedData]: A list of ScrapedData instances containing the collected data.
        """
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
        """
        Check if the element is meant to target the current URL.

        Args:
            element_target_pages (list[str]): List of URLs or 'any' to indicate any URL is a target.
            url (str): The URL of the web page.

        Returns:
            bool: True if the element targets the current URL, False otherwise.
        """
        # Check if the element is meant to target the current URL
        return url in element_target_pages or element_target_pages.count('any')
