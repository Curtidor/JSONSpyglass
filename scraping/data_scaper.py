from typing import List, Dict
from bs4 import BeautifulSoup, PageElement

from events.event_dispatcher import EventDispatcher, Event
from loaders.config_loader import ConfigLoader
from models.target_element import TargetElement
from models.selector_element import SelectorElement
from models.scarped_data import ScrapedData
from utils.logger import LoggerLevel, Logger
from factories.config_element_factory import ConfigElementFactory


class DataScraper:
    def __init__(self, config: ConfigLoader, elements: Dict[str, List[TargetElement | SelectorElement]], event_dispatcher: EventDispatcher, max_empty_responses: int = 20):
        """
        Initialize the DataScraper class.

        Args:
            config (ConfigLoader): The configuration loader.
            elements (dict): Dictionary containing lists of target or selector elements.
            event_dispatcher (EventDispatcher): An EventDispatcher instance used for event handling.
            max_empty_responses (int, optional): The maximum number of consecutive empty responses before exiting. Defaults to 20.
        """
        self.config = config
        self.elements = elements
        self._max_empty_responses = max_empty_responses
        self._empty_responses = 0

        self.event_dispatcher = event_dispatcher
        self.event_dispatcher.add_listener("new_responses", self.collect_data)

    def collect_data(self, event: Event) -> None:
        """
        Collect data from the responses obtained by the response loader.

        Args:
            event (Event): The event triggered with the responses' data.
        """
        responses = event.data
        if not responses:
            Logger.console_log("No data to scrape", LoggerLevel.WARNING)
            if self._empty_responses == self._max_empty_responses:
                Logger.console_log(f"EXITING DUE TO NO DATA FOUND IN THE LAST {self._empty_responses} RESPONSES", LoggerLevel.INFO)
                return
            self._empty_responses += 1

        hrefs = set()
        results = []
        for response in responses:
            page_data = self._process_response(response)
            [hrefs.add(href) for href in page_data['hrefs']]
            results.extend(page_data['results'])

        self.event_dispatcher.trigger(Event("scraped_data", "raw_data", data=results))
        self.event_dispatcher.trigger(Event("new_hrefs", "data_update", data=hrefs))

    def _process_response(self, response: Dict[str, str]) -> dict[str, list[ScrapedData] | list[PageElement]]:
        """
        Process the response data obtained from the response loader.

        Args:
            response (dict): Dictionary containing URL and HTML content.

        Returns:
            dict: Dictionary containing extracted hrefs and target element data.
        """
        hrefs = []
        results = []
        for url, content in response.items():
            soup = BeautifulSoup(content, "html.parser")
            hrefs.extend(self._collect_hrefs(soup))

            if self.config.only_scrape_sub_pages(url):
                continue

            for element_type, element_data in self.elements.items():
                for element in element_data:
                    if element_type == ConfigElementFactory.ELEMENT_SELECTOR:

                        data = self._collect_all_selector_elements(url, element, soup)
                    else:
                        data = self._collect_all_target_elements(url, element, soup)
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
        return [href['href'] for href in soup.find_all("a", href=True)]

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
        return ScrapedData(url, soup.find_all(target_element.tag, attrs=target_element.attributes), target_element.element_id)

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

    @staticmethod
    def _is_target_page(element_target_pages: list[str], url: str) -> bool:
        """
        Check if the element is meant to target the current URL.

        Args:
            element_target_pages (list[str]): List of URLs or 'any' to indicate any URL is a target.
            url (str): The URL of the web page.

        Returns:
            bool: True if the element targets the current URL, False otherwise.
        """
        return url in element_target_pages or element_target_pages.count('any')