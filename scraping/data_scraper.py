from typing import List, Dict
from selectolax.parser import HTMLParser

from EVNTDispatch import EventDispatcher, PEvent, EventType
from loaders.config_loader import ConfigLoader
from models.scarped_data import ScrapedData
from models.target_element import TargetElement


class DataScraper:
    def __init__(self,
                 config: ConfigLoader,
                 elements: List[TargetElement],
                 event_dispatcher: EventDispatcher):
        """
        Initialize the DataScraper class.

        Args:
            config (ConfigLoader): The configuration loader.
            elements (dict): List containing lists of target or selector elements.
            event_dispatcher (EventDispatcher): An EventDispatcher instance used for event handling.
        """
        self.config = config
        self.elements = elements

        self.event_dispatcher = event_dispatcher
        self.event_dispatcher.add_listener("new_responses", self.collect_data)

    def collect_data(self, event: PEvent) -> None:
        """
        (OUT DATED DOC)
        Collect data from the responses obtained by the response loader.

        Args:
            event (Event): The event triggered with the responses' data.
        """
        responses: Dict[str, str] = event.data
        for url in responses:
            scraped_data = self._process_response(url, responses[url])

            if not scraped_data:
                continue

            self.event_dispatcher.async_trigger_nw(PEvent("scraped_data", EventType.Base, data=scraped_data))

    def _process_response(self, url: str, content: str) -> List[ScrapedData]:
        results = []

        parser = HTMLParser(content)

        if self.config.only_scrape_sub_pages(url):
            return results

        for element in self.elements:
            scraped_data = self.collect_all_target_elements(url, element, parser)

            if scraped_data.nodes:
                results.append(scraped_data)

        return results

    @staticmethod
    def collect_all_target_elements(url: str, target_element: TargetElement, parser: HTMLParser) -> ScrapedData:
        """
        Collect data from all target elements specified by the TargetElement.

        Args:
            url (str): The URL of the web page.
            target_element (TargetElement): The TargetElement instance representing the element to collect data from.
            parser (HTMLParser): The Selectolax HTMLParser instance representing the parsed HTML content.

        Returns:
            ScrapedData: An instance containing the collected data.
        """
        result_set = parser.css(
            target_element.search_hierarchy[0]) if target_element.search_hierarchy else []

        if len(target_element.search_hierarchy) <= 1:
            return ScrapedData(url, result_set, target_element.element_id)

        for attr in target_element.search_hierarchy[1:]:
            new_result_set = []
            for tag in result_set:
                temp_result_set = tag.css(attr)
                if temp_result_set:
                    new_result_set.extend(temp_result_set)
            result_set = new_result_set

        return ScrapedData(url, result_set, target_element.element_id)
