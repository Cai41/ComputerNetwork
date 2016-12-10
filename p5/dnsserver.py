import SocketServer
import argparse
import socket
import struct
from threading import *

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

hosts = [('ec2-54-210-1-206.compute-1.amazonaws.com', None),
         ('ec2-54-67-25-76.us-west-1.compute.amazonaws.com', None),
         ('ec2-35-161-203-105.us-west-2.compute.amazonaws.com', None),
         ('ec2-52-213-13-179.eu-west-1.compute.amazonaws.com', None),
         ('ec2-52-196-161-198.ap-northeast-1.compute.amazonaws.com', None),
         ('ec2-54-255-148-115.ap-southeast-1.compute.amazonaws.com', None),
         ('ec2-13-54-30-86.ap-southeast-2.compute.amazonaws.com', None),
         ('ec2-52-67-177-90.sa-east-1.compute.amazonaws.com', None),
         ('ec2-35-156-54-135.eu-central-1.compute.amazonaws.com', None)]

dns_fmt = ['id', 'flags', 'qscount', 'ancount', 'nscount', 'adcount']
record_fmt = ['name', 'type', 'class', 'ttl', 'len', 'rdata']

for i in range(len(hosts)):
    hosts[i] = (hosts[i][0], socket.gethostbyname(hosts[i][0]))
    
class DNSHandler(SocketServer.BaseRequestHandler):
    def handle(self):
        dnsHeader, data = self._stripDNSHeader(self.request[0])
        sock = self.request[1]
        query, restData = self._extractQuery(data)
        q_name = ''
        i = 0
        skip = ord(query[i])
        while skip != 0:
            if i != 0:
                q_name += '.'
            q_name += query[i+1:i+1+skip]
            i += (1 + skip)
            skip = ord(query[i])
        q_type = struct.unpack('!H', query[i+1:i+3])[0]
        print 'qtype', q_type

        if q_name == self.server.name and q_type == 1:
            ansHdr = self._hdrDict(dnsHeader['id'])
            print self.client_address
            recDict = self._recDict(self._encodeName(self.server.name), self._select_best(self.client_address[0]))
            ansHdr['flags'] = 1 << 15

            sendData = self._buildHdr(ansHdr) + query + self._buildRec(recDict)
            # print ':'.join(x.encode('hex') for x in sendData)
            sock.sendto(sendData, self.client_address)

    def _select_best(self, clientIP):
        res = hosts[0][1]
        print clientIP
        print self.server.rtt
        if clientIP in self.server.rtt and len(self.server.rtt[clientIP]) < len(hosts):
            print 'client meet before'
            for h in hosts:
                print h
                if h[1] not in self.server.rtt[clientIP]:
                    res = h[1]
                    print 'found',h
                if h[1] in self.server.rtt[clientIP]:
                    print 'recorded'
        elif clientIP in self.server.rtt:
            res =  min(self.server.rtt[clientIP], key = self.server.rtt[clientIP].get)
        print res
        return socket.inet_aton(res)
        
    def _stripDNSHeader(self, data):
        header = struct.unpack('!HHHHHH', data[:12])
        header_dict = dict(zip(dns_fmt, header))
        print 'strip'
        print header_dict, data[12:]
        return header_dict, data[12:]

    def _hdrDict(self, id):
        return {'id':id,'flags':0,'qscount':1,'ancount':1,'nscount':0,'adcount':0}

    def _buildHdr(self, hdrDict):
        return struct.pack('!HHHHHH', hdrDict['id'], hdrDict['flags'],
                    hdrDict['qscount'], hdrDict['ancount'], hdrDict['nscount'], hdrDict['adcount'])

    def _recDict(self, name, ip):
        return {'name':name, 'type':1, 'class':1, 'ttl':100,'len':4,'rdata':ip}

    def _buildRec(self, rec):
        print rec
        return rec['name'] + struct.pack('!HHIH', rec['type'],rec['class'],rec['ttl'],rec['len']) + rec['rdata']

    def _extractQuery(self, data):
        pos = data.find('\x00')
        pos += 5
        return data[:pos], data[pos:]

    def _encodeName(self, s):
        labels = s.split('.')
        res = ''
        for l in labels:
            res += struct.pack('B', len(l))
            res += l
        res += '\x00'
        return res

class myServer(SocketServer.UDPServer):
    def __init__(self, addr, handler, name):
        SocketServer.UDPServer.__init__(self, addr, handler)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('', 55555))
        self.rtt = {}
        self.name = name
        Thread(target = self._accept_rtt).start()

    def _accept_rtt(self):
        while True:
            data, addr = self.sock.recvfrom(1024)
            data = data.split()
            print data
            #data[0] is client's ip, data[1] is rtt between client and replica, addr[0] is replica's ip
            if data[0] not in self.rtt:
                self.rtt[data[0]] = {}
            if str(addr[0]) not in self.rtt[data[0]]:
                self.rtt[data[0]][str(addr[0])] = eval(data[1])
            else:
                self.rtt[data[0]][str(addr[0])] = 0.5*self.rtt[data[0]][addr[0]] + 0.5*eval(data[1])
            print self.rtt
            
if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="client")
    parser.add_argument('-p', metavar='port', dest = 'port', help='port number.')
    parser.add_argument('-n', dest='name', help='name to be translated')
    args = parser.parse_args()
    server = myServer(('', int(args.port)), DNSHandler, args.name)
    server.serve_forever()
