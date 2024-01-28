import logging

from typing import Dict


class CLogger(logging.Logger):
    def __init__(self, name: str, level: int = logging.INFO, handlers: Dict[logging.Handler, int] = None,
                 formatter: logging.Formatter = None):
        """
        Initialize a custom logger.

        :param name: The name of the logger.
        :param level: The logging level.
        :param handlers: Dictionary of handlers and their levels.
        :param formatter: The log formatter.
        """
        super().__init__(name, level)
        formatter = formatter or logging.Formatter("%(asctime)s| %(name)s | %(levelname)s | %(message)s")
        if handlers:
            for handler, h_level in handlers.items():
                handler.setLevel(h_level)
                handler.setFormatter(formatter)
                self.addHandler(handler)
