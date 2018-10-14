#!/usr/bin/env python

# Tested on Python 2.7.15rc1

import os
import re
import sys
import time
import json
import signal
import tarfile
import urlparse
import datetime
import argparse
import requests
import multiprocessing
# Disable the annoying warnings.
from urllib3 import disable_warnings
disable_warnings()

import common

# Get token
# ref: https://stackoverflow.com/questions/13567507/passing-csrftoken-with-python-requests
def get_csrftoken(client, url):
    # Retrieve the CSRF token first
    client.get(url)  
    # sets cookie
    if 'csrftoken' in client.cookies:
        # Django 1.6 and up
        csrftoken = client.cookies['csrftoken']
    else:
        # older versions
        csrftoken = client.cookies['csrf']
    return csrftoken

# Grab a web page(source code).
def get_page((client, next_path)):
    login_data = dict(username=g_logserver_login_username, password=g_logserver_login_password, 
                      csrfmiddlewaretoken=get_csrftoken(client, g_logserver_login_url), next=next_path)
    try:
        r = client.post(g_logserver_login_url, data=login_data, headers=dict(Referer=g_logserver_login_url))
    except:
        g_logger.error("post to %s failed." % url)
        return
    
    global g_shared_list
    g_shared_list.append(r.text)

    global g_counter_pages
    with g_counter_pages.get_lock():
        g_counter_pages.value += 1

    g_logger.info("Downloaded page (%d/%d)" % (g_counter_pages.value, g_args.pages))

def get_pages():
    client = requests.session()
    params = []

    for page in range(g_args.pages):
        next_path = '/'+g_logserver_loglist_path+'?'+'q='+g_query_criteria+'&'+'p='+str(page)
        params.append((client, next_path))
    
    mp_handler(get_page, params, g_args.threads)

# parse the page to get the file id, name and timestamp.
def fill_log_list(input_list, output_list):
    # TODO: use html lib to parse the file.
    # The difference between .+ and .+? is:
    #   .+ is greedy and consumes as many characters as it can.
    #   .+? is reluctant and consumes as few characters as it can.
    # log_id_re   = '<td class="field-log_id">(.+?)</td><td class="field-link_filename">'
    id_name_re   = '<a href="download/(.+?)/">(.+?)</a>'
    timestamp_re = '<td class="field-created_date nowrap">(.+?)</td>'
    regex = re.compile(id_name_re+'.+?'+timestamp_re)
    for line in input_list:
        if (re.match('<tr class', line)):
            # returned found is a list of tuple.
            found = regex.findall(line)
            if (found and (found[0] not in output_list)):
                output_list.extend(found)
    
    g_logger.debug(output_list)

    return len(output_list)

# Download a single file.
def download_file(url, filename='', username='', password=''):
    try:
        r = requests.get(url, auth=(username, password), verify=False, stream=True)
    except:
        g_logger.error("Download %s failed, requests.get returned error." % url)
        return False

    if (r.status_code != 200):
        g_logger.error("Download %s failed, status_code = %d" % (url, r.status_code))
        return False

    if (not len(filename)):
        filename=url.split('/')[-2]+g_file_suffix

    try:
        with open(filename, 'wb') as fd:
            for chunk in r.iter_content(chunk_size=128):
                fd.write(chunk)
            return True
    except:
        g_logger.error("Open or write to %s failed." % filename)
        return False

def extract_date(timestamp):
    # convert it to yyyymmdd
    # there are different formats for timestamp, including:
    # Oct. 10, 2018, 12:14 a.m.
    # Oct. 10, 2018, 12 a.m.
    # Oct. 10, 2018, noon
    # Oct. 11, 2018, midnight
    # Sept. 30, 2018, 4:45 p.m.
    # So:
    #   * get rid of the trailer from the last ','(comma)
    #   * convert Sept to Sep.
    #   * don't know if there are any other months need to convert.    
    try:
        struct_time = time.strptime(timestamp[:timestamp.rfind(',')].replace('Sept', 'Sep'), "%b. %d, %Y")
    except:
        g_logger.warning("Can't get date from %s, skip it." % timestamp)
        return 'unknown_date'

    return str(datetime.datetime(struct_time.tm_year, struct_time.tm_mon, struct_time.tm_mday).date())

def extract_file(file):
    # extract a file to a directory with the same name but without .tar.gz suffix
    # TODO: why it's failed sometimes, Unicode issue?
    try:
        tar = tarfile.open(file, "r:gz")
        tar.extractall(file.replace(g_file_suffix, ''))
        ret = True
    except:
        g_logger.warning('Failed to extract %s' % file)
        ret = False

    tar.close()
    return ret

def delete_file(file):
    os.remove(file)

