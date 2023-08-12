import unittest
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


if __name__ == '__main__':
    unittest.main()
