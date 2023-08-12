from enum import Enum
from datetime import datetime


class LoggerLevel(Enum):
    """Enumeration for logging levels."""
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class Logger:
    """A simple logger utility for logging messages to the console and a file.

    This class provides methods to log messages to the console and write messages to a file.
    It supports three log levels: INFO, WARNING, and ERROR, defined in the LoggerLevel enumeration.

    Example usage:
    Logger.console_log("This is an informational message.", LoggerLevel.INFO)
    Logger.file_log("This is an error message.", LoggerLevel.ERROR, include_time=True)
    """

    # flag to keep track if a error was logged
    had_error = False

    @staticmethod
    def console_log(message: str, level: LoggerLevel, include_time: bool = False) -> None:
        """Log a message to the console.

        Args:
            message (str): The message to log.
            level (str): The log level (INFO, WARNING, or ERROR) from the LoggerLevel enumeration.
            include_time (bool, optional): Whether to include the current time in the log message.
                Defaults to False.
        """

        if level == LoggerLevel.ERROR:
            Logger.had_error = True

        # if include time, reformat the message to include the time
        message = f"{Logger._get_data_time()}: {message}" if include_time \
            else message

        print(f"[{level.value}] {message}\n")

    @staticmethod
    def file_log(file_path: str, message: str, level: LoggerLevel, include_time: bool = False):
        """Write a message to a file.

        Args:
            file_path (str): The path to the log file.
            message (str): The message to log.
            level (LoggerLevel): The log level (INFO, WARNING, or ERROR) from the LoggerLevel enumeration.
            include_time (bool, optional): Whether to include the current time in the log message.
                Defaults to False.
        """
        if level == LoggerLevel.ERROR:
            Logger.had_error = True

        try:
            with open(file_path, 'a') as output_file:
                # if include time, reformat the message to include the time
                message = f"{Logger._get_data_time()}: {message}" if include_time \
                    else message

                output_file.write(f"[{level.value}] {message}\n")
        except OSError as ose:
            Logger.console_log(f"Failed to write to file: {file_path}\nERROR: {ose}", LoggerLevel.ERROR)

    @staticmethod
    def _get_data_time() -> str:
        """Returns the current time as a formatted string.

        Returns:
            str: The current time in the format "Y-m-d H:M:S".
        """
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return current_time


if __name__ == "__main__":
    Logger.console_log("LMAO", LoggerLevel.ERROR)
    Logger.file_log('../../DataScraper/debug_output/output.text', "TEST", LoggerLevel.INFO, include_time=True)
