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
version_status_list = set()
logger = common.init_logger()

parser = argparse.ArgumentParser()
parser.add_argument('-s', '--secrets', type=argparse.FileType('r'),
                    default='./secrets.json',
                    help='json file to read account information from')
args = parser.parse_args()

with args.secrets as fd:
    js               = json.load(fd)
    # read status code relevant
    code_file        = js['status_code']['file']
    code_check       = js['status_code']['check']
    abnormal_file    = js['status_code']['abnormal_file']
    include_keyword  = js['status_code']['include_keyword']

if code_file and code_check and abnormal_file:
    with open(code_file, 'r') as fd, open(abnormal_file, 'w') as ab_fd:
        for line in fd:
            if line.split()[1] in code_check:
                with open(line.split()[2], 'r') as logfile:
                    found = False
                    for ln in logfile:
                        if re.findall(include_keyword, ln):
                            print >> ab_fd, line, ln,
                            found = True
                            break
                    if not found:
                        print line