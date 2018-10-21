#!/usr/bin/env python
import logging
import signal
import multiprocessing

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

def delete_prefix(name, pre):
    if pre in name:
        return name[len(pre):]
    return name

def debug_print(s, index, print_index):
    if index == print_index:
        print s

def beep():
    print "\a"

def mp_handler(worker, params, num_of_threads):
    original_sigint_handler = signal.signal(signal.SIGINT, signal.SIG_IGN)
    pool = multiprocessing.Pool(processes=num_of_threads)
    signal.signal(signal.SIGINT, original_sigint_handler)
    try:
        res = pool.map_async(worker, params)
        # waiting for a long time to make sure it's done its jobs.
        res.get(1000000)
    except KeyboardInterrupt:
        print "Caught KeyboardInterrupt, terminating workers"
        pool.terminate()
    else:
        pool.close()
    pool.join()