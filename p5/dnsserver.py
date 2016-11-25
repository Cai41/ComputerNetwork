import SocketServer
import argparse
import socket
import struct

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

hosts = [('ec2-54-167-4-20.compute-1.amazonaws.com',None),
         ('ec2-54-210-1-206.compute-1.amazonaws.com',None)]

dns_fmt = ['id', 'flags', 'qscount', 'ancount', 'nscount', 'adcount']
record_fmt = ['name', 'type', 'class', 'ttl', 'len', 'rdata']

for i in range(len(hosts)):
    hosts[i] = (hosts[i][0], socket.inet_aton(socket.gethostbyname(hosts[i][0])))
    
class DNSHandler(SocketServer.BaseRequestHandler):
    def handle(self):
        dnsHeader, data = self._stripDNSHeader(self.request[0])
        sock = self.request[1]

        query, restData = self._extractQuery(data)

        ansHdr = self._hdrDict(dnsHeader['id'])
        recDict = self._recDict(self._encodeName('cs5700cdnproject.ccs.neu.edu'), hosts[0][1])
        ansHdr['flags'] = 1 << 15

        sendData = self._buildHdr(ansHdr) + query + self._buildRec(recDict)
        # print ':'.join(x.encode('hex') for x in sendData)
        sock.sendto(sendData, self.client_address)

    def _stripDNSHeader(self, data):
        header = struct.unpack('!HHHHHH', data[:12])
        header_dict = dict(zip(dns_fmt, header))
        print header_dict
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

if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="client")
    parser.add_argument('-p', metavar='port', dest = 'port', help='port number.')
    parser.add_argument('-n', dest='name', help='name to be translated')
    args = parser.parse_args()
    server = SocketServer.UDPServer(('', int(args.port)), DNSHandler)
    server.serve_forever()
