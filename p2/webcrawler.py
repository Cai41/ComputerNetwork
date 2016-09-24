#! /usr/bin/env python

import socket
import argparse
import re
import logging
import time

Debug = 1

log = logging.getLogger()
filehandler = logging.FileHandler('crawler.log')
log.addHandler(filehandler)
consolehandler = logging.StreamHandler()
log.addHandler(consolehandler)
log.setLevel(logging.DEBUG)

def DPrint(debug_info):
    if Debug > 0:
        log.debug(debug_info)

default_host = 'cs5700f16.ccs.neu.edu'
default_connect = 'keep-alive'
default_agent = 'Mozilla/5.0 (X11; Fedora; Linux x86_64) '\
        'AppleWebKit/537.36 (KHTML, like Gecko) '\
        'Chrome/52.0.2743.116 Safari/537.36'
default_accept = 'text/html,application/xhtml+xml,'\
        'application/xml;q=0.9,*/*;q=0.8'
default_lang = 'en-US,en;q=0.5'

class Request():
    def __init__(self, method, uri, version='HTTP/1.1'):
        if method not in ['OPTIONS', 'GET', 'POST', 'HEAD', 'PUT',
                          'DELETE', 'TRACE', 'CONNECT']:
            DPrint("error: method not found")
        self.reqLine = method + ' ' + uri + ' ' + version + '\r\n'
        self.reqHeader = self.reqLine
        self.reqContent = ''
        self.fields = {'method': method, 'uri': uri, 'version': version}
        # print self.reqLine

    def add_header(self, key, val):
        self.fields[key] = val
        self.reqHeader = self.reqHeader+key+': '+val+'\r\n'

    def add_content(self, content):
        self.reqContent = self.reqContent+content

    def repl(self, s):
        return '%'+format(ord(s.group()), 'X')

    def urlencode(self, s):
        return re.sub(r'[^a-zA-Z0-9]', self.repl, s)

    def add_form(self, dict):
        form = ''
        for k in dict:
            key = self.urlencode(k)
            value = self.urlencode(dict[k])
            if len(form) != 0:
                form = form + '&' + key + '=' + value
            else:
                form = form + key + '=' + value
        self.add_content(form)
        # DPrint(form)

    def getContent(self):
        return self.reqContent

    def getAll(self):
        return self.reqHeader+'\r\n'+self.reqContent+'\r\n'


