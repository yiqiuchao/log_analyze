#!/usr/bin/env python

import os
import re
import common
import regexs
from collections import defaultdict
from operator import itemgetter
import signal
import multiprocessing
import argparse

g_logger = common.init_logger()

parser = argparse.ArgumentParser()
parser.add_argument('-d', '--dir', type=str, default='./',
                    help='the log file diretory.')
parser.add_argument('-p', '--prev', action='store_true',
                    help='if parse prev logs.')
parser.add_argument('-f', '--status_file', action='store_true',
                    help='if get path from the local file.')
args = parser.parse_args()

g_shared_list        = multiprocessing.Manager().list()
g_counter_processed  = multiprocessing.Value('i', 0)
g_counter_processing = multiprocessing.Value('i', 0)

def parse(file, devices, messages):
    with open(file, 'r') as fd:
        for line in fd:
            for index, regex in enumerate(regexs.regexs):
                keyword, search, replace = regex
                if re.search(keyword, line):
                    s = re.sub(search, replace, line)
                    if s:
                        common.debug_print(s, index, -1)
                        if index == 0:
                            l = s.split('\t')
                            if (len(l) > 4):
                                devices[common.delete_prefix(l[0], 'ACT-')] = l[4]
                            # devices[l[4]] = l[4]
                        # get device name or IP
                        l = s.split('\t', 1)
                        common.debug_print(l, index, -1)
                        if (len(l) > 1):
                            name = common.delete_prefix(l[0], 'ACT-')
                            messages[name].append(l[1])

def save_to_memory(devices, messages, loginfo):
    # sort map.
    items=[]
    for key, value in devices.iteritems():
        if key and value:
            items.append((value, key))
    
    if not loginfo.endswith('\n'):
        loginfo += '\n'

    global g_shared_list
    global g_counter_processed
    # += operation is not atomic, so we need to get a lock:
    with g_counter_processed.get_lock():
        g_counter_processed.value += 1
        g_shared_list.append("logfile[%d]: %s" % (g_counter_processed.value, loginfo))
        device_index = int(0)
        for item in sorted(items):
            name = item[1]
            device_index += 1
            g_shared_list.append("Device[%d]\t%20s\t%s\n" % (device_index, devices[name], name))
            for line in messages[name]:
                g_shared_list.append('\t%s' % line)
            if not g_shared_list[-1].endswith('\n'):
                g_shared_list.append("\n")
            g_shared_list.append("="*120)
            g_shared_list.append("\n")

def parse_line(line):
    with g_counter_processing.get_lock():
        g_counter_processing.value += 1
        g_logger.info("Processing [%d/%d]: %s" % (g_counter_processing.value, g_num_lines, line.split()[2]))
    logdir   = os.path.dirname(line.split()[2])
    devices  = defaultdict(str)
    messages = defaultdict(list)
    for file in os.listdir(logdir):
        if re.match(logfile, file):
            parse(os.path.join(logdir, file), devices, messages)
    # save(fd_out, logdir, index)
    save_to_memory(devices, messages, line)

# def save(fd, logdir, file_index):
#     # sort map.
#     items=[]
#     for key, value in devices.iteritems():
#         if key and value:
#             items.append((value, key))
    
#     index = int(0)
#     print >> fd, "logfile[%d]: " % file_index, logdir
#     for item in sorted(items):
#         name = item[1]
#         index += 1
#         print >> fd, "Device[%d]\t%20s\t%s" % (index, devices[name], name)
#         for line in messages[name]:
#             print >> fd, '\t', line,
#         print >> fd, "="*120

def mp_handler(worker, params, num_of_threads):
    original_sigint_handler = signal.signal(signal.SIGINT, signal.SIG_IGN)
    pool = multiprocessing.Pool(processes=num_of_threads)
    signal.signal(signal.SIGINT, original_sigint_handler)
    try:
        res = pool.map_async(worker, params)
        # waiting for a long time to make sure it's done its jobs.
        res.get(1000000)
    except KeyboardInterrupt:
        g_logger.debug("Caught KeyboardInterrupt, terminating workers")
        pool.terminate()
    else:
        g_logger.debug("Normal termination")
        pool.close()
    pool.join()

# {key=name, value=IP}, we assume that both IP and name are unique.
# devices  = defaultdict(str)
# {key=name, value=list of logs}
# messages = defaultdict(list)

logfile = 'logfile'
if args.prev:
    logfile = 'prev_' + logfile

g_num_lines = int(0)        
if args.status_file:
    lines = []
    with open('status_code.txt', 'r') as fd:
        for line in fd:
            # parse_line(line)
            lines.append(line)
            g_num_lines += 1
        
    mp_handler(parse_line, lines, 8)
    g_shared_list.append("Total logs processed: %d" % g_counter_processed.value)
else:
    for file in os.listdir(args.dir):
        if re.match(logfile, file):
            # parse(args.dir+file)
            print "TODO"
    # save_to_memory(g_shared_list, args.dir, 0)

with open('log_parser.txt', 'w') as fd_out:
    for item in g_shared_list:
        fd_out.write("%s" % item)

common.beep()