def get_log_file((file_id, file_name, timestamp)):
    url  = urlparse.urljoin(g_logserver_download_base_url, file_id+'/')
    date = extract_date(timestamp)
    if not len(date):
        # return true to continue process next one.
        return True

    # make dir if needed. remember we are working in the dir made in make_local_dirs()
    make_dir(date)

    file_path = os.path.join(date, file_name)
    # if there is a file or dir with the same name without .tar.gz, it means we've already downloaded this file.
    if os.path.exists(file_path) or os.path.exists(file_path.replace(g_file_suffix, '')):
        global g_counter_existed
        # += operation is not atomic, so we need to get a lock:
        with g_counter_existed.get_lock():
            g_counter_existed.value += 1
        # return false to stop processing next one.
        return False

    # download, extract and then remove it.
    if download_file(url, file_path):
        if extract_file(file_path):
            global g_counter_processed
            # += operation is not atomic, so we need to get a lock:
            with g_counter_processed.get_lock():
                g_counter_processed.value += 1
            g_logger.info("Processed[%d/%d] %s" % (g_counter_processed.value, g_num_logs_total, file_name))
        else:
            global g_counter_failed
            # += operation is not atomic, so we need to get a lock:
            with g_counter_failed.get_lock():
                g_counter_failed.value += 1        
        delete_file(file_path)

# download, extract to dirs and then remove log files.
def get_log_files(log_list):
    mp_handler(get_log_file, log_list, g_args.threads)

# thread pool: https://stackoverflow.com/questions/20887555/dead-simple-example-of-using-multiprocessing-queue-pool-and-locking
# shared counter: https://stackoverflow.com/questions/2080660/python-multiprocessing-and-a-shared-counter
# capture ctrl+c: https://stackoverflow.com/questions/11312525/catch-ctrlc-sigint-and-exit-multiprocesses-gracefully-in-python
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

# Set up arguments.
def init_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--secrets', type=argparse.FileType('r'),
                        default='./logserver_secrets.json',
                        help='json file to read account information from')
    parser.add_argument('-l', '--logserver', type=str, default='prod',
                        choices=['dev', 'merge', 'prod', 'pre-prod', 'beta'],
                        help='log server to download files from')
    parser.add_argument('-q', '--query', type=str, default='',
                        help='query criteria to filter the files')
    parser.add_argument('-p', '--pages', type=int, choices=range(1, 101), default='5',
                        help='how many pages to download')
    parser.add_argument('-t', '--threads', type=int, choices=range(1, 9), default='4',
                        help='how many threads to use')
    parser.add_argument('-d', '--localdir', type=str, default='./',
                        help='where to save the files')
    
    return parser.parse_args()

def make_dir(dir):
    if not os.path.isdir(dir):
        try:
            os.mkdir(dir)
        except:
            g_logger.debug("%s exists." % dir)

def make_local_dirs():
    # make the top dir with name of the filename
    top_dir = os.path.join(g_args.localdir, os.path.splitext(sys.argv[0])[0])
    top_dir = os.path.expanduser(top_dir)
    make_dir(top_dir)

    # then make the second dir with logserver's name
    logserver_dir = os.path.join(top_dir, g_args.logserver)
    make_dir(logserver_dir)

    # then change to that dir, all the logs would be saved there.
    os.chdir(logserver_dir)

# Print header
def print_header():
    print "*"*150
    g_logger.info("Start to download from '%s': %d pages, %d threads." % (g_args.logserver, g_args.pages, g_args.threads))

# Print footer
def print_footer():
    print "*"*150
    g_logger.info("Finished, logs saved to '%s', processed %d, skipped %d, failed %d, spent %s." \
                  % (g_args.localdir, g_counter_processed.value, g_counter_existed.value, g_counter_failed.value, \
                     str(datetime.timedelta(seconds=time.time()-g_start_time))))

####################################################################################################
# Record start time.
g_start_time = time.time()

# Initialization
g_args        = init_args()
g_logger      = common.init_logger()

# Get secrets from json
js = json.load(g_args.secrets)
info = js[g_args.logserver]
comm = js['common']

g_logserver_login_username    = info['name']
g_logserver_login_password    = info['pass']
g_logserver_base_url          = info['url']
g_logserver_login_url         = urlparse.urljoin(g_logserver_base_url, comm['login_path'])
g_logserver_download_base_url = urlparse.urljoin(g_logserver_base_url, comm['download_path'])
g_logserver_loglist_path      = comm['loglist_path']
g_query_criteria              = g_args.query if g_args.query else comm['query']

# Global shared counters.
g_counter_pages      = multiprocessing.Value('i', 0)
g_counter_processed  = multiprocessing.Value('i', 0)
g_counter_existed    = multiprocessing.Value('i', 0)
g_counter_failed     = multiprocessing.Value('i', 0)
g_shared_list        = multiprocessing.Manager().list()
# Readonly for worker threads.
g_num_logs_total     = 0

# file suffix
g_file_suffix = '.tar.gz'

# main
def main():
    global g_num_logs_total
    print_header()    
    # Set up local dirs.
    make_local_dirs()
    # download pages with search criteria.
    get_pages()
    # each item in this list is a tuple with three fields: id, name, timestamp, looks like:
    # (u'6200211', u'log-6324E-982E2E41FE4240F5A638FA76D505D61A-1539130461.DISC.AUTO.tar.gz', u'Oct. 10, 2018, 12:14 a.m.')
    log_list = []
    g_num_logs_total = fill_log_list(''.join(g_shared_list).splitlines(), log_list)
    # download and extract logs.
    get_log_files(log_list)
    print_footer()

if __name__ == '__main__':
    main()