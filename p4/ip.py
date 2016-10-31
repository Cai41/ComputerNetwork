import utils
import socket
import struct

# IP header
# 0                   1                   2                   3   
#     0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 
#    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
#    |Version|  IHL  |Type of Service|          Total Length         |
#    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
#    |         Identification        |Flags|      Fragment Offset    |
#    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
#    |  Time to Live |    Protocol   |         Header Checksum       |
#    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
#    |                       Source Address                          |
#    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
#    |                    Destination Address                        |
#    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
#    |                    Options                    |    Padding    |
#    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

from ethernet import *

class IP:
    def __init__(self):
        self.ethernet = Ethernet()
        self.source_ip = utils.get_local_ip_address('eth0')

    def _build_header(self, header):
        return pack('!BBHHHBBHII' , header['ver_ihl'], header['tos'], header['tot_len'],
                    header['id'], header['frag_off'], header['ttl'], header['protocol'],
                    header['cksum'], header['saddr'], header['daddr'])
        

    def send(self, segment, dest_ip):
        """segment is from layer above, e.g. tcp packet"""
        # add header
        
        ip_header_dict = {'ver_ihl': self.ipversion << 4 + 5, 'tos': 0, 'tot_len': 0, 'id': 0,
                          'frag_off': 0, 'ttl': 255, 'protocol': socket.IPPROTO_TCP, 'cksum': 0,
                          'saddr': socket.inet_aton(self.source_ip), 'daddr':
                          dest_ip}
        ip_header = buildTCPHeader(ip_header_dict)
        header = None
        packet = header + segment 
        self.ethernet.send(packet)

    def recv(self):
        packet = self.ethernet.recv()
        segment = packet[20:]
        # TODO do stuff like here, remove header
        return segment 

if __name__ == '__main__':
    ip = IP()
    ip.send('', socket.inet_aton('10.0.2.2'))
