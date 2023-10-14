import unittest

from selectolax.parser import HTMLParser

from models.target_element import TargetElement


class TestTargetElementModel(unittest.TestCase):
    def setUp(self):
        self.single_class_attributes = {
            "attributes": [
                {"name": "class", "value": "price_color"},
                {"name": "class", "value": "price_amount"},
                {"name": "id", "value": "1"}
            ]
        }
        self.multi_class_attributes = {
            "attributes": [
                {"name": "class", "value": "price_color price_amount"},
                {"name": "id", "value": "1"}
            ]
        }

        self.search_hierarchy_raw = [
                {"name": "class", "value": "grandparent"},
                {"name": "class", "value": "parent someother_class"},
                {"name": "class", "value": "child"},
            ]

        formatted_search_hierarchy_attrs = TargetElement.collect_attributes(self.search_hierarchy_raw)
        self.search_hierarchy_formatted = TargetElement.format_search_hierarchy_from_attributes([formatted_search_hierarchy_attrs])

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

        self.parser = HTMLParser(self.html)

    def test_collect_attributes_single_class(self):
        """Test collecting attributes with a single class value."""
        out_put = TargetElement.collect_attributes(self.single_class_attributes["attributes"])
        expected_out = {'class': 'price_color price_amount', 'id': '1'}
        self.assertEqual(expected_out, out_put, "Collect attributes (single class) failed")

    def test_collect_attributes_multi_class(self):
        """Test collecting attributes with multiple class values."""
        out_put = TargetElement.collect_attributes(self.multi_class_attributes["attributes"])
        expected_out = {'class': 'price_color price_amount', 'id': '1'}
        self.assertEqual(expected_out, out_put, "Collect attributes (multi-class) failed")

    def test_build_attributes_into_search_hierarchy(self):
        """Test building a search hierarchy from collected attributes."""
        attrs = TargetElement.collect_attributes(self.multi_class_attributes["attributes"])

        element = TargetElement("test_element", "target", 0, attrs, [])

        element.element_search_hierarchy = TargetElement.format_search_hierarchy_from_attributes([attrs])

        expected_out = [".price_color.price_amount", "[id=1]"]
        self.assertEqual(expected_out, element.element_search_hierarchy)

    def test_search_hierarchy(self):
        print(self.search_hierarchy_formatted)


if __name__ == '__main__':
    unittest.main()
