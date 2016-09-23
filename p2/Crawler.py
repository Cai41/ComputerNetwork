#! /usr/bin/env python

import socket, argparse, re

default_host = 'cs5700f16.ccs.neu.edu'
default_connect = 'keep-alive'
default_agent = 'Mozilla/5.0 (X11; Fedora; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/52.0.2743.116 Safari/537.36'
default_accept = 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
default_lang = 'en-US,en;q=0.5'

class Request():
    def __init__(self, method, uri, version='HTTP/1.1'):
        if method not in ['OPTIONS', 'GET', 'POST', 'HEAD', 'PUT', 'DELETE', 'TRACE', 'CONNECT']:
            print "error: method not found"
        self.reqLine = method + ' ' + uri + ' ' + version + '\r\n'
        self.reqHeader = self.reqLine
        self.reqContent = ''
        self.fields = {'method':method, 'uri':uri, 'version':version}
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
                form  = form + '&' + key + '=' + value
            else:
                form = form + key + '=' + value
        self.add_content(form)
        # print form
    def getContent(self):
        return self.reqContent
    def getAll(self):
        return self.reqHeader+'\r\n'+self.reqContent+'\r\n'
    
def main():
    parser = argparse.ArgumentParser(prog="crawler")
    parser.add_argument('username')
    parser.add_argument('password')
    args = parser.parse_args()
    # print args

    hostname = 'cs5700f16.ccs.neu.edu'
    port = 80
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((hostname, port))
    except Exception as e:
        print 'Can not connect to %s:%d, err: %s' % (hostname, port, e)
        sock.close()
        return
    r = Request('GET', '/accounts/login/?next=/fakebook/')
    r.add_header('Host', 'cs5700f16.ccs.neu.edu')
    print r.getAll()
    sock.send(r.getAll())
    recvMsg = sock.recv(4096*4)
    print recvMsg
    csrf = re.search(r'csrftoken=([a-zA-Z0-9]+)', recvMsg)
    session = re.search(r'sessionid=([a-zA-Z0-9]+)', recvMsg)
    nextPage = re.search(r'name="next" value="([^"]+)"', recvMsg)
    # print csrf.group(1)
    # print session.group(1)
    # print nextPage.group(0)
    r = Request('POST', '/accounts/login/')
    # print '{0}; {1}'.format(csrf.group(0), session.group(0))
    r.add_header('Host', default_host)
    r.add_header('Cookie', '{0}; {1}'.format(csrf.group(0), session.group(0)))
    form = 'username={}&password={}&csrfmiddlewaretoken={}&next={}\r\n'.format(args.username, args.password, csrf.group(1), nextPage.group(1))
    # r.add_header('Content-Type', 'application/x-www-form-urlencoded')
    r.add_form({'username':args.username, 'password': args.password, 'csrfmiddlewaretoken': csrf.group(1), 'next': nextPage.group(1)})
    # r.add_content(form)
    r.add_header('Content-length', str(len(r.getContent())))
    print r.getAll() 
    sock.send(r.getAll())
    msg = sock.recv(4096*4)
    print msg
    sock.close()

if __name__=='__main__':
    main()
