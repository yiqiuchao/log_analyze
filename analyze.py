#!/usr/bin/env python

import os
import re
import json
from collections import defaultdict
import common

versions = defaultdict(list)
logger = common.init_logger()

# Android version number pattern
with open('./logserver_secrets.json') as fd:
    pattern_versions = json.load(fd)['pattern_versions']
    pattern_ios      = re.compile(pattern_versions['ios'])
    pattern_android  = re.compile(pattern_versions['android'])

for path, subdirs, files in os.walk('./'):
    for file in files:
        if 'alt' not in path and (file == "logfile0"):
            with open(os.path.join(path, file), 'r') as fd:
                for line in fd:
                    # try to find iOS version number
                    version = pattern_ios.findall(line)
                    if not version:
                        # try to find Android version number
                        version = pattern_android.findall(line)
                    
                    # Found it!
                    if version:
                        logger.debug(version[0])
                        versions[version[0]].append((path, file))
                        break

for key, values in versions.iteritems():
    logger.info("ver=%s\t%3d", key, len(values))
    for value in values:
        logger.debug(str(key)+'\t'+value[0]+'\t'+value[1])