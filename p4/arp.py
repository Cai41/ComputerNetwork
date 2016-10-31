from ethernet import Ethernet
import struct
import utils


class Arp:
    def __init__(self):
        self.ethernet = Ethernet()
        self.arp_packet = None
    def build_arp(self, 
            ethernet_protocal_type = utils.ETHERNET_PROTOCOL_TYPE_ARP,
            hardware_type = utils.HARDWARE_TYPE_ETHERNET,
            protocol_type = utils.PROTOCOL_TYPE_IP,
            hardware_size = struct.pack('!B', 0x06),
            protocal_size = struct.pack('!B', 0x04),
            opcode = utils.ARPOP_REQUEST,
            sender_mac = None,
            sender_ip = None,
            target_mac = utils.ZERO_MAC,
            target_ip = None
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
        self.arp_packet = ''.join(self.packet_struct)
    def send(self):
        local_ip = struct.pack('!4B', *[int(x) for x in utils.get_local_ip_address('eth0').split('.')])
        gateway_ip = struct.pack('!4B', *[int(x) for x in utils.get_default_gateway_linux().split('.')])
        local_mac = self.ethernet.sock.getsockname()[4]
        print local_ip, gateway_ip, local_mac
        self.build_arp(source_mac = local_mac, sender_mac = local_mac, sender_ip = local_ip, target_ip = gateway_ip)
        self.ethernet.send(utils.BCAST_MAC, self.arp_packet, ptype = utils.ETHERNET_PROTOCOL_TYPE_ARP)


if __name__ == '__main__':

    a = Arp()
    a.send()

    #recv_sock = socket.socket(SOCK_STREAM, IPPROTO_IP)
    #recv_sock.bind(('eth0', SOCK_RAW))
    while True:
        print a.recvfrom(4096)
