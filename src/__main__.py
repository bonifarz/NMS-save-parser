import logging
import sys
import os
from NMS_save_parser import save_parser_class

def log_uncaught(exc_type, exc_value, exc_tb):
    """Brute force logging of uncaught exceptions."""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return
    log.error("Oops, we ran into an uncaught exception:\n\n",
              exc_info=(exc_type, exc_value, exc_tb))

if __name__ == "__main__":
    """Set up a basic logger, then initialize and run the NMS-save-parser."""
    os.makedirs("./download/", exist_ok=True)
    os.makedirs("./io/", exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s    %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("io/log.txt", encoding="utf-8"),
        ],
    )
    log = logging.getLogger(__name__)
    sys.excepthook = log_uncaught
    i = save_parser_class(log)
    i.parse_saves_from_io()