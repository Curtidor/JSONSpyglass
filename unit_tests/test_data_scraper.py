import unittest

from selectolax.parser import HTMLParser

from models.target_element import TargetElement
from scraping.data_scraper import DataScraper

# TODO: (BUG) only the search hierarchy seems to work right now for selecting elements from html


class TestDataScraper(unittest.TestCase):
    def setUp(self) -> None:
        self.html = """
               <div class="grandparent">
                 <div class="parent someother_class">
                   <div class="child">
                     CHILD ELEMENT
                   </div>
                 </div>
                   <div class="child">
                       BAD ELEMENT
                   </div>
               </div
               """

        self.search_hierarchy_raw = [
            {"name": "class", "value": "grandparent"},
            {"name": "class", "value": "parent someother_class"},
            {"name": "class", "value": "child"},
        ]

        self.html_parser = HTMLParser(self.html)

    def test_collecting_elements_search_hierarchy(self):
        url = "some_url"
        hierarchy = TargetElement.create_search_hierarchy_from_raw_hierarchy(self.search_hierarchy_raw)
        target_element = TargetElement("test_element", 0, hierarchy)

        scraped_data = DataScraper.collect_all_target_elements(url, target_element, self.html_parser)

        first_node = scraped_data.nodes[0]

        self.assertEqual(first_node.text().strip(), "CHILD ELEMENT")


if __name__ == '__main__':
    unittest.main()
