import SocketServer
import argparse
import socket

"""
DNS Message Header:

0 1 2 3 4 6 7 8 9 a b c d e 0 1 2 3 4 6 7 8 9 a b c d e
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
        Identifier        |     Flags and Codes         |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      Question Count      |    Answer Record Count      |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
     Name Server Count    |    Additional Record Count  |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

"""

hosts = {'ec2-54-167-4-20.compute-1.amazonaws.com':None,
         'ec2-54-210-1-206.compute-1.amazonaws.com':None}

dns_fmt = {'id', 'flags', 'qscount', 'arcount', 'nscount', 'arcount'}

for h in hosts:
    hosts[h] = socket.gethostbyname(h)
    
class DNSHandler(SocketServer.BaseRequestHandler):
    def handle(self):
        data = self.request[0].strip()
        sock = self.request[1]        
        sock.sendto(data, self.client_address[0]) 

if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="client")
    parser.add_argument('-p', metavar='port', dest = 'port', help='port number.')
    parser.add_argument('-n', dest='name', help='name to be translated')
    args = parser.parse_args()
    server = SocketServer.UDPServer(('', int(args.port)), DNSHandler)
    server.serve_forever()
