from typing import List

from bs4 import BeautifulSoup

from models.target_element import TargetElement
from models.scarped_data import ScrapedData
from observables.observable_collection import ObservableCollection


class DataScraper:
    def __init__(self, target_elements: list[TargetElement]):
        self.target_elements: list[TargetElement] = target_elements

        ObservableCollection.add_observer_to_target("responses", self.collect_data)

    def collect_data(self, response: dict) -> List[List[ScrapedData]]:
        results = []

        for url, content in response.items():
            # Parse the HTML content of the response
            soup = BeautifulSoup(content, "html.parser")
            for target_element in self.target_elements:
                # Check if the element is meant to target the current URL
                if not self.is_target_page(target_element.target_pages, url):
                    # Skip collecting data with this element on the current page
                    continue
                data = self.collect_all_target_elements(url, target_element, soup)
                results.append(data)
        print(results)
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
    def is_target_page(element_target_pages: list[str], url: str) -> bool:
        # Check if the element is meant to target the current URL
        return url in element_target_pages or element_target_pages.count('any')
