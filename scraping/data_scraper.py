from typing import List, Dict, Generator, Union, Any
from bs4 import BeautifulSoup, ResultSet

from events.event_dispatcher import EventDispatcher, Event
from loaders.config_loader import ConfigLoader
from models.scarped_data import ScrapedData
from factories.config_element_factory import ConfigElementFactory, TargetElement, SelectorElement


class DataScraper:
    def __init__(self, config: ConfigLoader, elements: Dict[str, List[TargetElement | SelectorElement]], event_dispatcher: EventDispatcher):
        """
        Initialize the DataScraper class.

        Args:
            config (ConfigLoader): The configuration loader.
            elements (dict): Dictionary containing lists of target or selector elements.
            event_dispatcher (EventDispatcher): An EventDispatcher instance used for event handling.
        """
        self.config = config
        self.elements = elements

        self.event_dispatcher = event_dispatcher
        self.event_dispatcher.add_listener("new_responses", self.collect_data)

    def collect_data(self, event: Event) -> None:
        """
        (OUT DATED DOC)
        Collect data from the responses obtained by the response loader.

        Args:
            event (Event): The event triggered with the responses' data.
        """
        responses = event.data

        all_scraped_data = []
        for response in responses:
            scraped_data = self._process_response(response)
            all_scraped_data.extend(scraped_data)

        self.event_dispatcher.trigger(Event("scraped_data", "data", data=all_scraped_data))

    def _process_response(self, response: Dict[str, str]) -> List[ScrapedData]:
        results = []

        for url, content in response.items():
            soup = BeautifulSoup(content, "html.parser")

            if self.config.only_scrape_sub_pages(url):
                continue

            for element_type, element_data in self.elements.items():
                if not element_data:
                    continue
                results.extend(self._collect_elements(url, element_type, soup, element_data))

        return results

    def _collect_elements(self, url: str, element_type: str, soup: BeautifulSoup, element_data: List[Union[TargetElement, SelectorElement]]) -> Generator[ScrapedData, Any, Any]:
        for element in element_data:
            if element_type == ConfigElementFactory.ELEMENT_SELECTOR:
                data = self._collect_all_selector_elements(url, element, soup)
            else:
                data = self._collect_all_target_elements(url, element, soup)
            yield data

    @staticmethod
    def _collect_all_target_elements(url: str, target_element: TargetElement, soup: BeautifulSoup) -> ScrapedData:
        """
        Collect data from all target elements specified by the TargetElement.

        Args:
            url (str): The URL of the web page.
            target_element (TargetElement): The TargetElement instance representing the element to collect data from.
            soup (BeautifulSoup): The BeautifulSoup instance representing the parsed HTML content.

        Returns:
            ScrapedData: An instance containing the collected data.
        """
        result_set: ResultSet = soup.find_all(
            attrs=target_element.element_search_hierarchy[0]) if target_element.element_search_hierarchy else []

        if len(target_element.element_search_hierarchy) <= 1:
            return ScrapedData(url, result_set, target_element.element_id)

        for attr in target_element.element_search_hierarchy[1:]:
            for tag in result_set:
                temp_result_set = tag.find_all(attrs=attr)
                if temp_result_set:
                    result_set = temp_result_set
                else:
                    return ScrapedData(url, result_set, target_element.element_id)

        return ScrapedData(url, result_set, target_element.element_id)

    @staticmethod
    def _collect_all_selector_elements(url: str, selector_element: SelectorElement, soup: BeautifulSoup) -> ScrapedData:
        """
        Collect data from all selector elements specified by the SelectorElement.

        Args:
            url (str): The URL of the web page.
            selector_element (SelectorElement): The SelectorElement instance representing the element to collect data from.
            soup (BeautifulSoup): The BeautifulSoup instance representing the parsed HTML content.

        Returns:
            ScrapedData: An instance containing the collected data.
        """
        return ScrapedData(url, soup.select(selector_element.css_selector), selector_element.element_id)

