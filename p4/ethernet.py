import struct
import fcntl
import sys
import socket

# constants
BCAST_MAC = struct.pack('!6B', *(0xFF,)*6)
ZERO_MAC = struct.pack('!6B', *(0x00,)*6)
HARDWARE_TYPE_ETHERNET= struct.pack('!H', 0x0001)

ARPOP_REQUEST = struct.pack('!H', 0x0001)
ARPOP_REPLY = struct.pack('!H', 0x0002)

PROTOCOL_TYPE_IP = struct.pack('!H', 0x0800)
# Ethernet protocol type (=ARP)
ETHERNET_PROTOCOL_TYPE_ARP = struct.pack('!H', 0x0806)


def get_default_gateway_linux():
    """Read the default gateway directly from /proc."""
    with open("/proc/net/route") as fh:
        for line in fh:
            fields = line.strip().split()
            if fields[1] != '00000000' or not int(fields[3], 16) & 2:
                continue

            return socket.inet_ntoa(struct.pack("<L", int(fields[2], 16)))

def get_local_ip_address(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(
        s.fileno(),
        0x8915,  # SIOCGIFADDR
        struct.pack('256s', ifname[:15])
    )[20:24])

local_ip = get_local_ip_address('eth0')
gateway_ip = get_default_gateway_linux()

class Arp:
    def __init__(self, 
            sock = None,
            dest_mac = BCAST_MAC,
            source_mac = None,
            ethernet_protocal_type = ETHERNET_PROTOCOL_TYPE_ARP,
            hardware_type = HARDWARE_TYPE_ETHERNET,
            protocol_type = PROTOCOL_TYPE_IP,
            hardware_size = struct.pack('!B', 0x06),
            protocal_size = struct.pack('!B', 0x04),
            opcode = ARPOP_REQUEST,
            sender_mac = None,
            sender_ip = struct.pack('!4B', *[int(x) for x in local_ip.split('.')]),
            target_mac = ZERO_MAC,
            target_ip = struct.pack('!4B', *[int(x) for x in gateway_ip.split('.')])
            ):
        self.packet_struct = [
            dest_mac,
            source_mac,
            ethernet_protocal_type,
            hardware_type,
            protocol_type,
            hardware_size,
            protocal_size,
            opcode,
            sender_mac,
            sender_ip,
            target_mac,
            target_ip
            ]
        self.packet = ''.join(self.packet_struct)
        self.sock = sock
    def send(self):
        self.sock.send(self.packet)

class Ethernet:
    def __init__(self, sock):
        self.sock = sock
        try:
            self.gateway_ip = get_default_gateway_linux()
            print 'gateway_ip:', self.gateway_ip
        except:
            sys.exit()
        self.local_mac= sock.getsockname()[4]
        self.local_ip = get_local_ip_address('eth0')
        self.gateway_mac = None

    def arp_request_gateway(self):
        arp = Arp(sock = self.sock, source_mac = self.local_mac, sender_mac =
                self.local_mac)
        arp.send()
        


if __name__ == '__main__':
    try:
        #s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.IPPROTO_RAW)
        s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW)
    except socket.error , msg:
        print 'Socket could not be created. Error Code : ' + str(msg[0]) + ' Message ' + msg[1]
        if msg[0] == 1:
            print "Need sudo!"
        sys.exit()

    # TODO: need to comfirm if we can assume device is eth0
    s.bind(('eth0', socket.SOCK_RAW))

    ether = Ethernet(s)
    ether.arp_request_gateway()

    #recv_sock = socket.socket(SOCK_STREAM, IPPROTO_IP)
    #recv_sock.bind(('eth0', SOCK_RAW))
    while True:
        print s.recvfrom(4096)
