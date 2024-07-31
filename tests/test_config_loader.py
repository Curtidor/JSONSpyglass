import unittest
from loaders.config_loader import ConfigLoader


class TestConfigLoader(unittest.TestCase):
    def test_data_order(self):
        config = ConfigLoader('tests/test_configs/data_order_test.json')

        data_order = config.get_data_order()

        self.assertEqual(["Stock", "Book Name", "Book Price", "Not in data order", "element 4"], data_order)

    def test_data_order_with_unknown_name(self):
        config = ConfigLoader('tests/test_configs/data_order_test_bad_name.json')

        try:
            config.get_data_order()
        except ValueError as e:
            self.assertEqual(type(e), ValueError)
            return

        self.fail()


if __name__ == '__main__':
    unittest.main()
