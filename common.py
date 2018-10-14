#!/usr/bin/env python
import logging

# Set up loggings
def init_logger():
    # create logger
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    # create console handler and set level
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)

    # create formatter
    formatter = logging.Formatter('%(asctime)s - %(process)d - %(levelname)s - %(message)s')

    # add formatter to ch
    ch.setFormatter(formatter)

    # add ch to logger
    logger.addHandler(ch)
    return logger