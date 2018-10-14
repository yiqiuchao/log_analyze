#!/usr/bin/env python

import os
import re
import json
from collections import defaultdict
import common

versions = defaultdict(list)
statuses = defaultdict(list)
logger = common.init_logger()

# Android version number pattern
with open('./logserver_secrets.json') as fd:
    patterns         = json.load(fd)['patterns']
    pattern_ios      = re.compile(patterns['ios'])
    pattern_android  = re.compile(patterns['android'])
    pattern_status   = re.compile(patterns['status'])

for path, subdirs, files in os.walk('./'):
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


for key, values in versions.iteritems():
    logger.info("%s\t%d", key, len(values))
    for value in values:
        logger.debug(str(key)+'\t'+value[0]+'\t'+value[1])

for key, values in statuses.iteritems():
    logger.info("%s\t%d", key, len(values))
    for value in values:
        logger.debug(str(key)+'\t'+value[0]+'\t'+value[1])