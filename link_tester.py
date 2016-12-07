import re
import threading
from queue import Queue, Empty
import urllib.request
from urllib.parse import urlsplit, urlunsplit
from urllib.error import URLError, HTTPError
from http.client import HTTPException
import socket

import gzip
import zlib

import argparse
import time
from datetime import datetime

from log import Logger

parser = argparse.ArgumentParser(description='check the Invalid links in the website')
parser.add_argument('-d', type=str, metavar='host', default='m.sohu.com', help='domain/host name. default:m.sohu.com')
parser.add_argument('-n', type=int, metavar='num_threads', default=100, help='number of Threads creating to scrap. default:100')
parser.add_argument('-t', type=int, metavar='timeout', default=100, help='timeout set in seconds in downloading webpage content. default:100. Means if content can\'t not download in 100s, the link will be considered as a error link')

args = parser.parse_args()

scheme = 'http'
host = args.d
num_worker_threads = args.n
timeout = args.t


insite_set = set()  # insite means link in website
outsite_set = set()  # outsite means link is not in website
insite_set_lock = threading.RLock()
outsite_set_lock = threading.RLock()

queue = Queue()  # Task Queue

# result of dead
error_logger = Logger(name=host + '-error-' + datetime.now().strftime('%Y-%m-%d_%H-%M') + '.log')
info_logger = Logger(name=host + '-info-' + datetime.now().strftime('%Y-%m-%d_%H-%M') + '.log')
links_logger = Logger(host + '-links-' + datetime.now().strftime('%Y-%m-%d_%H-%M') + '.log')

# only check links using these schemes
supported_schemes = ('file', 'ftp', 'gopher', 'hdl', 'http', 'https', 'imap', 'mailto',
                     'mms', 'news', 'nntp', 'prospero', 'rsync', 'rtsp', 'rtspu',
                     'sftp', 'shttp', 'sip', 'sips', 'snews', 'svn', 'svn+ssh', 'telnet', 'wais', 'ws', 'wss')

# only find links from the content types below
supported_content_type = ('application/xhtml+xml', 'text/html')

opener = urllib.request.build_opener()
# use User-agent of Googlebot | Search engine | Mobile bot
opener.addheaders = [('User-agent',
                      'Mozilla/5.0 (iPhone; CPU iPhone OS 8_3 like Mac OS X) '
                      'AppleWebKit/600.1.4 (KHTML, like Gecko) Version/8.0 Mobile/12F70 Safari/600.1.4 '
                      '(compatible; Googlebot/2.1; +http://www.google.com/bot.html)')]


# add to set if url is not exists (threading safe)
def set_add_nx(name, url):
    global insite_set, outsite_set
    result = False
    if name == 'insite':
        if insite_set_lock.acquire():
            if url not in insite_set:
                insite_set.add(url)
                result = True
            insite_set_lock.release()
    elif name == 'outsite':
        if outsite_set_lock.acquire():
            if url not in outsite_set:
                outsite_set.add(url)
                result = True
            outsite_set_lock.release()
    return result


# decode content
def read_content(response, content):
    content_type = response.headers.get_content_type()
    charset = response.headers.get_content_charset()
    if not charset:
        charset = 'utf-8'
    content_encoding = response.headers.get('Content-Encoding')
    if content_type in supported_content_type:
        if content_encoding == 'gzip':
            content = gzip.decompress(content)
        elif content_encoding == 'deflate':
            content = zlib.decompress(content)
        content = content.decode(charset)
        return content


# process link, including check outsite link and read insite link content.
def link_process(url):
    global insite_set, outsite_set
    url = urllib.request.quote(url, safe='/:?=#')
    try:
        # response = urllib.request.urlopen(url, timeout=timeout)
        response = opener.open(url, timeout=timeout)
        content = response.read()
    except (URLError, HTTPError) as error:
        error_logger.info(url=url, msg=error)
        return
    except (ConnectionResetError, TimeoutError) as error:
        error_logger.info(url=url, msg=error)
        return
    except socket.timeout as error:
        info_logger.info(url=url, msg='%s. retry later' % error)
        # socket.timeout may cause by poor network status. Put url to queue and retry later
        queue.put(url)
        return
    except HTTPException as error:
        error_logger.error(url=url, msg=error)
        return
    info_logger.info(url=url, msg=response.code)
    if urlsplit(response.url)[1] == host:
        content = read_content(response, content)
        if content:
            link_iter = re.finditer(r"(?<=href=\").+?(?=\")|(?<=href=\').+?(?=\')", content)
            for link in link_iter:
                link = link.group()
                a = list(urlsplit(link))
                if a[0] == '':  # a[0] is scheme
                    a[0] = 'http'
                if a[0] not in supported_schemes:
                    continue
                if a[1] == '':  # a[1] is netloc
                    a[1] = host
                link = urlunsplit(a)
                if a[1] == host:
                    if set_add_nx('insite', link):
                        queue.put(link)  # put link into task queue
                        links_logger.info(url=link, msg='scrap from ' + url)
                elif set_add_nx('outsite', link):
                    queue.put(link)  # put link into task queue
                    links_logger.info(url=link, msg='scrap from ' + url)


def work():
    while True:
        print(threading.active_count(), ' threads are running; ', queue.qsize(), ' links wait for check')
        try:
            url = queue.get(block=False)  # get link from task queue
        except Empty:  # if task queue is empty, wait next task put in queue
            time.sleep(1)
            continue
        if url is None:  # None is stop signal. None will be put into queue after all tasks in queue done.
            break
        link_process(url)  # process link
        queue.task_done()

if __name__ == '__main__':
    queue.put(scheme + '://' + host)
    for i in range(num_worker_threads):
        t = threading.Thread(target=work)
        t.setDaemon(True)
        t.start()
        print('thread %d started' % i)
    queue.join()

    print('All tasks done')
    for i in range(num_worker_threads):
        queue.put(None)
    print('END')