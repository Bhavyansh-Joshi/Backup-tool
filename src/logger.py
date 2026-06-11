import logging
from src.config import LOG_DIR

def setup_logger():

    logger = logging.getLogger("Backup")

    logger.setLevel(logging.INFO)

    ch = logging.StreamHandler()
    fh = logging.FileHandler(LOG_DIR)

    ch.setLevel(logging.INFO)
    fh.setLevel(logging.INFO)

    fmt = logging.Formatter("%(asctime)s %(levelname)s: %(message)s")
    ch.setFormatter(fmt)
    fh.setFormatter(fmt)


    logger.addHandler(ch)
    logger.addHandler(fh)
    logger.propagate = False

    return logger