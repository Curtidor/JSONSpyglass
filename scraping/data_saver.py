import csv
from typing import Dict, Any, List

from utils.logger import Logger, LoggerLevel


class DataSaver:
    """
    This class is responsible for saving the data
    """

    def __init__(self, save_config: Dict[Any, Any], data_keys: List[str]):
        """
        Initializer. It instantiates the DataSaver with specified save configurations and data keys

        :param save_config: Dict which specifies how the data should be saved
        :param: data_keys: List of keys in order which will be used to save the data
        """

        self.data_keys = data_keys
        self.save_config = save_config
        self.save_types = []

        self._initialize_save_types()

        self._save_func_mapping = {
            'csv': self.save_csv,
            'txt': self.save_txt,
            'database': self.save_database
        }

    def save(self, data: Any):
        """
        Given data is saved based on the initialized save types and configurations

        :param data: Data to be saved
        """
        for save_type in self.save_types:
            save_func = self._save_func_mapping.get(save_type)

            if not save_func:
                Logger.console_log(f"Unknown save type: {save_type}", LoggerLevel.WARNING)
                continue

            save_func(self.save_config.get(save_type), data, self.data_keys)

    @staticmethod
    def save_csv(csv_options: Dict[Any, Any], data: Any, data_keys: List) -> None:
        """
        Data is saved in a csv file based on the specified options

        :param csv_options: Dict containing csv saving options
        :param data: Data to be saved
        :param data_keys: Keys to access and order the data
        """

        ALLOWED_ORIENTATIONS = ['horizontal', 'vertical']

        if not csv_options.get('enabled', True):
            return

        csv_file_path = csv_options.get('file_path', 'bad_file_path')
        orientation = csv_options.get('orientation', 'horizontal')

        if csv_file_path == "bad_file_path":
            raise SyntaxError("No file path was given for saving csv")

        if orientation not in ALLOWED_ORIENTATIONS:
            raise ValueError(f"Unknown orientation: {orientation}, allowed orientations are => {ALLOWED_ORIENTATIONS} ")

        # create a 2d list where the first element of each sub list
        # is the name of the type of data we are saving (i.e. [["book_name"], ["book_price"]])
        if data_keys:
            ordered_data = [[key] for key in data_keys]
        # if the order to save the data is not given we just save it all in a single list
        # in the future, this should change as the data scraper will look at the different elements
        # and save based on id, but for now we just save in a single list
        else:
            ordered_data = [[]]

        for index, item in enumerate(ordered_data):
            item.extend(data[index::len(ordered_data)])

        with open(csv_file_path, mode='w', newline='') as csv_file:
            csv_writer = csv.writer(csv_file)
            # horizontal means item names are on the side
            if orientation == 'horizontal':
                csv_writer.writerows(ordered_data)
            # else its vertical which means item names are on the top
            else:
                csv_writer.writerows(zip(*ordered_data))

    @staticmethod
    def save_txt(txt_options: Dict[Any, Any], data: Any, data_keys: List) -> None:
        """
        Placeholder for future implementation of txt saving feature
        """
        raise NotImplementedError("This feature will be added soon!")

    @staticmethod
    def save_database(db_options: Dict[Any, Any], data: Any, data_keys: List) -> None:
        """
        Placeholder for future implementation of database saving feature
        """
        raise NotImplementedError("This feature will be added soon!")

    def _initialize_save_types(self):
        """
        Initialize save types based on the save configurations
        """
        if self.save_types:
            return

        for save_type in self.save_config:
            self.save_types.append(save_type)
