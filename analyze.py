#!/usr/bin/env python

import os
import re
import glob
from collections import defaultdict
import common

versions = defaultdict(list)
logger = common.init_logger()

# Android version number pattern
pattern_ios     = re.compile(r'Controller::App::Version: (.+?)$')
pattern_android = re.compile(r'DeviceInfo:Heos App - Version: (.+?)   Build')

for path, subdirs, files in os.walk('./'):
    for file in files:
        if 'alt' not in path and (file == "logfile0"):
            with open(os.path.join(path, file), 'r') as fd:
                for line in fd:
                    # try to find iOS version number
                    version = pattern_ios.findall(line)
                    if not version:
                        # try to finde Android version number
                        version = pattern_android.findall(line)
                    
                    # Found it!
                    if version:
                        logger.debug(version[0])
                        versions[version[0]].append((path, file))
                        break

for key, values in versions.iteritems():
    for value in values:
        print str(key)+'\t'+value[0]+'\t'+value[1]