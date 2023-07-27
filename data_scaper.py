import requests

from bs4 import BeautifulSoup
from requests import Response

from models.target_element import TargetElement
from loaders.config_loader import ConfigLoader
from loaders.response_loader import ResponsesLoader
from models.scarped_data import ScrapedData


class DataScraper:
    def __init__(self, config: ConfigLoader, target_elements: list[TargetElement]):
        self.config = config
        self.urls = self.config.get_target_urls()

        self.target_elements = target_elements

        self.response_loader = ResponsesLoader(self.urls)
        self.response_loader.collect_responses()

    def collect_data(self) -> list[ScrapedData]:
        results = []

        for url, content in self.response_loader.get_responses(included_errors=False):
            # Parse the HTML content of the response
            soup = BeautifulSoup(content, "html.parser")
            for target_element in self.target_elements:
                # Check if the element is meant to target the current URL
                if not self.is_target_page(target_element.target_page, url):
                    # Skip collecting data with this element on the current page
                    continue
                data = self.collect_all_target_elements(url, target_element, soup)
                results += data

        return results

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
    def is_target_page(element_page_target: str, url: str) -> bool:
        # Check if the element is meant to target the current URL
        return element_page_target in ["any", url]

    @staticmethod
    def _load_responses(urls: list[str]) -> dict[str, Response]:
        if not urls:
            print("WARNING: No URLs found!")

        responses = {}
        for url in urls:
            # Fetch the response for each URL
            response = requests.get(url)
            if response.status_code != 200:
                raise Exception(f"Failed to load the URL: {url}")
            responses[url] = response

        return responses
