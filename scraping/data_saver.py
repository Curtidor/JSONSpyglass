import aiofiles
import logging

from asyncio import Lock
from typing import Dict, Any, List

from utils.clogger import CLogger


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
        self._lock = Lock()
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

        self._logger = CLogger("DataSaver", logging.INFO, {logging.StreamHandler(): logging.INFO})

    async def setup(self, clear: bool = False) -> None:
        if clear:
            # clear all the files that where specified in the config file
            self._clear_file()

        for save_type in self.save_types:
            save_func = self._save_func_mapping.get(save_type)

            if not save_func:
                self._logger.warning(f"Unknown save type: {save_type}")
                continue

            await save_func(self.save_config.get(save_type), self.data_keys, len(self.data_keys), self._lock)

    async def save(self, data: Any) -> None:
        """
        Given data is saved based on the initialized save types and configurations

        :param data: Data to be saved
        """
        for save_type in self.save_types:
            save_func = self._save_func_mapping.get(save_type)

            if not save_func:
                self._logger.warning(f"Unknown save type: {save_type}")
                continue

            await save_func(self.save_config.get(save_type), data, len(self.data_keys), self._lock)

    @staticmethod
    def clear_csv(clear_data: Dict[Any, Any]) -> None:
        file_path = clear_data.get('file_path', 'bad_file_path')

        if file_path == "bad_file_path":
            raise SyntaxError("No file path was given for saving csv")

        with open(file_path, "w") as file:
            file.truncate(0)

    @staticmethod
    async def save_csv(csv_options: Dict[Any, Any], data: Any, t_items: int, lock: Lock) -> None:
        """
        Data is saved in a csv file based on the specified options

        :param lock:
        :param t_items: how many total items there are
        :param csv_options: Dict containing csv saving options
        :param data: Data to be saved
        """
        async with lock:
            BAD_FILE_PATH = 'bfp'
            ALLOWED_ORIENTATIONS = {'horizontal', 'vertical'}

            # if save feature is disabled return without saving
            if not csv_options.get('enabled', True):
                return

            csv_file_path = csv_options.get('file_path', BAD_FILE_PATH)
            orientation = csv_options.get('orientation', 'missing orientation')

            if csv_file_path == BAD_FILE_PATH:
                raise SyntaxError("No file path was given for saving csv")

            if orientation not in ALLOWED_ORIENTATIONS:
                raise ValueError(f"Unknown orientation: {orientation}, allowed orientations are => {ALLOWED_ORIENTATIONS} ")

            ordered_data = [[] for _ in range(t_items)]

            for index, item in enumerate(ordered_data):
                item.extend(data[index::len(ordered_data)])

            async with aiofiles.open(csv_file_path, mode='a', newline='') as csv_file:
                if orientation == 'horizontal':
                    # Write the rows as-is
                    await csv_file.writelines([','.join(row) + '\n' for row in ordered_data])
                else:
                    # Transpose the data and write it
                    transposed_data = [list(row) for row in zip(*ordered_data)]
                    await csv_file.writelines([','.join(row) + '\n' for row in transposed_data])

    @staticmethod
    async def save_txt(txt_options: Dict[Any, Any], data: Any, t_items: int, lock: Lock) -> None:
        """
        Placeholder for future implementation of txt saving feature
        """
        raise NotImplementedError("This feature will be added soon!")

    @staticmethod
    async def save_database(db_options: Dict[Any, Any], data: Any, t_items: int, lock: Lock) -> None:
        """
        Placeholder for future implementation of database saving feature
        """
        raise NotImplementedError("This feature will be added soon!")

    def _clear_file(self):
        for save_type in self.save_types:
            clear_func = self._clear_func_mapping.get(save_type)
            if not clear_func:
                self._logger.warning(f"Unknown clear type: {save_type}")
                continue
            clear_func(self.save_config.get(save_type))

    def _initialize_save_types(self):
        """
        Initialize save types based on the save configurations
        """
        if self.save_types:
            return

        for save_type in self.save_config:
            self.save_types.append(save_type)

