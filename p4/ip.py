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
import random
    
class IP:
    def __init__(self):
        self.ethernet = Ethernet()
        self.source_ip = self.ethernet.local_ip
        self.ipversion = 4

    def _build_header(self, header):
        pseudo_ip_header = struct.pack('!BBHHHBBH' , header['ver_ihl'], header['tos'], header['tot_len'],
                    header['id'], header['frag_off'], header['ttl'], header['protocol'],
                    header['cksum'] ) + header['saddr'] + header['daddr']
        cksum = utils.checksum(pseudo_ip_header)
        ip_header = struct.pack('!BBHHHBBH' , header['ver_ihl'], header['tos'], header['tot_len'],
                    header['id'], header['frag_off'], header['ttl'], header['protocol'],
                    cksum) + header['saddr'] + header['daddr']
        return ip_header, cksum
        

    def send(self, segment, dest_ip):
        """segment is from layer above, e.g. tcp packet, dest_ip is binary form"""
        # add header
        
        random_id = random.randint(0, 65534)
        ip_header_dict = {'ver_ihl': (self.ipversion << 4) + 5, 'tos': 0, 'tot_len': 20 + len(segment), 'id': random_id,
                          'frag_off': 0, 'ttl': 255, 'protocol': 6, 'cksum': 0,
                          'saddr': self.source_ip, 'daddr': dest_ip}
        ip_header, _ = self._build_header(ip_header_dict)
        packet = ip_header + segment 
        self.ethernet.send(packet)

    # return packet if checksum and protocol is correct. Otherwise return None
    def recv(self, from_ip):
        ip_header_fmt = ['ver_ihl', 'tos', 'tot_len', 'id', 'frag_off', 'ttl', 'protocol', 'cksum', 'saddr', 'daddr']
        
        packet = self.ethernet.recv()

        ip_header = struct.unpack('!BBHHHBBH4s4s', packet[:20])
        ip_header_dict = dict(zip(ip_header_fmt, ip_header))
        packet_cksum = ip_header_dict['cksum'] # save real checksum
        ip_header_dict['cksum'] = 0 # for cksum calculation
        # ignore UDP and packets not from server we want
        if ip_header_dict['protocol'] == 17 or ip_header_dict['saddr'] != from_ip:
            #print 'got a udp packet'
            return None
        # verify checksum
        _, cksum = self._build_header(ip_header_dict)
        if cksum == packet_cksum:
            segment = packet[20:ip_header_dict['tot_len']]
            #print 'ip header:', ip_header_dict
            return segment
        # print 'ip cksum fail'
        return None

if __name__ == '__main__':
    ip = IP()
    print ip.recv()
