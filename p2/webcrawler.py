#! /usr/bin/env python

import socket
import argparse
import re
import logging
import time
import Queue
import httpClient
from HTMLParser import HTMLParser
from urlparse import urlparse

# debug level logger
log = logging.getLogger()
log.setLevel(logging.DEBUG)

fh = logging.FileHandler('crawler.log')
ch = logging.StreamHandler()

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s:\n'
                              '%(message)s')
fh.setFormatter(formatter)
ch.setFormatter(formatter)

log.addHandler(fh)
log.addHandler(ch)

login_url = '/accounts/login/?next=/fakebook/'

OK = 0
RETRY = -1


class LinkParser(HTMLParser):
    """subclass of HTMLParser, used for extracting outlinks"""
    def __init__(self):
        self.reset()
        self.urls = set([]) # found URLs are saved into this Set

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            for attr in attrs:
                if attr[0] == 'href':
                    self.urls.add(attr[1])
                    break # an 'a' tag may have multiple attrs, break once we
                          # find the href attr 


class Crawler:
    def __init__(self, hostname, port, username, password):
        self.hostname = hostname
        self.port = port
        self.username = username
        self.password = password
        # frontier of the crawler, URLs to be visited next
        self.queue = Queue.Queue()
        
        # save visited URL in this Set so that no duplicates, quick lookup
        self.visited = set([])
        self.flags = [] # found flags

        # regular expression patterns 
        self.lenPattern = re.compile(r'Content-Length: ([0-9]+)')
        self.chkPattern = re.compile(r'Transfer-Encoding: chunked')
        self.terminalPattern = re.compile(r'0\r\n\r\n')
        self.chunkPattern = re.compile(r'([0-9a-f]+)\r\n(.+)\r\n([0-9a-f]+)\r\n', re.DOTALL)
        self.flagPattern = re.compile(r'<h2 class=\'secret_flag\' style=\"color:red\">FLAG: ([0-9a-zA-Z]+)</h2>')
        self.redirectPattern = re.compile(r'Location: (.+)\r\n')

        # create socket connection using HttpConn class defined in httpClient.py
        self.httpConn = httpClient.HttpConn(self.hostname)

    def getContent(self, recvMsg):
        """
        Args: 
        recvMsg: String -- received message from socket
        Return:
        String -- content of the message
        """

        length = self.lenPattern.search(recvMsg)
        chunked = self.chkPattern.search(recvMsg)
        contentPos = recvMsg.find('\r\n\r\n')
        content = ''
        # deal with chunked message
        if chunked is not None and contentPos != -1:
            m = self.chunkPattern.search(recvMsg, contentPos)
            while m is not None:
                content += recvMsg[m.start(2): m.end(2)]
                m = self.chunkPattern.search(recvMsg, m.end(2))
        elif length is not None and contentPos != -1 and len(recvMsg[contentPos+4:]) <= int(length.group(1)):
            content = recvMsg[contentPos+4: contentPos+4+int(length.group(1))]
        log.debug('Content:' + content)
        log.debug('Content Size:' + str(len(content)))
        return content

    def handleRespMsg(self, recvMsg, currentUrl):
        # first line is status line
        statusLine = recvMsg[:recvMsg.find('\r\n')]
        statusFields = statusLine.split()
        try:
            code = int(statusFields[1]) # status code
        except:
            log.debug('This is impossible..')
            return OK
        if code == 200:
            log.debug('OK')
            return self.handle200(recvMsg, currentUrl)
        elif code == 302:
            # TODO
            # not required by the project, occurs if login seesion expires,
            # relogin
            log.debug('FOUND')
            return OK
        elif code == 301:
            log.debug('MOVED')
            # find redirected URL
            redirect = self.redirectPattern.search(recvMsg)
            url = redirect.group(1)
            vurl = self.validURL(url)
            # make sure this URL is valid and not visited, then add it to queue
            if vurl is not None and vurl not in self.visited:
                self.queue.put(vurl)
            return OK
        elif code == 403 or code == 404:
            log.debug('FORBIDDEN')
            return OK
        elif code == 500:
            log.debug('ServerErr')
            return RETRY
        else:
            # TODO
            log.debug('Unhandled Error')
            return OK

    def handle200(self, recvMsg, currentUrl):
        # call self.getContent, self.searchURL, add them to self.queue and self.visited
        cont = self.getContent(recvMsg)
        urls = self.searchURL(cont)
        # log.debug(urls)
        for url in urls:
            vurl = self.validURL(url)
            if vurl is not None and vurl not in self.visited:
                self.queue.put(vurl)
        f = self.flagPattern.search(cont)
        if f is not None:
            self.flags.append((f.group(1), currentUrl))
        # log.debug(self.visited)
        # log.debug(self.queue)
        return OK

    def searchURL(self, cont):
        htmlParser = LinkParser()
        htmlParser.feed(cont)
        htmlParser.close()
        return htmlParser.urls

    def validURL(self, url):
        """
        check if URL is on the the website cs5700f16.ccs.neu.edu
        either starts with '/' or host name is cs5700f16.ccs.neu.edu
        """
        if url[0] == '/':
            return url
        o = urlparse(url)
        if o.hostname is not None and o.hostname == 'cs5700f16.ccs.neu.edu':
            return o.path
        return None

    def wrapProcessURL(self, url):
        r = httpClient.Request('GET', url)
        r.add_header('Host', self.hostname)
        r.add_header('Cookie', '{0}'.format(self.session))
        # r.add_header('Connection', 'keep-alive')
        recvMsg = self.httpConn.getResponse(r)
        while recvMsg != '' and self.handleRespMsg(recvMsg, url) == RETRY:
            log.debug('retry')
            recvMsg = self.httpConn.getResponse(r)

    def login(self):
        """ login to Fakebook"""
        # GET login page
        r = httpClient.Request('GET', login_url)
        r.add_header('Host', self.hostname)
        recvMsg = self.httpConn.getResponse(r)
        self.visited.add(login_url)

        # Log in
        csrf = re.search(r'csrftoken=([a-zA-Z0-9]+)', recvMsg)
        session = re.search(r'sessionid=([a-zA-Z0-9]+)', recvMsg)
        nextPage = re.search(r'name="next" value="([^"]+)"', recvMsg)
        r = httpClient.Request('POST', '/accounts/login/')
        r.add_header('Host', self.hostname)
        r.add_header('Cookie', '{0}; {1}'.format(csrf.group(0), session.group(0)))
        r.add_form(
            {
                'username': self.username,
                'password': self.password,
                'csrfmiddlewaretoken': csrf.group(1),
                'next': nextPage.group(1)
            })
        r.add_header('Content-length', str(len(r.getContent())))
        recvMsg = self.httpConn.getResponse(r)

        # GET main page and update session cookie
        session = re.search(r'sessionid=([a-zA-Z0-9]+)', recvMsg)
        self.session = session.group(0)
        r = httpClient.Request('GET', '/fakebook/')
        r.add_header('Host', self.hostname)
        r.add_header('Cookie', '{0}'.format(self.session))
        recvMsg = self.httpConn.getResponse(r)
        self.visited.add('/fakebook/')
        self.handleRespMsg(recvMsg, '/fakebook/')
        return

    def search(self):
        while not self.queue.empty() and len(self.flags) < 5:
            url = self.queue.get()
            log.debug(url)
            self.wrapProcessURL(url)
            log.debug(self.flags)
            self.visited.add(url)
            

def main():
    parser = argparse.ArgumentParser(prog="webcrawler")
    parser.add_argument('username')
    parser.add_argument('password')
    args = parser.parse_args()
    # print args

    hostname = 'cs5700f16.ccs.neu.edu'
    port = 80
    username = args.username
    password = args.password

    crawler = Crawler(hostname, port, username, password)
    crawler.login()
    crawler.search()
    log.debug(crawler.flags)
    crawler.httpConn.close()


if __name__ == '__main__':
    main()
