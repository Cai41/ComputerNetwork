#! /usr/bin/env python

import socket
import argparse
import re
import logging
import time
import Queue
import httpClient
from HTMLParser import HTMLParser

log = logging.getLogger()
log.setLevel(logging.DEBUG)

fh = logging.FileHandler('crawler.log')
ch = logging.StreamHandler()

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s:\n%(message)s')
fh.setFormatter(formatter)
ch.setFormatter(formatter)

log.addHandler(fh)
log.addHandler(ch)

default_host = 'cs5700f16.ccs.neu.edu'
default_connect = 'keep-alive'
default_agent = 'Mozilla/5.0 (X11; Fedora; Linux x86_64) '\
        'AppleWebKit/537.36 (KHTML, like Gecko) '\
        'Chrome/52.0.2743.116 Safari/537.36'
default_accept = 'text/html,application/xhtml+xml,'\
        'application/xml;q=0.9,*/*;q=0.8'
default_lang = 'en-US,en;q=0.5'
login_url = '/accounts/login/?next=/fakebook/'

OK = 0
RETRY = -1

class Crawler:
    def __init__(self, hostname, port, username, password):
        self.hostname = hostname
        self.port = port
        self.username = username
        self.password = password
        self.queue = Queue.Queue()
        self.visited = set([])
        self.flags = []
        
        self.lenPattern = re.compile(r'Content-Length: ([0-9]+)')
        self.chkPattern = re.compile(r'Transfer-Encoding: chunked')
        self.terminalPattern = re.compile(r'0\r\n\r\n')
        self.chunkPattern = re.compile(r'([0-9a-f]+)\r\n(.+)\r\n([0-9a-f]+)\r\n', re.DOTALL)
        self.flagPattern = re.compile(r'<h2 class=\'secret_flag\' style=\"color:red\">FLAG: ([0-9a-zA-Z]+)</h2>')
        self.redirectPattern = re.compile(r'Location: (.+)\r\n')

        self.httpConn = httpClient.HttpConn(self.hostname)

    # return the content of message
    def getContent(self, recvMsg):
        length = self.lenPattern.search(recvMsg)
        chunked = self.chkPattern.search(recvMsg)
        contentPos = recvMsg.find('\r\n\r\n')
        content = ''
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
        statusLine = recvMsg[:recvMsg.find('\r\n')]
        statusFields = statusLine.split()
        try:
            code = int(statusFields[1])
        except:
            log.debug('This is impossible..')
            return OK
        if code == 200:
            log.debug('OK')
            return self.handle200(recvMsg, currentUrl)
        elif code == 302:
            # TODO
            log.debug('FOUND')
            return OK
        elif code == 301:
            log.debug('MOVED')
            redirect = self.redirectPattern.search(recvMsg)
            url = redirect.group(1)
            vurl = self.validURL(url)
            if vurl is not None and vurl not in self.visited:
                self.visited.add(vurl)
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
                self.visited.add(vurl)
                self.queue.put(vurl)
        f = self.flagPattern.search(cont)
        if f is not None:
            self.flags.append((f.group(1), currentUrl))
        # log.debug(self.visited)
        # log.debug(self.queue)
        return OK

    def searchURL(self, cont):
        # TODO
        class MyHTMLParser(HTMLParser):
            def __init__(self):
                self.urls = set([])

            def handle_starttag(self, tag, attrs):
                if tag == 'a':
                    for attr in attrs:
                        if attr[0] == 'href':
                            self.urls.add(attr[1])
                            break
        parser = MyHTMLParser()
        parser.feed(cont)
        return parser.urls

        # while True:
        #     link = cont.find('a href')
        #     if link == -1:
        #         break
        #     start = cont.find('"', link)
        #     end = cont.find('"', start+1)
        #     url = cont[start+1: end]
        #     urls.append(url)
        #     cont = cont[end:]
        # return urls

    def validURL(self, url):
        if 'http://cs5700f16.ccs.neu.edu' in url:
            return url[url.find('.edu')+4:]
        if url[0:1] == '/':
            return url
        return None

    def wrapProcessURL(self, url):
        r = httpClient.Request('GET', url)
        r.add_header('Host', default_host)
        r.add_header('Cookie', '{0}'.format(self.session))
        # r.add_header('Connection', 'keep-alive')
        recvMsg = self.httpConn.getResponse(r)
        while recvMsg != '' and self.handleRespMsg(recvMsg, url) == RETRY:
            log.debug('retry')
            recvMsg = self.httpConn.getResponse(r)
        
    def login(self):
        # GET login page
        r = httpClient.Request('GET', login_url)
        r.add_header('Host', default_host)
        # r.add_header('Connection', 'keep-alive')
        recvMsg = self.httpConn.getResponse(r)
        # self.getContent(recvMsg)
        self.visited.add(login_url)

        # Log in
        csrf = re.search(r'csrftoken=([a-zA-Z0-9]+)', recvMsg)
        session = re.search(r'sessionid=([a-zA-Z0-9]+)', recvMsg)
        nextPage = re.search(r'name="next" value="([^"]+)"', recvMsg)
        r = httpClient.Request('POST', '/accounts/login/')
        r.add_header('Host', default_host)
        r.add_header('Cookie', '{0}; {1}'.format(csrf.group(0), session.group(0)))
        # r.add_header('Content-Type', 'application/x-www-form-urlencoded')
        r.add_form(
            {
                'username': self.username,
                'password': self.password,
                'csrfmiddlewaretoken': csrf.group(1),
                'next': nextPage.group(1)
            })
        r.add_header('Content-length', str(len(r.getContent())))
        recvMsg = self.httpConn.getResponse(r)
        # self.getContent(recvMsg)
        
        # GET main page and update session cookie
        session = re.search(r'sessionid=([a-zA-Z0-9]+)', recvMsg)
        self.session = session.group(0)
        r = httpClient.Request('GET', '/fakebook/')
        r.add_header('Host', default_host)
        r.add_header('Cookie', '{0}'.format(self.session))
        recvMsg = self.httpConn.getResponse(r)
        self.visited.add('/fakebook/')
        self.handleRespMsg(recvMsg, '/fakebook/')
        # self.getContent(recvMsg)        
        return

    def search(self):
        while not self.queue.empty() and len(self.flags) < 5:
            url = self.queue.get()
            log.debug(url)
            self.wrapProcessURL(url)
            log.debug(self.flags)
            

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
