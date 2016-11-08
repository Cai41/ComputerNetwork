# from ip import *
import random
import time
from socket import *
from struct import pack, unpack
from ip import IP
from arp import Arp

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
    return ip_header_dict, packet[20:ip_header_dict['tot_len']]
    
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


class TCP:
    def __init__(self, host, uri):
        self.IP = IP()

        # do ARP here
        self.Arp = Arp(self.IP.ethernet)
        if self.Arp.find_gateway_mac() == None:
            print "ARP failed"
        self.uri = uri
        self.host = host
        # if next packet is to be sent, then its seq should be self.seq
        self.seq = random.randint(0, (1 << 32) - 1)
        self.ack = 0
        self.sport = random.randint(5000, (1 << 16) - 1)
        self.dport = 80
        self.cwnd = 1
        self.dest_advwnd = 0
        self.sip = unpack('!L', inet_aton(getsourceip()))[0]
        self.dip = unpack('!L', inet_aton(gethostbyname(host)))[0]
        print inet_ntoa(pack('!L', self.sip))
        print inet_ntoa(pack('!L', self.dip))
        # data that haven't been read by application, starting from seq number self.LBR + 1, ending at self.NBE - 1
        self.recv_data  = ''
        # seqno of last ACK received, changing only when ack is recieved
        self.LAR = self.seq - 1
        # last byte sent, changinf only when self.send is called
        self.LBS = self.seq - 1
        # send queue to store all un-acked packet
        self.squeue = {}
        # recv queue to store all out-of-order packet
        self.rqueue = {}
        # seqno of next byte expected, changing only when payload is received
        self.NBE = self.ack
        # seqno of last byte application has read, changing when self.recv() is called
        self.LBR = self.ack - 1
        self.max_recv_buffer = 4096

    # for reciever
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
            return None, None
            
        offset_res = tcp_header_dict['offset_res']
        tcp_header_len = 4*(offset_res >> 4)
        return tcp_header_dict, seg[tcp_header_len:]

    # return a header dictionary that has default value
    def _default_hdr(self):
        tcp_header_dict = {'sport':self.sport, 'dport':self.dport, 'seq':self.seq, 'ack': self.ack,
                           'offset_res': 5 << 4, 'flags': 0,
                           'window': self._advertised_wnd(),
                           'cksum': 0,
                           'urg': 0}
        return tcp_header_dict

    # check whether sequence is within window(min <= seq <= max), sequence number might wrap around
    def _seq_in_window(self, seq, min, max):
        pos = (seq - min + MAX_SEQ) % MAX_SEQ
        max_pos = (max - min + MAX_SEQ + 1) % MAX_SEQ
        return pos < max_pos
    
    # recv one packet starting from NBE, if out of order then buffer and waiting for NBE to come
    # TODO: add a timeout
    def recv(self, max = 10240):
        t = time.time()
        while time.time() - t < 3.0:
            if len(self.recv_data) != 0:
                size = min(max, (self.NBE + MAX_SEQ - self.LBR - 1) % MAX_SEQ)
                data = self.recv_data[:size]
                self.recv_data = self.recv_data[size:]                
                self.LBR = (self.LBR + len(data)) % MAX_SEQ
                return data
            
            try:
                pkt = self.rsock.recv(10240)
            except Exception as e:
                continue
            iphdr, seg = getIPHeader(pkt)
            hdr, payload = self._strip_tcp_hdr(seg)
            if hdr is None or payload is None:
                t = time.time()
                self.send_ack()
                continue
            if hdr['sport'] != self.dport or hdr['dport'] != self.sport:
                continue
            # if it is ack
            if hdr['flags'] & ACK:
                # if it is within the send window
                if self._seq_in_window(hdr['ack'], self.LAR + 1, self.LBS + 1):
                    self.LAR = hdr['ack']
                    filter_queue = {k: v for k, v in self.squeue.iteritems() if k < hdr['ack']}
                    self.squeue = filter_queue
                    self.cwnd += 1

            if len(payload) != 0:
                if hdr['seq'] == self.NBE:
                    self.recv_data += payload
                    self.NBE = (self.NBE + len(payload)) % MAX_SEQ
                    while self.NBE in self.rqueue:
                        tmp = self.NBE
                        self.recv_data += self.rqueue[self.NBE]
                        self.NBE = (self.NBE + len(self.rqueue[self.NBE])) % MAX_SEQ
                        self.rqueue.pop(tmp)
                    # send ack, which equals to self.NBE
                    self.ack = self.NBE
                    self.send_ack()
                elif self._seq_in_window(hdr['seq'], (self.NBE + 1) % MAX_SEQ, (self.LBR + self.max_recv_buffer) % MAX_SEQ):
                    self.rqueue[hdr['seq']] = payload
        return None
    
    # send payload, called by application
    # TODO: if dest_advwmd is 0, then keep calling self.recv() until dest_advwnd is not 0
    def send(self, payload):
        # condition.acquire()
        # if buffer reaches window size, sleep
        # while (self.LBS - self.LAR + MAX_SEQ) % MAX_SEQ>= min(self.max_recv_buffer, self.adwnd)
            # condition.wait()
        pkt_dict = self._default_hdr()
        pkt_dict['flags'] = (1 << 3) + (1 << 4)
        tcp_hdr = self._build_tcp_hdr(pkt_dict, payload)
        self.squeue[self.LBS+1] = (payload, pkt_dict, time.time())
        self.LBS = (self.LBS + len(payload)) % MAX_SEQ
        self.seq = (self.seq + len(payload)) % MAX_SEQ
        # condition.release()
        self.ssock.sendto(default_ip_hdr(self.sip, self.dip) + tcp_hdr + payload, (inet_ntoa(pack('!L', self.dip)), 0))
    
    # send ack
    def send_ack(self):
        pkt_dict = self._default_hdr()
        pkt_dict['flags'] = 1 << 4
        self.ssock.sendto(default_ip_hdr(self.sip, self.dip) + self._build_tcp_hdr(pkt_dict, ''), (inet_ntoa(pack('!L', self.dip)), 0))

    # send syn
    def send_syn(self):
        pkt_dict = self._default_hdr()
        pkt_dict['flags'] = 1 << 1
        self.ssock.sendto(default_ip_hdr(self.sip, self.dip) + self._build_tcp_hdr(pkt_dict, ''), (inet_ntoa(pack('!L', self.dip)), 0))
        self.seq += 1
        self.LBS = self.seq - 1

    # recv syn&ack, only called by handshake
    def recv_syn_ack(self):
        while True:
            p = self.rsock.recv(4096)
            iphdr, p = getIPHeader(p)
            hdr, payload = self._strip_tcp_hdr(p)
            if hdr is None or payload is None:
                continue
            if hdr['sport'] == self.dport and hdr['dport'] == self.sport:
                self.ack = hdr['seq'] + 1
                self.NBE = self.ack
                self.LBR = self.ack - 1
                self.LAR = hdr['ack']
                self.dest_advwnd = hdr['window']
                return
        
    def handshake(self):
        self.send_syn()
        self.recv_syn_ack()
        self.send_ack()

    def print_info(self):
        print 'NBE: ' + str(self.NBE)
        print 'LBR: ' + str(self.LBR)
        print 'LAR: ' + str(self.LAR)
        print 'LBS: ' + str(self.LBS)
        print 'self.ack: ' + str(self.ack)
        print 'self.seq: ' + str(self.seq)
        
