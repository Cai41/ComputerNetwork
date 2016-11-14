# from ip import *
import random
import time
from socket import *
from struct import pack, unpack
from ip import IP
from arp import Arp
from threading import Lock, Thread
import utils

tcp_header_fmt = ['sport', 'dport', 'seq', 'ack', 'offset_res', 'flags', 'window', 'cksum', 'urg']
ACK = 1 << 4
FIN = 1 << 0
SYN = 1 << 1
RST = 1 << 2
MAX_SEQ = 1 << 32


class TCP:
    def __init__(self, host, uri):
        self.IP = IP()

        # do ARP here
        self.Arp = Arp(self.IP.ethernet)
        if self.Arp.find_gateway_mac() == None:
            print "ARP failed"
        else:
            print 'gateway_mac', self.IP.ethernet.gateway_mac
        self.uri = uri
        self.host = host
        # if next packet is to be sent, then its seq should be self.seq
        self.seq = random.randint(0, (1 << 32) - 1)
        self.ack = 0
        self.sport = random.randint(5000, (1 << 16) - 1)
        self.dport = 80
        self.cwnd = 1
        self.dest_advwnd = 0
        self.sip = self.IP.ethernet.local_ip
        self.dip = inet_aton(gethostbyname(host))
        print 'At TCP, source ip:', inet_ntoa(self.sip)
        print 'At TCP, dest ip:', inet_ntoa(self.dip)
        # data that haven't been read by application, starting from seq number self.LBR + 1, ending at self.NBE - 1
        self.recv_data  = ''
        # seqno of last ACK received, changing only when ack is recieved
        self.LAR = self.seq - 1
        # last byte sent, changinf only when self.send is called
        self.LBS = self.seq - 1
        # send queue to store all un-acked packet
        self.squeue = {}
        self.slock = Lock()
        # recv queue to store all out-of-order packet
        self.rqueue = {}
        # seqno of next byte expected, changing only when payload is received
        self.NBE = self.ack
        # seqno of last byte application has read, changing when self.recv() is called
        self.LBR = self.ack - 1
        self.max_recv_buffer = 65535
        # fin indicate whether it is finished
        self.fin = False
        self.lock = Lock()

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
        psh = pack('!4s4sBBH', self.sip, self.dip, 0, IPPROTO_TCP, tcp_length)
        header['cksum'] = utils.checksum(psh + tcp_header + payload)
        tcp_header =  pack('!HHLLBBH' , header['sport'], header['dport'], header['seq'],
                           header['ack'], header['offset_res'], header['flags'],
                           header['window']) + pack('!H', header['cksum']) + pack('!H', header['urg'])
        return tcp_header

    # strip the tcp header, return header dictionary and payload
    def _strip_tcp_hdr(self, seg):
        tcp_header = unpack('!HHLLBBHHH', seg[:20])
        tcp_header_dict = dict(zip(tcp_header_fmt, tcp_header))

        tcp_length = len(seg)
        psh = pack('!4s4sBBH', self.sip, self.dip, 0, IPPROTO_TCP, tcp_length)
        cksum_msg = psh + seg
        if utils.checksum(cksum_msg) != 0:
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
    # If ip/tcp checksum is incorrect, send ack again.
    # If receive a FIN/REST, send back ACK, and return None to notify upper application
    # If nothing received in 10 seconds, return empty string(in case of network disconnect, server down, etc..)
    # If packet and ip/tcp checksum is correct, return payload
    def recv(self, max_size = 10240):
        # Add a timer to avoid loop forever(in case of network disconnect, server down ....)
        t = time.time()
        while time.time() - t < 10:
            # If there is data int the buffer, return immediately
            if len(self.recv_data) != 0:
                size = min(max_size, (self.NBE + MAX_SEQ - self.LBR - 1) % MAX_SEQ)
                data = self.recv_data[:size]
                self.recv_data = self.recv_data[size:]                
                self.LBR = (self.LBR + len(data)) % MAX_SEQ
                #print 'got data:', data
                return data

            # If no data in buffer and already received fin/rst from server, return None to notify upper application
            if self.fin:
                return None
            
            try:
                pkt = self.IP.recv(self.dip)
                # If check sum fail, send ack and keep receiving
                if pkt == None:
                    self.send_ack()
                    continue
            except Exception as e:
                continue
            hdr, payload = self._strip_tcp_hdr(pkt)
            # If check sum fail, send ack and keep receiving
            if hdr is None or payload is None:
                self.send_ack()
                continue
            # If port number is incorrect, keep receiving
            if hdr['sport'] != self.dport or hdr['dport'] != self.sport:
                continue
            # If it is ack
            if hdr['flags'] & ACK != 0:
                # if it is within the send window
                # print 'ack recevied: ', hdr['ack']
                # print 'self.LBS: ', self.LBS
                if self._seq_in_window(hdr['ack'], self.LAR + 1, self.LBS + 1):
                    acq = self.slock.acquire()
                    self.LAR = hdr['ack']
                    filter_queue = {k: v for k, v in self.squeue.iteritems() if k >= hdr['ack']}
                    self.squeue = filter_queue
                    self.cwnd += 1
                    rel = self.slock.release()

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
                elif self._seq_in_window(hdr['seq'], (self.NBE + 1) % MAX_SEQ, (self.LBR + self.max_recv_buffer) % MAX_SEQ):
                    self.rqueue[hdr['seq']] = payload
                self.send_ack()

            # If RST/FIN in flag, then send ack, set self.fin to be true
            if hdr['flags'] & FIN != 0 or hdr['flags'] & RST != 0:
                self.ack = max(hdr['seq'] + 1, self.ack + 1)
                self.send_ack()
                self.lock.acquire()
                self.fin = True
                self.lock.release()
                print 'rqueue: ', len(self.rqueue)
        # time out, received nothing so return empty string
        return ''

    # send payload, called by application.
    # len(payload) should be smaller than MSS
    def send(self, payload):
        pkt_dict = self._default_hdr()
        pkt_dict['flags'] = (1 << 3) + (1 << 4)
        tcp_hdr = self._build_tcp_hdr(pkt_dict, payload)
        acq = self.slock.acquire()
        self.squeue[self.LBS+1] = (payload, pkt_dict, time.time())
        rel = self.slock.release()
        self.LBS = (self.LBS + len(payload)) % MAX_SEQ
        self.seq = (self.seq + len(payload)) % MAX_SEQ
        self.IP.send(tcp_hdr + payload, self.dip)

    # re-transmit un-acked packet that timeout
    def retrans(self):
        while True:
            self.lock.acquire()
            if self.fin:
                self.lock.release()
                break
            self.lock.release()
            acq = self.slock.acquire()
            for seq in self.squeue:
                if(time.time() - self.squeue[seq][2] > 2.0):
                    self.squeue[seq] = (self.squeue[seq][0], self.squeue[seq][1], time.time())
                    tcp_hdr = self._build_tcp_hdr(self.squeue[seq][1], self.squeue[seq][0])
                    print 'retrans', seq
                    print 'LAR', self.LAR
                    print 'LBS', self.LBS
                    self.IP.send(tcp_hdr + self.squeue[seq][0], self.dip)
            rel = self.slock.release()
            time.sleep(4.0)
    
    # send ack
    def send_ack(self):
        pkt_dict = self._default_hdr()
        pkt_dict['flags'] = ACK
        self.IP.send(self._build_tcp_hdr(pkt_dict, ''), self.dip)

    # send syn
    def send_syn(self):
        pkt_dict = self._default_hdr()
        pkt_dict['flags'] = SYN
        self.IP.send(self._build_tcp_hdr(pkt_dict, ''), self.dip)

    # recv syn&ack, only called by handshake
    def recv_syn_ack(self):
        t = time.time()
        while time.time() - t < 3.0:
            #p = self.IP.recv(4096)
            p = self.IP.recv(self.dip)
            if p == None:
                continue
            # print p
            hdr, payload = self._strip_tcp_hdr(p)
            if hdr is None or payload is None:
                continue
            if hdr['sport'] == self.dport and hdr['dport'] == self.sport:
                self.seq += 1
                self.LBS = self.seq - 1                
                self.ack = hdr['seq'] + 1
                self.NBE = self.ack
                self.LBR = self.ack - 1
                self.LAR = hdr['ack']
                self.dest_advwnd = hdr['window']
                return True
        return False

    # send fin, called when client want to disconnect
    def send_fin(self):
        pkt_dict = self._default_hdr()
        pkt_dict['flags'] = FIN + ACK
        self.IP.send(self._build_tcp_hdr(pkt_dict, ''), self.dip)

    # recv ack for fin, called after sending fin
    def recv_fin_ack(self):
        t = time.time()
        while time.time() - t  < 3.0:
            #p = self.IP.recv(4096)
            p = self.IP.recv(self.dip)
            if p == None:
                continue
            # print p
            hdr, payload = self._strip_tcp_hdr(p)
            if hdr is None or payload is None:
                continue
            if hdr['sport'] == self.dport and hdr['dport'] == self.sport:
                if hdr['flags'] & ACK != 0:
                    return True
        return False
            
    def handshake(self):
        self.send_syn()
        while False == self.recv_syn_ack():
            self.send_syn()
        self.send_ack()
        t = Thread(target=self.retrans)
        t.start()

    def teardown(self):
        self.send_fin()
        while False == self.recv_fin_ack():
            self.send_fin()
        self.lock.acquire()
        if self.fin:
            # self.fin is True means already received FIN.RST from server
            self.lock.release()
            return
        self.fin = True
        self.lock.release()
        # Still add a timer here to avoid the very unlucky situation(server not respond anymore and loop forever)
        # Since we already tear down, so it is OK to ignore the last ACK
        t = time.time()
        while time.time() - t < 10:
            p = self.IP.recv(self.dip)
            if p == None:
                continue
            # print p
            hdr, payload = self._strip_tcp_hdr(p)
            if hdr is None or payload is None:
                continue
            if hdr['sport'] == self.dport and hdr['dport'] == self.sport:
                if hdr['flags'] & FIN != 0 or hdr['flags'] & RST != 0:
                    self.ack = hdr['seq'] + len(payload) + 1
                    self.seq = hdr['ack']
                    self.send_ack()
                    break

    def print_info(self):
        print 'NBE: ' + str(self.NBE)
        print 'LBR: ' + str(self.LBR)
        print 'LAR: ' + str(self.LAR)
        print 'LBS: ' + str(self.LBS)
        print 'self.ack: ' + str(self.ack)
        print 'self.seq: ' + str(self.seq)
        
