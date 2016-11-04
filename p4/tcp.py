# from ip import *
import argparse
import urlparse
import random
import time
from socket import *
from struct import pack, unpack

ip_header_fmt = ['ver_ihl', 'tos', 'tot_len', 'id', 'frag_off', 'ttl', 'protocol', 'cksum', 'saddr', 'daddr']
tcp_header_fmt = ['sport', 'dport', 'seq', 'ack', 'offset_res', 'flags', 'window', 'cksum', 'urg']
ACK = 1 << 4
MAX_SEQ = 1 << 32


def default_ip_hdr(sip, dip):
    return buildIPHeader(default_ip_dict(sip, dip))
    
def buildIPHeader(header):
    return pack('!BBHHHBBHII' , header['ver_ihl'], header['tos'], header['tot_len'],
                header['id'], header['frag_off'], header['ttl'], header['protocol'],
                header['cksum'], header['saddr'], header['daddr'])

def default_ip_dict(sip, dip):
    ip_header_dict = {'ver_ihl': (4 << 4) + 5, 'tos': 0, 'tot_len': 0, 'id': 0,
                  'frag_off': 0, 'ttl': 255, 'protocol': IPPROTO_TCP, 'cksum': 0,
                  'saddr': 0, 'daddr': 0}
    ip_header_dict['saddr'] = sip
    ip_header_dict['daddr'] = dip
    return ip_header_dict

def getIPHeader(packet):
    ip_header = unpack('!BBHHHBBHII', packet[:20])
    ip_header_dict = dict(zip(ip_header_fmt, ip_header))
    return ip_header_dict, packet[20:]
    
if pack("H",1) == "\x00\x01":
    # big endian
    def checksum(msg):
        if len(msg) % 2 == 1:
            msg += '\0'
        sum = 0
        for i in range(0, len(msg), 2):
            w = (ord(msg[i]) << 8) + ord(msg[i+1])
            sum = ((sum + w) & 0xffff) + ((sum + w) >> 16)
        return ~sum & 0xffff
else:
    def checksum(msg):
        if len(msg) % 2 == 1:
            msg += '\0'
        sum = 0
        for i in range(0, len(msg), 2):
            w = ord(msg[i]) + (ord(msg[i+1]) << 8)
            sum = ((sum + w) & 0xffff) + ((sum + w) >> 16)
        return ~sum & 0xffff

def getsourceip(): 
    s = socket(AF_INET, SOCK_DGRAM)
    s.connect(('google.com', 0))
    return s.getsockname()[0]

def parseURL(url):
    u = urlparse.urlparse(url)
    path = u.path
    if u.path == '':
        path += '/index.html'
    elif u.path[-1] == '/':
        path += 'index.html'        
    return u.netloc, path

