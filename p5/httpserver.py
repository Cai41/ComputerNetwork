from BaseHTTPServer import *
from urllib2 import *
from subprocess import *
import os
import argparse
import re
import socket

class WebHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        osPath = self._pathToFile(self.path)
        cached = False
        content = None
        if os.path.isfile(osPath):
            content = open(osPath).read()
            cached = True
        elif self.path in self.server.cache:
            content = self.server.cache[self.path]
            cached = True

        if cached:
            print 'cache found'
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(content)
        else:
            reqPath = 'http://' + self.server.origin + ':8080'+ self.path
            print reqPath
            try:
                f = urlopen(reqPath)
            except HTTPError as e:
                print e.code, e.reason
                self.send_error(e.code, e.reason)
                return
            except URLError as e:
                print e
                return
            content = f.read()
            if f.getcode() == 200:
                self.server.cache[self.path] = content
            self.send_response(f.getcode())
            self.send_header('Content-Type', 'text/html')            
            self.end_headers()
            self.wfile.write(content)
        output = Popen(['ss', '-i', 'dst' , self.client_address[0]], stdout = PIPE).communicate()[0]
        rtt = self.server.p.search(output).group(1)
        self.server.sock.connect(('cs5700cdnproject.ccs.neu.edu', 55555))        
        self.server.sock.sendall(str(self.client_address[0]) + ' ' + str(rtt))
        self.server.rtt[self.client_address[0]] = rtt
        self.server.sock.close()
        self.server.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print rtt
        
    def _pathToFile(self, path):
        if path == '/':
            return os.curdir + '/index.html'
        else:
            return os.curdir + 'path'

class WebServer(HTTPServer):
    def __init__(self, address, handler, origin):
        HTTPServer.__init__(self, address, handler)
        self.origin = origin
        self.cache = {}
        self.p = re.compile('rtt:([^\s]+)')
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.rtt = {}
        
if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="client")
    parser.add_argument('-p', metavar='port', dest = 'port', help='port number.')
    parser.add_argument('-o', dest='origin', help='origin server')
    args = parser.parse_args()
    server = WebServer(('', int(args.port)), WebHandler, args.origin)
    server.serve_forever()
