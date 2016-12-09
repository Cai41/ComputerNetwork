from BaseHTTPServer import *
from urllib2 import *
from subprocess import *
import os
import argparse
import re
import socket
import Cache

class WebHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        print 'path:', self.path
        self.server.total += 1
        osPath = self._pathToFile(self.path)
        content = None
        # If cached or we know that it will return 404
        if os.path.isfile(osPath):
            self.server.hit += 1
            print 'hit in disk!'
            content = open(osPath).read()        
        elif self.server.cache.contains(self.path):
            self.server.hit += 1
            print 'hit in memory!'
            content = self.server.cache.get(self.path)
        elif self.path in self.server.cache.notFound:
            self.server.hit += 1
            self.send_error(404)
            print 'hit notFound list!'
            return

        if content is not None:
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
                self.server.cache.notFound.add(self.path)
                self.flushNotFound()
                return
            except URLError as e:
                print e
                self.send_error(500)                
                return
            content = f.read()
            if f.getcode() == 200 and self.path in self.server.cache.freq:
                self.server.cache.insert(self.path, content)
            self.send_response(f.getcode())
            self.send_header('Content-Type', 'text/html')            
            self.end_headers()
            self.wfile.write(content)
        output = Popen(['ss', '-i', 'dst' , self.client_address[0]], stdout = PIPE).communicate()[0]
        rtt = self.server.p.search(output).group(1).split('/')[0]
        self.server.sock.sendto(str(self.client_address[0]) + ' ' + str(rtt), ('cs5700cdnproject.ccs.neu.edu', 55555))
        self.server.rtt[self.client_address[0]] = rtt
        print rtt
        print 'hit rate:',str(self.server.hit*1.0/self.server.total)
        
    def _pathToFile(self, path):
        if path == '/':
            return os.getcwd() + '/data/wiki/Main_Page'
        else:
            return os.getcwd() + '/data' + path

    def flushNotFound(self):
        f = open('notFound', 'w')
        for i in self.server.cache.notFound:
            f.write(i+'\n')
        f.close()
        
class WebServer(HTTPServer):
    def __init__(self, address, handler, origin):
        HTTPServer.__init__(self, address, handler)
        self.origin = origin
        self.cache = Cache.Cache(8*1024*1024)
        self.p = re.compile('rtt:([^\s]+)')
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.rtt = {}
        self.total = 0
        self.hit = 0
        
if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="client")
    parser.add_argument('-p', metavar='port', dest = 'port', help='port number.')
    parser.add_argument('-o', dest='origin', help='origin server')
    args = parser.parse_args()
    server = WebServer(('', int(args.port)), WebHandler, args.origin)
    server.serve_forever()
