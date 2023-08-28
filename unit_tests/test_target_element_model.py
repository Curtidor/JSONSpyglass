import unittest

from bs4 import BeautifulSoup, ResultSet

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
                {"name": "class", "value": ["price_color", "price_amount"]},
                {"name": "id", "value": "1"}
            ]
        }

        self.search_hierarchy = [
                {"name": "class", "value": "grandparent"},
                {"name": "class", "value": "parent someother_class"},
                {"name": "class", "value": "child"}
            ]

        self.search_hierarchy = TargetElement.format_search_hierarchy(self.search_hierarchy)

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

        self.soup = BeautifulSoup(self.html, 'html.parser')

    def test_collect_attributes_single_class(self):
        """Test collecting attributes with a single class value."""
        out_put = TargetElement.collect_attributes(self.single_class_attributes["attributes"])
        expected_out = {'class': ['price_color', 'price_amount'], 'id': ['1']}
        self.assertEqual(expected_out, out_put, "Collect attributes (single class) failed")

    def test_collect_attributes_multi_class(self):
        """Test collecting attributes with multiple class values."""
        out_put = TargetElement.collect_attributes(self.multi_class_attributes["attributes"])
        expected_out = {'class': ['price_color', 'price_amount'], 'id': ['1']}
        self.assertEqual(expected_out, out_put, "Collect attributes (multi-class) failed")

    def test_build_attributes_into_search_hierarchy(self):
        """Test building a search hierarchy from collected attributes."""
        attrs = TargetElement.collect_attributes(self.multi_class_attributes["attributes"])

        element = TargetElement('test_element', 1, ['any'], 'some_tag', attrs)
        element.create_search_hierarchy_from_attributes()

        expected_out = [{'class': ['price_color', 'price_amount'], 'id': ['1']}]
        self.assertEqual(expected_out, element.element_search_hierarchy)

    def test_search_hierarchy(self):
        result_set: ResultSet = self.soup.find_all(
            attrs=self.search_hierarchy[0]) if self.search_hierarchy else []

        for attr in self.search_hierarchy[1:]:
            for tag in result_set:
                temp_result_set = tag.find_all(attrs=attr)
                if temp_result_set:
                    result_set = temp_result_set
                else:
                    break

        output_text = [text.text.strip() for text in result_set]
        expected = ['CHILD ELEMENT']
        self.assertEqual(expected, output_text)


if __name__ == '__main__':
    unittest.main()
