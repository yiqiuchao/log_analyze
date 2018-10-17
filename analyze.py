#!/usr/bin/env python

import os
import re
import json
from collections import defaultdict
from operator import itemgetter
import common
import argparse

versions = defaultdict(list)
statuses = defaultdict(list)
version_status_list = []
logger = common.init_logger()
    
parser = argparse.ArgumentParser()
parser.add_argument('-s', '--secrets', type=argparse.FileType('r'),
                    default='./logserver_secrets.json',
                    help='json file to read account information from')
parser.add_argument('-r', '--rootdir', type=str, default='./',
                    help='the root diretory.')
args = parser.parse_args()

# Android version number pattern
with args.secrets as fd:
    patterns         = json.load(fd)['patterns']
    pattern_ios      = re.compile(patterns['ios'])
    pattern_android  = re.compile(patterns['android'])
    pattern_status   = re.compile(patterns['status'])

for path, subdirs, files in os.walk(args.rootdir):
    version = ""
    status  = ""
    for file in files:
        if 'alt' not in path:
            with open(os.path.join(path, file), 'r') as fd:
                if (file == "logfile0"):
                    for line in fd:
                        version = pattern_ios.findall(line)
                        if not version:
                            version = pattern_android.findall(line)                        
                        if version:
                            logger.debug(version[0])
                            versions[version[0]].append((path, file))
                            break
                # get status code
                if re.match("logfile", file):
                    for line in fd:
                        status = re.findall(pattern_status, line)
                        if status:
                            logger.debug("status = %s", status)
                            statuses[status[0]].append((path, file))
                            if version:
                                version_status_list.append((version[0], status[0], path, file))


def print_map_by_order(m,n=1):
    items=[]
    for key, values in m.iteritems():
        logger.debug("%s\t%d", key, len(values))
        items.append((key, len(values)))
        for value in values:
            logger.debug(str(key)+'\t'+value[0]+'\t'+value[1])
    for item in sorted(items, key=itemgetter(n)):
        logger.info("%s\t%d", item[0], item[1])

print_map_by_order(versions)
print_map_by_order(statuses)

f = open("./status_code.txt", "w")
for version_status in sorted(version_status_list, key=itemgetter(0, 1), reverse=True):
    print >> f, "%s\t%s\t%s/%s" % (version_status[0], version_status[1], version_status[2], version_status[3])