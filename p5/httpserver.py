from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
import os
import urllib
import argparse

class WebHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        osPath = self._pathToFile(self.path)
        cached = False
        content = ''
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
            f = urllib.urlopen(reqPath)
            content = f.read()
            if f.getcode() == 200:
                self.server.cache[self.path] = content
            self.send_response(f.getcode())
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(content)
        

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
        
if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="client")
    parser.add_argument('-p', metavar='port', dest = 'port', help='port number.')
    parser.add_argument('-o', dest='origin', help='origin server')
    args = parser.parse_args()
    server = WebServer(('', int(args.port)), WebHandler, args.origin)
    server.serve_forever()
