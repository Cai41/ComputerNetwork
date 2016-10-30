import argparse
import urlparse
import random
import socket
from struct import pack, unpack

file_header_fmt = ['majic', 'version_major', 'version_minor', 'zone', 'max_len', 'time_stap', 'link_type']
cap_header_fmt = ['gmt_time', 'micro_time', 'pcap_len', 'len']
mac_header_fmt = ['smac', 'dmac', 'type']
ip_header_fmt = ['ver_ihl', 'tos', 'tot_len', 'id', 'frag_off', 'ttl', 'protocol', 'cksum', 'saddr', 'daddr']
tcp_header_fmt = ['sport', 'dport', 'seq', 'ack', 'offset_res', 'flags', 'window', 'cksum', 'urg']

def parseURL(url):
    u = urlparse.urlparse(url)
    path = u.path
    if u.path == '':
        path += '/index.html'
    elif u.path[-1] == '/':
        path += 'index.html'        
    return u.netloc, path

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

class rawSocket():
    def __init__(self, host, uri):
        self.seq = random.randint(0, (1 << 32) - 1)
        self.httpGet = 'GET {} HTTP/1.1\r\nHost: {}\r\n'.format(uri, host)
        self.sport = 1111
        self.dport = 80
        self.adwnd = 500
        self.cwnd = 1
        self.ipversion = 4
        dip = socket.gethostbyname(host)
        sip = self.getsourceip()
        print dip
        print sip
        self.sip = socket.inet_aton(sip)
        self.dip = socket.inet_aton(dip)

    def getsourceip(self): 
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('google.com', 0))
        return s.getsockname()[0]
       
    def buildTCPHeader(self, header, payload):
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

    def buildIPHeader(self, header):
        return pack('!BBHHHBBHII' , header['ver_ihl'], header['tos'], header['tot_len'],
                    header['id'], header['frag_off'], header['ttl'], header['protocol'],
                    header['cksum'], header['saddr'], header['daddr'])

    def getMACHeader(self, frame):
        mac_header = unpack('!6s6sH', frame[:14])
        print mac_header
        mac_header_dict = dict(zip(mac_header_fmt, mac_header))
        return mac_header_dict
    
    def getIPHeader(self, packet):
    	ip_header = unpack('!BBHHHBBHII', packet[:20])
    	ip_header_dict = dict(zip(ip_header_fmt, ip_header))
        return ip_header_dict

    def getTCPHeader(self, seg):
        tcp_header = unpack('!HHLLBBHHH', seg[:20])
        tcp_header_dict = dict(zip(tcp_header_fmt, tcp_header))

        tcp_length = len(seg)
        psh = pack('!IIBBH', self.sip, self.dip, 0, socket.IPPROTO_TCP, tcp_length)
        cksum_msg = psh + seg
        if checksum(cksum_msg) != 0:
            print 'cksum fail'
        return tcp_header_dict

    def connect(self):
        tcp_header_size = 5
        tcp_header_dict = {'sport':self.sport, 'dport':self.dport, 'seq':self.seq, 'ack': 0,
                           'offset_res': tcp_header_size << 4, 'flags': 1 << 1,
                           'window': socket.htons(min(self.adwnd, self, cwnd)), 'cksum': 0, 'urg': 0}
        tcp_header = buildTCPHeader(tcp_header_dict)

        ip_header_dict = {'ver_ihl': self.ipversion << 4 + 5, 'tos': 0, 'tot_len': 0, 'id': 0,
                          'frag_off': 0, 'ttl': 255, 'protocol': socket.IPPROTO_TCP, 'cksum': 0,
                          'saddr': socket.inet_aton(self.sip), 'daddr': socket.inet_aton (dip)}
        ip_header = buildTCPHeader(ip_header_dict)

        packet = ip_header + tcp_header
        
    def sendPacket(self):
        return 0
    
    def tearDown(self):
        return 0

def testPcapFile(s):
    # read .cap/.pcap file
    fcap = open('testpacket.pcap', 'rb')
    text = fcap.read()

    # read cap
    file_head_len = 24
    cap_head_len = 16
    cap_header = unpack('IIII', text[file_head_len : file_head_len + cap_head_len])
    cap_header_dict = dict(zip(cap_header_fmt, cap_header))

    print 'frame len: ' + str(cap_header_dict['len'])

    # parse frame
    frame = text[file_head_len + cap_head_len: file_head_len + cap_head_len + cap_header_dict['pcap_len']];
    mac_header_dict = s.getMACHeader(frame)
    
    # parse packet
    packet = frame[14:]
    ip_header_dict = s.getIPHeader(packet)
    ip_header_len = (ip_header_dict['ver_ihl'] & 0xF) * 4
    source_address = ip_header_dict['saddr']
    dest_address = ip_header_dict['daddr']

    print 'ip version: ' + str((ip_header_dict['ver_ihl'] & 0xF0) >> 4)
    print 'ip header len: ' + str(ip_header_len) + ' bytes'
    print socket.inet_ntoa(pack('!I', source_address))
    print socket.inet_ntoa(pack('!I', dest_address))

    s.sip = ip_header_dict['saddr']
    s.dip = ip_header_dict['daddr']

    # parse segment
    segment = packet[ip_header_len:]
    tcp_header_dict = s.getTCPHeader(segment)
    offset_res = tcp_header_dict['offset_res']
    tcp_header_len = 4*(offset_res >> 4)
    
    print 'source port: ' + str(tcp_header_dict['sport'])
    print 'dest port: ' + str(tcp_header_dict['dport'])
    print 'window size: ' + str(tcp_header_dict['window'])

    # parse payload
    payload = segment[tcp_header_len:]
    print 'payload: '
    print payload

    return mac_header_dict, ip_header_dict, tcp_header_dict, payload

def testBuildPacket(s, machdr, iphdr, tcphdr, payload):
    # Build tcp header
    seg = s.buildTCPHeader(tcphdr, payload) + payload
    pkt = s.buildIPHeader(iphdr) + seg
    return pkt
    
if __name__ == '__main__':
    # parse the URL given
    parser = argparse.ArgumentParser(prog = 'rawHttp')
    parser.add_argument('url')
    args = parser.parse_args()

    host, uri =  parseURL(args.url)
    s = rawSocket(host, uri)
    
    machdr, iphdr, tcphdr, payload = testPcapFile(s)
    pkt = testBuildPacket(s, machdr, iphdr, tcphdr, payload)

    # print mac head
    print ":".join("{:02x}".format(ord(c)) for c in machdr['smac'])
    print ":".join("{:02x}".format(ord(c)) for c in machdr['dmac'])
    print format(machdr['type'], '04x')
    
