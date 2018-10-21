#!/usr/bin/env python

import os
import re
import json
from collections import defaultdict
from operator import itemgetter
import common
import argparse
# import signal
import multiprocessing

g_logger = common.init_logger()

g_counter_processed  = multiprocessing.Value('i', 0)
g_version_status     = multiprocessing.Manager().list()
g_lines = []
g_num_logs_total     = 0

parser = argparse.ArgumentParser()
parser.add_argument('-s', '--secrets', type=argparse.FileType('r'),
                    default='./secrets.json',
                    help='json file to read account information from')
parser.add_argument('-d', '--rootdir', type=str, default='./',
                    help='the root diretory.')
args = parser.parse_args()

with args.secrets as fd:
    js               = json.load(fd)
    # read patterns
    patterns         = js['patterns']
    pattern_ios      = re.compile(patterns['ios'])
    pattern_android  = re.compile(patterns['android'])
    pattern_status   = re.compile(patterns['status'])
    pattern_version  = re.compile(patterns['version'])
    # read status code relevant
    code_file        = js['status_code']['file']
    code_ignore      = js['status_code']['ignore']

def do_analyze(path):
    # TODO: do we still need those two?
    versions = defaultdict(list)
    statuses = defaultdict(list)
    global g_version_status
    global g_counter_processed
    with g_counter_processed.get_lock():
            g_counter_processed.value += 1
            g_logger.info("Analyzing: [%d/%d]: %s" % (g_counter_processed.value, g_num_logs_total, os.path.join(path, path)))
    path = os.path.join(path, 'logs')
    files = os.listdir(path)
    for file in files:
        if re.match("logfile", file):
            with open(os.path.join(path, file), 'r') as fd:
                if (file == "logfile0"):
                    for line in fd:
                        version = pattern_ios.findall(line)
                        if not version:
                            version = pattern_android.findall(line)
                        if version:
                            g_logger.debug(version[0])
                            versions[version[0]].append((path, file))
                            break
                # get status code
                for line in fd:
                    status = pattern_status.findall(line)
                    if status:
                        g_logger.debug("status = %s", status)
                        statuses[status[0]].append((path, file))
                        if version:
                            g_version_status.append((version[0], status[0], path, file))

def get_file_list():
    for path, _, _ in os.walk(args.rootdir):
        if path.endswith('DISC.AUTO'):
            g_lines.append(path)
    return len(g_lines)

if (args.rootdir):
    g_logger.info("Analyzing: Walk through '%s' to get log file list." % args.rootdir)
    g_num_logs_total = get_file_list()
else:
    # read a file to a list
    # TODO: set it as a parameter.
    with open('./download_logs/prod/downloaded_log_list.tmp', 'r') as fd:
        for line in fd:
            g_lines.append(line.rstrip())

g_logger.info("Analyzing: Start to analyze logs(%d) in %s" % (g_num_logs_total, args.rootdir))
common.mp_handler(do_analyze, g_lines, 8)

# def print_map_by_order(m,n=1):
#     items=[]
#     for key, values in m.iteritems():
#         g_logger.debug("%s\t%d", key, len(values))
#         items.append((key, len(values)))
#         for value in values:
#             g_logger.debug(str(key)+'\t'+value[0]+'\t'+value[1])
#     for item in sorted(items, key=itemgetter(n)):
#         g_logger.info("%s\t%d", item[0], item[1])

# print_map_by_order(versions)
# print_map_by_order(statuses)

if code_file:
    with open(code_file, "w") as f:
        g_logger.info("Analyzing: Save result to %s" % code_file)
        for item in sorted(list(set(g_version_status)), key=itemgetter(0, 1), reverse=True):
            if pattern_version.match(item[0]) and item[1] not in code_ignore:
                print >> f, "%s\t%s\t%s/%s" % (item[0], item[1], item[2], item[3])

common.beep()