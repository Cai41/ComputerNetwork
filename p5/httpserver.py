from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
import urllib2
import argparse
class WebHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path not in self.server.cache:
            path = 'http://' + self.server.origin + ':8080'+ self.path
            print path
            self.server.cache['path'] = urllib2.urlopen(path).read()
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        self.wfile.write(self.server.cache['path'])

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
    print args
    server = WebServer(('', int(args.port)), WebHandler, args.origin)
    server.serve_forever()
