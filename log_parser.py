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
args = parser.parse_args()


# {key=name, value=IP}, we assume that both IP and name are unique.
devices  = defaultdict(str)
# {key=name, value=list of logs}
messages = defaultdict(list)

logfile = 'logfile'
if args.prev:
    logfile = 'prev_' + logfile

for file in os.listdir(args.dir):
    if re.match(logfile, file):
        with open(args.dir+file, 'r') as fd:
            for line in fd:
                for index, regex in enumerate(regexs.regexs):
                    keyword, search, replace = regex
                    if re.search(keyword, line):
                        s = re.sub(search, replace, line)
                        common.debug_print(s, index, -1)
                        if index == 0:
                            l = s.split('\t')
                            devices[common.delete_prefix(l[0], 'ACT-')] = l[4]
                            # devices[l[4]] = l[4]
                        # get device name or IP
                        l = s.split('\t', 1)
                        common.debug_print(l, index, -1)
                        name = common.delete_prefix(l[0], 'ACT-')
                        ip   = devices[name]
                        if name in s or ip in s:
                            messages[name].append(l[1])

with open('log_parser.txt', 'w') as fd:
    # sort map.
    items=[]
    for key, value in devices.iteritems():
        if key and value:
            items.append((value, key))
    
    index = int(0)
    for item in sorted(items):
        name = item[1]
        index += 1
        print >> fd, "Device[%d]\t%20s\t%s" % (index, devices[name], name)
        for line in messages[name]:
            print >> fd, '\t', line,
        print >> fd, "="*120

# with open('log_parser.txt', 'r') as fd:
#     for line in fd:
#         print line,