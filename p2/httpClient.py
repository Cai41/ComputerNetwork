import socket
import re
import logging

OK = 0
INCOMPLETE = -1
CORRUPT = -2

log = logging.getLogger(__name__)

class HttpConn():
    def __init__(self, hostname):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.port = 80
        self.hostname = hostname
        self.lenPattern = re.compile(r'Content-Length: ([0-9]+)')
        self.chkPattern = re.compile(r'Transfer-Encoding: chunked')
        self.terminalPattern = re.compile(r'0\r\n\r\n')
        try:
            self.sock.connect((self.hostname, self.port))
        except Exception as e:
            log.error('Can not connect to {}:{}, err: {}'.format(hostname, port, e))
            self.sock.close()
            return

    def _sendReq(self, r):
        try:
            self.sock.send(r.getAll())
            return True
        except Exception as e:
            log.error('Can not send request, err: {}'.format(e))
            return False

    def _recv(self, timeout=2.0):
        recvMsg = None
        self.sock.settimeout(timeout)
        try:
            recvMsg = self.sock.recv(4096)
        except Exception as e:
            log.error('Can not receive message, err: {}'.format(e))
        # self.sock.setblocking(1)
        return recvMsg

    # Checks whether the message is complete, if not, keep receiving
    def getResponse(self, req, times=3):
        log.debug(req.getAll())
        for x in xrange(times):
            if not self._sendReq(req):
                continue
            recvMsg = self._recv(4096)
            if recvMsg is None:
                continue
            
            res = self.isComplete(recvMsg, req)
            while res != OK:
                buf = self._recv(4096)
                if buf is None:
                    break
                recvMsg += buf
                res = self.isComplete(recvMsg, req)
            self.reconnect(recvMsg)
            if res == OK:
                log.debug(recvMsg)
                return recvMsg
        return ''

    def reconnect(self, recvMsg):
        if 'Connection: close' in recvMsg:
            self.sock.close()
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.hostname, self.port))
                
    # According to https://www.w3.org/Protocols/rfc2616/rfc2616-sec4.html#sec4.4. The length of body may be
    # 1. zero, if code is 204, 304, 1XX or request is HEAD, or
    # 2. identified by chunked transfer-encoding, if Transfer-Encoding is specified in header, or
    # 3. Content-Length, if Content-Length is specified in head, or
    # 4. is identified by self-delimiting media, if media type is multipart/byteranges.(Ignore in this project)
    def isComplete(self, recvMsg, req):
        if len(recvMsg) == 0:
            return CORRUPT
        length = self.lenPattern.search(recvMsg)
        chunked = self.chkPattern.search(recvMsg)
        statusLine = recvMsg[:recvMsg.find('\r\n')]
        statusFields = statusLine.split()
        try:
            code = int(statusFields[1])
        except Exception as e:
            log.error('Can not parse code, err: {}'.format(e))
            return CORRUPT

        if req.fields['method'] == 'HEAD' or code == 204 or code == 304 or 100 <= code < 200:
            return OK
        if chunked is not None:
            return OK if self.terminalPattern.search(recvMsg) is not None else INCOMPLETE
        elif length is not None:
            if length.group(1) == 0:
                return OK
            content = recvMsg.find('\r\n\r\n')
            return OK if content != -1 and len(recvMsg[content+4:]) == int(length.group(1)) else INCOMPLETE
        else:
            # Retry? Throw exception?
            return CORRUPT

    def close(self):
        self.sock.close()


class Request():
    def __init__(self, method, uri, version='HTTP/1.1'):
        if method not in ['OPTIONS', 'GET', 'POST', 'HEAD', 'PUT',
                          'DELETE', 'TRACE', 'CONNECT']:
            log.error("error: method not found")
        self.reqLine = method + ' ' + uri + ' ' + version + '\r\n'
        self.reqHeader = self.reqLine
        self.reqContent = ''
        self.fields = {'method': method, 'uri': uri, 'version': version}

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

    def getContent(self):
        return self.reqContent

    def getAll(self):
        return self.reqHeader+'\r\n'+self.reqContent+'\r\n'
