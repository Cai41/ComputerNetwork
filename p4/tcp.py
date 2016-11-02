from ip import *
import threading

tcp_header_fmt = ['sport', 'dport', 'seq', 'ack', 'offset_res', 'flags', 'window', 'cksum', 'urg']
ACK = 1 << 4
MAX_SEQ = 1 << 32

class TCP:
    def __init__():
        self.sock = ip.IP()
        self.seq = random.randint(0, (1 << 32) - 1)
        self.sport = 5555
        self.dport = 80
        self.adwnd = 500
        self.cwnd = 1
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
        self.condition = threading.Condition()
        threading.Thread(target = self._loop_recv)

    def _build_tcp_hder(self, header, payload):
        tcp_header =  pack('!HHLLBBHHH' , header['sport'], header['dport'], header['seq'],
                           header['ack'], header['offset_res'], header['flags'],
                           header['window'], header['cksum'], header['urg'])
        
        # make a pseudo header and fill the cksum field
        tcp_length = len(tcp_header)+len(payload)
        psh = pack('!IIBBH', self.sip, self.dip, 0, socket.IPPROTO_TCP, tcp_length)
        header['cksum'] = checksum(psh + tcp_header + payload)
        tcp_header =  pack('!HHLLBBH' , header['sport'], header['dport'], header['seq'],
                           header['ack'], header['offset_res'], header['flags'],
                           header['window']) + pack('H', header['cksum']) + pack('!H', header['urg'])
        return tcp_header

    def _strip_tcp_hder(self, seg):
        tcp_header = unpack('!HHLLBBHHH', seg[:20])
        tcp_header_dict = dict(zip(tcp_header_fmt, tcp_header))

        tcp_length = len(seg)
        psh = pack('!IIBBH', self.sip, self.dip, 0, socket.IPPROTO_TCP, tcp_length)
        cksum_msg = psh + seg
        if checksum(cksum_msg) != 0:
            print 'cksum fail'
            
        offset_res = tcp_header_dict['offset_res']
        tcp_header_len = 4*(offset_res >> 4)
        return tcp_header_dict, seg[tcp_header_len:]

    def _default_hdr():
        tcp_header_dict = {'sport':self.sport, 'dport':self.dport, 'seq':self.seq, 'ack': self.ack,
                           'offset_res': 5 << 4, 'flags': 0,
                           'window': socket.htons(min(self.adwnd, self, cwnd)), 'cksum': 0, 'urg': 0}
        return tcp_header_dict

    # check whether sequence is within window(min <= seq <= max), sequence number might wrap around
    def _seq_in_window(seq, min, max):
        pos = (seq - min + MAX_SEQ) % MAX_SEQ
        max_pos = (max - min + MAX_SEQ + 1) % MAX_SEQ
        return pos < max_pos
    
    # loop forever to receive packet from ip socket
    def _loop_recv(self):
        while True:
            p = self.sock.recv()
            hdr, payload = _strip_tcp_header(p)
            # if it is ack
            if hdr['flags'] & ACK:
                lar = self.LAR
                lbs = self.lbs
                # in case wrapping around
                if lbs
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

    # send payload
    def send(payload):
        condition.acquire()
        # if buffer reaches window size, sleep
        while self.LBS - self.LAR >= min(self.cwnd, self.adwnd)
            condition.wait()
        self.squeue[self.LBS+1] = buffer
        self.LBS += len(buffer)
        pkt_dict = _default_hdr()
        condition.release()
        self.sock.send(self._build_tcp_hdr(pkt_dict, buffer) + buffer)
        self.seq = (self.seq + len(payload)) % (1 << 32 - 1)

    # send ack
    def send_ack(ackno):
        pkt_dcit = _default_hdr()
        pkt_dict['flags'] |= 1 << 1
        self.sock.send(self._build_tcp_hdr(pkt_dict, ''))

    # called by application
    def recv(max_size = 500):
        for i in range(3):
            if self.NBE != self.LBR + 1:
                size = (self.NBE + MAX_SEQ - self.LBR) % MAX_SEQ
                buf = data[:min(size, max_size)]
                data = data[min(size, max_size):]
                self.LBR = (self.LBR + len(buf)) % MAX_SEQ
                return buf
            else:
                time.sleep(0.1)
        return None
        
    def _handshake():
        pass

    def send():
        pass

    def recv():
        pass
