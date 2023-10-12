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

        self._clear_func_mapping = {
            'csv': self.clear_csv
        }

    def setup(self, clear: bool = False) -> None:
        if clear:
            for save_type in self.save_types:
                clear_func = self._clear_func_mapping.get(save_type)
                if not clear_func:
                    Logger.console_log(f"Unknown clear type: {save_type}", LoggerLevel.WARNING)
                    continue
                clear_func(self.save_config.get(save_type))

        for save_type in self.save_types:
            save_func = self._save_func_mapping.get(save_type)

            if not save_func:
                Logger.console_log(f"Unknown save type: {save_type}", LoggerLevel.WARNING)
                continue

            save_func(self.save_config.get(save_type), self.data_keys, len(self.data_keys))

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

            save_func(self.save_config.get(save_type), data, len(self.data_keys))

    @staticmethod
    def clear_csv(clear_data: Dict[Any, Any]) -> None:
        file_path = clear_data.get('file_path', 'bad_file_path')

        if file_path == "bad_file_path":
            raise SyntaxError("No file path was given for saving csv")

        with open(file_path, "w") as file:
            file.truncate(0)

    @staticmethod
    def save_csv(csv_options: Dict[Any, Any], data: Any, t_items: int) -> None:
        """
        Data is saved in a csv file based on the specified options

        :param t_items: how many total items there are
        :param csv_options: Dict containing csv saving options
        :param data: Data to be saved
        """

        ALLOWED_ORIENTATIONS = ['horizontal', 'vertical']

        # if save feature is disabled return without saving
        if not csv_options.get('enabled', True):
            return

        csv_file_path = csv_options.get('file_path', 'bad_file_path')
        orientation = csv_options.get('orientation', 'horizontal')

        if csv_file_path == "bad_file_path":
            raise SyntaxError("No file path was given for saving csv")

        if orientation not in ALLOWED_ORIENTATIONS:
            raise ValueError(f"Unknown orientation: {orientation}, allowed orientations are => {ALLOWED_ORIENTATIONS} ")

        ordered_data = [[] for _ in range(t_items)]

        for index, item in enumerate(ordered_data):
            item.extend(data[index::len(ordered_data)])

        with open(csv_file_path, mode='a', newline='') as csv_file:
            csv_writer = csv.writer(csv_file)
            # horizontal means item names are on the side
            if orientation == 'horizontal':
                csv_writer.writerows(ordered_data)
            # else its vertical which means item names are on the top
            else:
                csv_writer.writerows(zip(*ordered_data))

    @staticmethod
    def save_txt(txt_options: Dict[Any, Any], data: Any, t_items: int) -> None:
        """
        Placeholder for future implementation of txt saving feature
        """
        raise NotImplementedError("This feature will be added soon!")

    @staticmethod
    def save_database(db_options: Dict[Any, Any], data: Any, t_items: int) -> None:
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