class TCP:
    def __init__(self, host, url):
        self.rsock = socket(AF_INET, SOCK_RAW, IPPROTO_TCP)
        self.ssock = socket(AF_INET, SOCK_RAW, IPPROTO_RAW)
        self.uri = uri
        self.host = host
        self.seq = random.randint(0, (1 << 32) - 1)
        self.ack = 0
        self.sport = random.randint(5000, (1 << 16) - 1)
        self.dport = 80
        self.cwnd = 1
        self.sip = unpack('!L', inet_aton(getsourceip()))[0]
        self.dip = unpack('!L', inet_aton(gethostbyname(host)))[0]
        print inet_ntoa(pack('!L', self.sip))
        print inet_ntoa(pack('!L', self.dip))
        # data that haven't been read by application, starting from seq number self.LBR + 1
        self.recv_data  = ''
        # seqno of last ACK received
        self.LAR = self.seq - 1
        # last byte sent
        self.LBS = self.seq - 1
        # send queue to store all un-acked packet
        self.squeue = {}
        # recv queue to store all out-of-order packet
        self.rqueue = {}
        # seqno of next byte expected
        self.NBE = self.ack + 1
        # seqno of last byte application has read
        self.LBR = self.ack
        self.max_recv_buffer = 1000

    def _advertised_wnd(self):
        return self.max_recv_buffer - ((self.NBE-1)-self.LBR)
    
    # build header based on dictionary
    def _build_tcp_hdr(self, header, payload):
        tcp_header =  pack('!HHLLBBHHH' , header['sport'], header['dport'], header['seq'],
                           header['ack'], header['offset_res'], header['flags'],
                           header['window'], header['cksum'], header['urg'])
        
        # make a pseudo header and fill the cksum field
        tcp_length = len(tcp_header)+len(payload)
        psh = pack('!IIBBH', self.sip, self.dip, 0, IPPROTO_TCP, tcp_length)
        header['cksum'] = checksum(psh + tcp_header + payload)
        tcp_header =  pack('!HHLLBBH' , header['sport'], header['dport'], header['seq'],
                           header['ack'], header['offset_res'], header['flags'],
                           header['window']) + pack('H', header['cksum']) + pack('!H', header['urg'])
        return tcp_header

    # strip the tcp header, return header dictionary and payload
    def _strip_tcp_hdr(self, seg):
        tcp_header = unpack('!HHLLBBHHH', seg[:20])
        tcp_header_dict = dict(zip(tcp_header_fmt, tcp_header))

        tcp_length = len(seg)
        psh = pack('!IIBBH', self.sip, self.dip, 0, IPPROTO_TCP, tcp_length)
        cksum_msg = psh + seg
        if checksum(cksum_msg) != 0:
            print 'cksum fail'
            
        offset_res = tcp_header_dict['offset_res']
        tcp_header_len = 4*(offset_res >> 4)
        return tcp_header_dict, seg[tcp_header_len:]

    # return a header dictionary that has default value
    def _default_hdr(self):
        tcp_header_dict = {'sport':self.sport, 'dport':self.dport, 'seq':self.seq, 'ack': self.ack,
                           'offset_res': 5 << 4, 'flags': 0,
                           'window': min(self._advertised_wnd(), self.cwnd),
                           'cksum': 0,
                           'urg': 0}
        return tcp_header_dict

    '''
    # check whether sequence is within window(min <= seq <= max), sequence number might wrap around
    def _seq_in_window(seq, min, max):
        pos = (seq - min + MAX_SEQ) % MAX_SEQ
        max_pos = (max - min + MAX_SEQ + 1) % MAX_SEQ
        return pos < max_pos
    
    # called by application
    def recv(self, maxsize = 500):
        while True:
            p = self.sock.recv()
            hdr, payload = _strip_tcp_hdr(p)
            if hdr['sport'] != self.dport or hdr['dport'] != self.sport:
                continue
            # if it is ack
            if hdr['flags'] & ACK:
                lar = self.LAR
                lbs = self.LBS
                # if it is within the send window
                if self._seq_in_window(hdr['ack'], self.LAR + 1, self.LBS + 1):
                    self.condition.acquire()
                    self.LAR = hdr['ack']
                    filter_queue = {k: v for k, v in self.squeue.iteritems() if k < hdr['ack']}
                    self.squeue = filter_queue
                    self.condition.notify()
                    self.condition.release()

            if len(payload) != 0:
                if hdr['seq'] == self.NBE:
                    self.recv_data += payload
                    self.NBE = (self.NBE + len(payload)) % MAX_SEQ
                    while self.rqueue[self.NBE] != None:
                        self.recv_data += self.rqueue[self.NBE]
                        self.NBE = (self.NBE + len(rqueue[self.NBE])) % MAX_SEQ
                        self.rqueue.pop([self.NBE])
                    # send ack, which equals to self.NBE
                    send_ack(self.NBE)
                elif self._seq_in_window(hdr['seq'], (self.NBE + 1) % MAX_SEQ, (self.LBR + self.max_recv_buffer) % MAX_SEQ):
                    self.rqueue[hdr['seq']] = payload

            if self.NBE != self.LBR + 1:
                size = (self.NBE + MAX_SEQ - self.LBR) % MAX_SEQ
                buf = data[:min(size, max_size)]
                data = data[min(size, max_size):]
                self.LBR = (self.LBR + len(buf)) % MAX_SEQ
                return buf
            
    '''
    
    # send payload, called by application
    def send(self, payload):
        # condition.acquire()
        # if buffer reaches window size, sleep
        # while (self.LBS - self.LAR + MAX_SEQ) % MAX_SEQ>= min(self.max_recv_buffer, self.adwnd)
            # condition.wait()
        pkt_dict = self._default_hdr()
        pkt_dict['flags'] = (1 << 3) + (1 << 4)
        tcp_hdr = self._build_tcp_hdr(pkt_dict, payload)
        self.squeue[self.LBS+1] = (payload, pkt_dict, time.time())
        self.LBS += len(payload)
        # condition.release()
        print payload
        self.ssock.sendto(default_ip_hdr(self.sip, self.dip) + tcp_hdr + payload, (inet_ntoa(pack('!L', self.dip)), 0))
        self.seq = (self.seq + len(payload)) % (1 << 32 - 1)
    
    # send ack
    def send_ack(self):
        pkt_dict = self._default_hdr()
        pkt_dict['flags'] = 1 << 4
        print pkt_dict
        self.ssock.sendto(default_ip_hdr(self.sip, self.dip) + self._build_tcp_hdr(pkt_dict, ''), (inet_ntoa(pack('!L', self.dip)), 0))
    
    def send_syn(self):
        pkt_dict = self._default_hdr()
        pkt_dict['flags'] = 1 << 1
        print pkt_dict        
        self.ssock.sendto(default_ip_hdr(self.sip, self.dip) + self._build_tcp_hdr(pkt_dict, ''), (inet_ntoa(pack('!L', self.dip)), 0))

    def recv_syn_ack(self):
        while True:
            p = self.rsock.recv(4096)
            iphdr, p = getIPHeader(p)
            print iphdr
            hdr, payload = self._strip_tcp_hdr(p)
            print hdr
            if hdr['sport'] == self.dport and hdr['dport'] == self.sport:
                break
        self.ack = hdr['seq'] + 1
    
    def handshake(self):
        self.send_syn()
        self.recv_syn_ack()
        self.seq += 1
        self.send_ack()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog = 'rawHttp')
    parser.add_argument('url')
    args = parser.parse_args()

    host, uri =  parseURL(args.url)
    
    tcp = TCP(host, uri)
    tcp.handshake()
    tcp.send('GET {} HTTP/1.1\r\nHost: {}\r\n\r\n'.format(tcp.uri, tcp.host))
