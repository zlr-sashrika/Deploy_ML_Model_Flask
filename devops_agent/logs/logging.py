import sys
from functools import wraps

from loguru import logger as main_logger


class Logger:
    """A custom logger class to add pre and post separators to logs."""

    def __init__(self, separators: str = "=", length: int = 100):
        self.logger = main_logger
        self.separators = separators
        self.length = length

        # set log level
        # self.logger.setLevel()

        # loop over every method
        for method_name in ["debug", "info", "error", "warning", "critical"]:
            method = getattr(self.logger, method_name)
            setattr(self, method_name, self.formatter(method))

    def formatter(self, func):
        """A decorator to format logs before printing the logs."""

        @wraps(func)
        def wrapper(*args, **kwargs):
            """A wrapper for log formatter that prints the final log."""
            func(self.separators * self.length)
            func(*args, **kwargs)
            func(self.separators * self.length)

        return wrapper

    def set_level(self, *args, **kwargs):
        """A method that sets the log level of this logger."""
        # remove default level
        self.logger.remove()
        self.logger.add(sys.stdout, *args, **kwargs)


logger = Logger()
"""Example of using set level:
    ```
    # set level
    logger.set_level(level="INFO")
    ```
"""
