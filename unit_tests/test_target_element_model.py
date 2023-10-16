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

        self.css_selector = {
            "css_selector": ".some-class"
        }

        self.search_hierarchy_raw_one = [
            {"name": "class", "value": "grandparent"},
            {"name": "class", "value": "parent someother_class"},
            {"name": "class", "value": "child"},
        ]

        self.search_hierarchy_raw_two = [
            {'name': 'class', 'value': 'btn active'},
            {'name': 'id', 'value': 'submit-button'},
            {'name': 'data-role', 'value': 'button'}
        ]

        self.search_hierarchy_raw_with_css = [
            {'name': 'class', 'value': 'btn active'},
            {'css_selector': '[id=submit-button]'},
            {'name': 'data-role', 'value': 'button'}
        ]

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

    def test_css_selector(self):
        out_put = TargetElement.collect_attributes([self.css_selector])

        expected_out = {'css_selector': ".some-class"}
        self.assertEqual(expected_out, out_put)

    def test_build_attributes_into_search_hierarchy(self):
        """Test building a search hierarchy from collected attributes."""
        attrs = TargetElement.collect_attributes(self.multi_class_attributes["attributes"])

        element = TargetElement("test_element", 0)

        element.element_search_hierarchy = TargetElement.format_search_hierarchy_from_attributes([attrs])

        expected_out = [".price_color.price_amount", "[id=1]"]
        self.assertEqual(expected_out, element.element_search_hierarchy)

    def test_search_hierarchy_from_raw_hierarchy(self):
        hierarchy = TargetElement.create_search_hierarchy_from_raw_hierarchy(self.search_hierarchy_raw_one)

        expected_out = ['.grandparent', '.parent.someother_class', '.child']
        self.assertEqual(expected_out, hierarchy)

        hierarchy = TargetElement.create_search_hierarchy_from_raw_hierarchy(self.search_hierarchy_raw_two)

        expected_out = ['.btn.active', '[id=submit-button]', '[data-role=button]']
        self.assertEqual(expected_out, hierarchy)

        hierarchy = TargetElement.create_search_hierarchy_from_raw_hierarchy(self.search_hierarchy_raw_with_css)

        expected_out = ['.btn.active', '[id=submit-button]', '[data-role=button]']
        self.assertEqual(expected_out, hierarchy)


if __name__ == '__main__':
    unittest.main()
