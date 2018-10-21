#!/usr/bin/env python

import os
import re
import common
import regexs
from collections import defaultdict
from operator import itemgetter
import argparse

logger = common.init_logger()

parser = argparse.ArgumentParser()
parser.add_argument('-d', '--dir', type=str, default='./',
                    help='the log file diretory.')
parser.add_argument('-p', '--prev', action='store_true',
                    help='if parse prev logs.')
parser.add_argument('-f', '--status_file', action='store_true',
                    help='if get path from the local file.')
args = parser.parse_args()

def parse(file):
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

def save(fd, logdir, file_index):
    # sort map.
    items=[]
    for key, value in devices.iteritems():
        if key and value:
            items.append((value, key))
    
    index = int(0)
    print >> fd, "logfile[%d]: " % file_index, logdir
    for item in sorted(items):
        name = item[1]
        index += 1
        print >> fd, "Device[%d]\t%20s\t%s" % (index, devices[name], name)
        for line in messages[name]:
            print >> fd, '\t', line,
        print >> fd, "="*120

def save_to_memory_without_order(message_container, loginfo, file_index):
    index = int(0)
    message_container.append("logfile[%d]: %s" % (file_index, loginfo))
    for name in devices:
        index += 1
        message_container.append("Device[%d]\t%20s\t%s" % (index, devices[name], name))
        for line in messages[name]:
            message_container.append('\t%s' % line)
        message_container.append("="*120)
        message_container.append("\n")

def save_to_memory(message_container, loginfo, file_index):
    # sort map.
    items=[]
    for key, value in devices.iteritems():
        if key and value:
            items.append((value, key))
    
    index = int(0)
    message_container.append("logfile[%d]: %s" % (file_index, loginfo))
    for item in sorted(items):
        name = item[1]
        index += 1
        message_container.append("Device[%d]\t%20s\t%s" % (index, devices[name], name))
        for line in messages[name]:
            message_container.append('\t%s' % line)
        message_container.append("="*120)
        message_container.append("\n")


# {key=name, value=IP}, we assume that both IP and name are unique.
devices  = defaultdict(str)
# {key=name, value=list of logs}
messages = defaultdict(list)

message_container = []

logfile = 'logfile'
if args.prev:
    logfile = 'prev_' + logfile

index = int(1)
if args.status_file:
    with open('status_code.txt', 'r') as fd:
        for line in fd:
            logdir = os.path.dirname(line.split()[2])
            devices.clear()
            messages.clear()
            for file in os.listdir(logdir):
                if re.match(logfile, file):
                    parse(os.path.join(logdir, file))
            # save(fd_out, logdir, index)
            save_to_memory(message_container, line, index)
            # save_to_memory_without_order(message_container, line, index)
            index += 1
        # print >> fd_out, "Total logs processed: %d" % index
    message_container.append("Total logs processed: %d" % index)
else:
    for file in os.listdir(args.dir):
        if re.match(logfile, file):
            parse(args.dir+file)
    save_to_memory(message_container, args.dir, index)

with open('log_parser.txt', 'w') as fd_out:
    for item in message_container:
        fd_out.write("%s" % item)

# with open('log_parser.txt', 'r') as fd:
#     for line in fd:
#         print line,