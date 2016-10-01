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
log.setLevel(logging.ERROR)

ch = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s:\n'
                              '%(message)s')
ch.setFormatter(formatter)
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
        '''
        set host name, port, username and password
        '''
        self.hostname = hostname
        self.port = port
        self.username = username
        self.password = password

        '''
        queue is for BFS searching the URL
        visited is used to avoid visiting same page twice
        flags are all the flas founded
        '''
        self.queue = Queue.Queue()
        self.visited = set([])
        self.flags = []

        '''
        lenPattern: regex for looking for the Content-Length field in http header
        chkPattern: regex for checking whether the http message is using chunked encoding
        terminalPattern: in the chunked encoding, message is ended by '0\r\n\r\n'
        chunkPattern: regex for looking for each chunk in chunked encoding
        flagPattern: regex for looking for each flag
        redirectPattern: regex for looking for redirect URL when returned 301
        '''
        self.lenPattern = re.compile(r'Content-Length: ([0-9]+)')
        self.chkPattern = re.compile(r'Transfer-Encoding: chunked')
        self.terminalPattern = re.compile(r'0\r\n\r\n')
        self.chunkPattern = re.compile(r'([0-9a-f]+)\r\n(.+)\r\n([0-9a-f]+)\r\n', re.DOTALL)
        self.flagPattern = re.compile(r'<h2 class=\'secret_flag\' style=\"color:red\">FLAG: ([0-9a-zA-Z]+)</h2>')
        self.redirectPattern = re.compile(r'Location: (.+)\r\n')
        '''
        http connection specified by the hostname
        '''
        self.httpConn = httpClient.HttpConn(self.hostname)

    '''
    Given the http message, remove the header and return the content of message
    '''
    def getContent(self, recvMsg):
        '''
        search the length of the message, or whether the message is in chunked encoding
        find the starting position of the content
        '''
        length = self.lenPattern.search(recvMsg)
        chunked = self.chkPattern.search(recvMsg)
        contentPos = recvMsg.find('\r\n\r\n')
        content = ''

        '''
        if the message is chunked encoding, and content is not empty
        '''
        if chunked is not None and contentPos != -1:
            ''' 
            searching for every chunk in the content,
            and concatenate each chunk
            '''
            m = self.chunkPattern.search(recvMsg, contentPos)
            while m is not None:
                content += recvMsg[m.start(2): m.end(2)]
                m = self.chunkPattern.search(recvMsg, m.end(2))
        elif length is not None and contentPos != -1 and len(recvMsg[contentPos+4:]) <= int(length.group(1)):
            '''
            if message is not chunked encoding, then find the total length if the content
            Get the content of message accoring to the length
            '''
            content = recvMsg[contentPos+4: contentPos+4+int(length.group(1))]
        log.debug('Content:' + content)
        log.debug('Content Size:' + str(len(content)))
        return content

    def handleRespMsg(self, recvMsg, currentUrl):
        '''
        The first line is the status line in http header
        The reponse code is the second part of status line
        '''
        statusLine = recvMsg[:recvMsg.find('\r\n')]
        statusFields = statusLine.split()
        try:
            code = int(statusFields[1])
        except:
            return OK
        if code == 200:
            '''
            If response code is 200, call handle200 to process the message: searching for urls and flags in this page
            '''
            return self.handle200(recvMsg, currentUrl)
        elif code == 301:
            '''
            If response code is 301, search the new URL in the header, 
            and add it to the queue if it is a valid url
            '''
            redirect = self.redirectPattern.search(recvMsg)
            url = redirect.group(1)
            vurl = self.validURL(url)
            if vurl is not None and vurl not in self.visited:
                self.visited.add(vurl)
                self.queue.put(vurl)
            return OK
        elif code == 403 or code == 404:
            '''
            Forbidden/Not Found: Abandon the URL
            '''
            return OK
        elif code == 500:
            '''
            ServerErr: return RETRY to tell the crawler to try again on this url
            '''
            return RETRY
        else:
            log.debug('Unhandled Error')
            return OK

    def handle200(self, recvMsg, currentUrl):
        '''
        call self.getContent to get the content of message
        call self.searchURL to search for all the url in the content
        and add each valid url to self.queue and self.visited.
        A valid url is not visited url and also under the domain http://cs5700f16.ccs.neu.edu
        '''
        cont = self.getContent(recvMsg)
        urls = self.searchURL(cont)
        for url in urls:
            vurl = self.validURL(url)
            '''
            Add each valid url to the Queue, and mark as visited
            '''
            if vurl is not None and vurl not in self.visited:
                self.visited.add(vurl)
                self.queue.put(vurl)

        '''
        Searching for flags in this message, and save them t self.glags
        '''
        f = self.flagPattern.search(cont)
        if f is not None:
            self.flags.append((f.group(1), currentUrl))
        return OK

    def searchURL(self, content):
        '''
        make a parser to searching for all urls in the content
        return all urls founded in the content
        '''
        htmlParser = LinkParser()
        htmlParser.feed(content)
        htmlParser.close()
        return htmlParser.urls

    def validURL(self, url):
        '''
        A valid url is either begin with '/' or under the 'cs5700f16.ccs.neu.edu' domain
        Otherwise return None
        '''
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
        recvMsg = self.httpConn.getResponse(r)
        while recvMsg != '' and self.handleRespMsg(recvMsg, url) == RETRY:
            log.debug('retry')
            recvMsg = self.httpConn.getResponse(r)

    def login(self):
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
            

if __name__ == '__main__':
    '''
    parse the username and password form command line
    '''
    parser = argparse.ArgumentParser(prog="webcrawler")
    parser.add_argument('username')
    parser.add_argument('password')
    args = parser.parse_args()

    '''
    set default hostname and port for project2
    save the username and password
    '''
    hostname = 'cs5700f16.ccs.neu.edu'
    port = 80
    username = args.username
    password = args.password

    '''
    make a crawler with default hostname, port and given username and password
    login to the fakebook
    begin to search
    when searching is ended, print every flag
    '''
    crawler = Crawler(hostname, port, username, password)
    crawler.login()
    crawler.search()
    for f in crawler.flags:
        print f[0]
    crawler.httpConn.close()
