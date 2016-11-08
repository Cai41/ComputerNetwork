from ethernet import Ethernet
import struct
import utils


class Arp:
    def __init__(self):
        self.ethernet = Ethernet()
        self.arp_packet = None
    def build_arp(self, 
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
    def _broadcast(self):
        self.local_ip = struct.pack('!4B', *[int(x) for x in self.ethernet.local_ip.split('.')])
        self.gateway_ip = struct.pack('!4B', *[int(x) for x in
            self.ethernet.gateway_ip.split('.')])
        self.local_mac = self.ethernet.local_mac
        self.build_arp(sender_mac = local_mac, sender_ip = local_ip, target_ip = gateway_ip)
        self.ethernet.send(utils.BCAST_MAC, self.arp_packet, ptype = utils.ETHERNET_PROTOCOL_TYPE_ARP)

    def find_gateway_mac(self):
        while self.ethernet.gateway_mac == None:
            frame = self.ethernet.recv_sock.recv(65536)
            ethernet_header = frame[0:14]
			dest_mac, source_mac, ptype = struct.unpack("!6s6s2s", ethernet_header)

			arp_header = frame[14:42]
			_, _, _, _, opcode, source_mac_arp, source_ip_arp, dest_mac_arp,
            dest_ip_arp = struct.unpack("2s2s1s1s2s6s4s6s4s", arp_header)
            if opcode == utils.ARPOP_REPLY and self.local_mac == dest_mac and
            source_ip_arp == self.gateway_ip and ptype ==
            utils.ETHERNET_PROTOCOL_TYPE_ARP:
                self.ethernet.gateway_mac = source_mac_arp



			


if __name__ == '__main__':

    a = Arp()

    #recv_sock = socket.socket(SOCK_STREAM, IPPROTO_IP)
    #recv_sock.bind(('eth0', SOCK_RAW))
    a.find_gateway_mac()

