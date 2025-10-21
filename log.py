import logging

SUCCESS_LEVEL_NUM = 25

class CustomFormatter(logging.Formatter):

    grey = "\x1b[38;20m"
    blue = "\x1b[34;20m"
    light_blue = "\x1b[94;20m"
    green = "\x1b[32;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    FORMATS = {
        logging.DEBUG: blue + format + reset,
        logging.INFO: light_blue + format + reset,
        SUCCESS_LEVEL_NUM: green + format + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: bold_red + format + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)

    def setup_logging(level=logging.WARNING):
        """Configures the root logger."""
        console = logging.StreamHandler()
        console.setFormatter(CustomFormatter())
        logging.basicConfig(level=level, handlers=[console], force=True)
    
    logging.addLevelName(SUCCESS_LEVEL_NUM, "SUCCESS")
    def success(self, message, *args, **kwargs):
        if self.isEnabledFor(SUCCESS_LEVEL_NUM):
            self._log(SUCCESS_LEVEL_NUM, message, args, **kwargs)
    logging.Logger.success = success
    
    # Add the module-level function that was missing
    def success_wrapper(msg, *args, **kwargs):
        if len(logging.root.handlers) == 0:
            logging.basicConfig()
        logging.root.success(msg, *args, **kwargs)
    
    logging.success = success_wrapper