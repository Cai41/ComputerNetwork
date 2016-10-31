from ethernet import Ethernet
from utils import *


class Arp:
    def __init__(self):
        self.ethernet = Ethernet()
        self.arp_packet = None
    def build_arp(self, 
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
    def send(self):
        self.ethernet.send(self.packet)

if __name__ == '__main__':

    a = Arp()
    a.arp_request_gateway()

    #recv_sock = socket.socket(SOCK_STREAM, IPPROTO_IP)
    #recv_sock.bind(('eth0', SOCK_RAW))
    while True:
        print a.recvfrom(4096)