class Crawler:
    def __init__(self, hostname, port, username, password):
        self.hostname = hostname
        self.port = port
        self.username = username
        self.password = password
        self.queue = []
        self.visited = set([])
        
        self.lenPattern = re.compile(r'Content-Length: ([0-9]+)')
        self.chkPattern = re.compile(r'Transfer-Encoding: chunked')
        self.terminalPattern = re.compile(r'0\r\n\r\n')
        self.chunkPattern = re.compile(r'([0-9a-f]+)\r\n(.+)\r\n([0-9a-f]+)\r\n', re.DOTALL)
        
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.sock.connect((hostname, port))
        except Exception as e:
            print 'Can not connect to %s:%d, err: %s' % (hostname, port, e)
            self.sock.close()
            return

    # 1. checks whether the message is complete, if not, keep receiving
    # 2. The other solution (self.recvAll()) is to set timeout(bad solution..)
    def getResponse(self, req):
        recvMsg = ''
        DPrint(req.getAll())
        self.sock.send(req.getAll())
        recvMsg = self.sock.recv(4096)
        while not self.isComplete(recvMsg, req):
            recvMsg += self.sock.recv(4096)
        # recvMsg = self.recvAll()
        DPrint(recvMsg)
        return recvMsg

    # According to https://www.w3.org/Protocols/rfc2616/rfc2616-sec4.html#sec4.4. The length of body may be
    # 1. zero, if code is 204, 304, 1XX or request is HEAD, or
    # 2. identified by chunked transfer-encoding, if Transfer-Encoding is specified in header, or
    # 3. Content-Length, if Content-Length is specified in head, or
    # 4. is identified by self-delimiting media, if media type is multipart/byteranges.(Ignore in this project)
    def isComplete(self, recvMsg, req):
        length = self.lenPattern.search(recvMsg)
        chunked = self.chkPattern.search(recvMsg)
        statusLine = recvMsg[:recvMsg.find('\r\n')]
        statusFields = statusLine.split()
        code = int(statusFields[1])

        if req.fields['method'] == 'HEAD' or code == 204 or code == 304 or 100 <= code < 200:
            return True
        if chunked is not None:
            return self.terminalPattern.search(recvMsg) is not None
        elif length is not None:
            if length.group(1) == 0:
                return True
            content = recvMsg.find('\r\n\r\n')
            return content != -1 and len(recvMsg[content+4:]) == int(length.group(1))
        else:
            # Retry? Throw exception?
            DPrint('This is impossible')
            return False

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
        DPrint('Content:' + content)
        DPrint('Content Size:' + str(len(content)))
        return content

    # might not need this function
    def recvAll(self, timeout=0.5):
        recvMsg = ''
        begin = time.time()
        self.sock.setblocking(0)
        while time.time() - begin < timeout:
            buf = None
            try:
                buf = self.sock.recv(4096)
            except:
                pass
            if buf is not None:
                recvMsg += buf
                begin = time.time()
            else:
                time.sleep(0.1)
        return recvMsg

    def handleRespMsg(self, recvMsg):
        statusLine = recvMsg[:recvMsg.find('\r\n')]
        statusFields = statusLine.split()
        try:
            code = int(statusFields[1])
        except:
            DPrint('This is impossible..')
        if code == 200:
            DPrint('OK')
            return self.handle200(recvMsg)
        elif code == 302:
            # TODO
            DPrint('FOUND')
        elif code == 301:
            # TODO
            DPrint('MOVED')
        elif code == 403:
            # TODO
            DPrint('FORBIDDEN')
        elif code == 500:
            # TODO
            DPrint('ServerErr')
        else:
            # TODO
            DPrint('Unhandled Error')
            
    def handle200(self, recvMsg):
        # TODO:
        # call self.getContent, self.searchURL, add them to self.queue and self.visited
        DPrint('handle200 not implement')
        cont = self.getContent(recvMsg)
        self.searchURL(cont)

    def searchURL(self, cont):
        # TODO
        DPrint('searchURL not implemented')
        while True:
            link = cont.find('a href')
            if link == -1:
                break
            start = cont.find('"', link)
            end = cont.find('"', start+1)
            url = cont[start+1: end]
            DPrint(url)                
            cont = cont[end:]

    def login(self):
        # GET login page
        r = Request('GET', '/accounts/login/?next=/fakebook/')
        r.add_header('Host', 'cs5700f16.ccs.neu.edu')
        # r.add_header('Connection', 'keep-alive')
        recvMsg = self.getResponse(r)
        self.getContent(recvMsg)

        # Log in
        csrf = re.search(r'csrftoken=([a-zA-Z0-9]+)', recvMsg)
        session = re.search(r'sessionid=([a-zA-Z0-9]+)', recvMsg)
        nextPage = re.search(r'name="next" value="([^"]+)"', recvMsg)
        r = Request('POST', '/accounts/login/')
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
        recvMsg = self.getResponse(r)
        self.getContent(recvMsg)
        
        # GET main page and update session cookie
        session = re.search(r'sessionid=([a-zA-Z0-9]+)', recvMsg)
        self.session = session.group(0)
        r = Request('GET', '/fakebook/')
        r.add_header('Host', default_host)
        r.add_header('Cookie', '{0}'.format(self.session))
        recvMsg = self.getResponse(r)
        self.handleRespMsg(recvMsg)
        # self.getContent(recvMsg)        
        return

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
    crawler.sock.close()


if __name__ == '__main__':
    main()
